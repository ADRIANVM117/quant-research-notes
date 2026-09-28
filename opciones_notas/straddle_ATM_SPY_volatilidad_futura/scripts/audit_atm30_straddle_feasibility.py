"""Read-only feasibility audit for ATM SPY straddles near 30 calendar days.

The module reads only the archived option chains and the local unadjusted SPY
close used for moneyness.  It does not construct a signal, a daily series, or
any forward-volatility outcome.
"""

from __future__ import annotations

import gzip
import json
import re
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
HMM_ROOT = PROJECT_ROOT.parents[1] / "HMM_regime_options"
RAW_DIR = HMM_ROOT / "data" / "raw"
PRICE_PATH = HMM_ROOT / "data" / "derived" / "spy_daily_adjusted_2020_2026.csv"

TARGET_DTE = 30
STRICT_RANGE = (27, 33)
BROAD_RANGE = (21, 45)


def _read_payload(path: Path) -> dict[str, Any]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def _chain_date(path: Path) -> str | None:
    match = re.search(r"(\d{4}-\d{2}-\d{2})", path.name)
    return match.group(1) if match else None


def _record_fingerprint(record: dict[str, Any]) -> str:
    """Full raw-record equality, independent of Python dictionary order."""

    return json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _deduplicate_contract_ids(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Keep one exact duplicate; exclude every contractID with conflicting rows."""

    groups: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    missing_id = 0
    for record in records:
        contract_id = record.get("contractID")
        if contract_id is None:
            missing_id += 1
            continue
        groups[str(contract_id)].append(record)

    retained: list[dict[str, Any]] = []
    stats = {
        "contract_id_groups": len(groups),
        "duplicate_contract_id_groups": 0,
        "identical_duplicate_groups": 0,
        "identical_duplicate_extra_rows": 0,
        "conflicting_contract_id_groups": 0,
        "conflicting_rows_excluded": 0,
        "missing_contract_id_rows": missing_id,
    }
    for rows in groups.values():
        if len(rows) == 1:
            retained.append(rows[0])
            continue
        stats["duplicate_contract_id_groups"] += 1
        fingerprints = {_record_fingerprint(row) for row in rows}
        if len(fingerprints) == 1:
            stats["identical_duplicate_groups"] += 1
            stats["identical_duplicate_extra_rows"] += len(rows) - 1
            retained.append(rows[0])
        else:
            stats["conflicting_contract_id_groups"] += 1
            stats["conflicting_rows_excluded"] += len(rows)
    return retained, stats


def _valid_quote(record: dict[str, Any]) -> tuple[float, float, float] | None:
    try:
        bid, ask = float(record["bid"]), float(record["ask"])
    except (KeyError, TypeError, ValueError):
        return None
    midpoint = (bid + ask) / 2
    if bid > 0 and ask >= bid and midpoint > 0:
        return bid, ask, midpoint
    return None


def _session_pair_candidates(records: list[dict[str, Any]], chain_date: date, spot: float) -> list[dict[str, Any]]:
    """Build valid call/put pairs, matching exactly on expiration and strike."""

    options: defaultdict[tuple[str, float], dict[str, list[dict[str, Any]]]] = defaultdict(
        lambda: {"call": [], "put": []}
    )
    for record in records:
        try:
            option_type = record["type"]
            expiration = str(record["expiration"])
            strike = float(record["strike"])
            expiration_date = date.fromisoformat(expiration)
        except (KeyError, TypeError, ValueError):
            continue
        if option_type not in {"call", "put"}:
            continue
        if _valid_quote(record) is None:
            continue
        options[(expiration, strike)][option_type].append(record)

    candidates: list[dict[str, Any]] = []
    for (expiration, strike), sides in options.items():
        if not sides["call"] or not sides["put"]:
            continue
        # Contract IDs are the final deterministic tie-breaker if a raw chain
        # has more than one usable record for one logical option side.
        call = min(sides["call"], key=lambda row: str(row.get("contractID")))
        put = min(sides["put"], key=lambda row: str(row.get("contractID")))
        call_bid, call_ask, call_mid = _valid_quote(call)  # validated above
        put_bid, put_ask, put_mid = _valid_quote(put)
        dte = (date.fromisoformat(expiration) - chain_date).days
        candidates.append({
            "expiration": expiration,
            "strike": strike,
            "dte": dte,
            "moneyness_distance": abs(strike / spot - 1.0),
            "call_contractID": call.get("contractID"),
            "put_contractID": put.get("contractID"),
            "call_bid": call_bid,
            "call_ask": call_ask,
            "call_midpoint": call_mid,
            "put_bid": put_bid,
            "put_ask": put_ask,
            "put_midpoint": put_mid,
            "call_spread": call_ask - call_bid,
            "put_spread": put_ask - put_bid,
            "call_relative_spread": (call_ask - call_bid) / call_mid,
            "put_relative_spread": (put_ask - put_bid) / put_mid,
        })
    return candidates


def _select_pair(candidates: list[dict[str, Any]], dte_range: tuple[int, int]) -> dict[str, Any] | None:
    eligible = [pair for pair in candidates if dte_range[0] <= pair["dte"] <= dte_range[1]]
    if not eligible:
        return None
    # Fixed ordering: nearest DTE to 30; nearest strike to spot; earlier
    # expiration; lower strike; then lexical call and put IDs.
    return min(
        eligible,
        key=lambda pair: (
            abs(pair["dte"] - TARGET_DTE),
            pair["moneyness_distance"],
            pair["expiration"],
            pair["strike"],
            str(pair["call_contractID"]),
            str(pair["put_contractID"]),
        ),
    )


def audit_atm30_straddles() -> dict[str, Any]:
    """Audit coverage, duplicates, selections and trace examples for straddles."""

    files = sorted(
        list(RAW_DIR.glob("spy_historical_options_*.json.gz"))
        + list(RAW_DIR.glob("spy_historical_options_*.json"))
    )
    prices = pd.read_csv(PRICE_PATH, parse_dates=["date"]).set_index("date")
    year_stats: defaultdict[str, dict[str, int]] = defaultdict(
        lambda: {
            "sessions": 0,
            "strict_sessions": 0,
            "broad_sessions": 0,
            "duplicate_contract_id_groups": 0,
            "identical_duplicate_groups": 0,
            "identical_duplicate_extra_rows": 0,
            "conflicting_contract_id_groups": 0,
            "conflicting_rows_excluded": 0,
            "missing_contract_id_rows": 0,
        }
    )
    duplicate_totals: defaultdict[str, int] = defaultdict(int)
    strict_selected: list[dict[str, Any]] = []
    broad_selected: list[dict[str, Any]] = []
    session_dates: list[str] = []

    for path in files:
        date_string = _chain_date(path)
        if date_string is None:
            continue
        timestamp = pd.Timestamp(date_string)
        if timestamp not in prices.index:
            continue
        chain_date = date.fromisoformat(date_string)
        try:
            raw_records = _read_payload(path).get("data", [])
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        retained, duplicate_stats = _deduplicate_contract_ids(raw_records)
        year = date_string[:4]
        stats = year_stats[year]
        stats["sessions"] += 1
        session_dates.append(date_string)
        for name, value in duplicate_stats.items():
            if name != "contract_id_groups":
                stats[name] += value
                duplicate_totals[name] += value
        spot = float(prices.loc[timestamp, "close"])
        candidates = _session_pair_candidates(retained, chain_date, spot)
        common = {"observation_date": date_string, "source_file": str(path), "spot_close_unadjusted": spot}
        strict = _select_pair(candidates, STRICT_RANGE)
        broad = _select_pair(candidates, BROAD_RANGE)
        if strict is not None:
            stats["strict_sessions"] += 1
            strict_selected.append(common | strict | {"definition": "27-33 DTE"})
        if broad is not None:
            stats["broad_sessions"] += 1
            broad_selected.append(common | broad | {"definition": "21-45 DTE"})

    coverage = pd.DataFrame(
        [{"year": year} | stats for year, stats in sorted(year_stats.items())]
    )
    strict_frame = pd.DataFrame(strict_selected).sort_values("observation_date").reset_index(drop=True)
    broad_frame = pd.DataFrame(broad_selected).sort_values("observation_date").reset_index(drop=True)
    anchors = [session_dates[0], session_dates[(len(session_dates) - 1) // 2], session_dates[-1]]
    strict_by_date = strict_frame.set_index("observation_date") if not strict_frame.empty else pd.DataFrame()
    examples: list[dict[str, Any]] = []
    for position, anchor in zip(("inicio", "mitad", "final"), anchors):
        if not strict_frame.empty and anchor in strict_by_date.index:
            record = strict_by_date.loc[anchor]
            if isinstance(record, pd.DataFrame):
                record = record.iloc[0]
            examples.append({"position": position, "anchor_date": anchor, "status": "strict pair selected", **record.to_dict()})
        else:
            examples.append({"position": position, "anchor_date": anchor, "status": "no 27-33 DTE usable pair"})

    return {
        "strict_range": STRICT_RANGE,
        "broad_range": BROAD_RANGE,
        "target_dte": TARGET_DTE,
        "files_scanned": len(files),
        "coverage_by_year": coverage,
        "duplicate_totals": dict(duplicate_totals),
        "strict_selected": strict_frame,
        "broad_selected": broad_frame,
        "examples": pd.DataFrame(examples),
    }


if __name__ == "__main__":
    result = audit_atm30_straddles()
    print(result["coverage_by_year"].to_string(index=False))
    print(result["duplicate_totals"])
