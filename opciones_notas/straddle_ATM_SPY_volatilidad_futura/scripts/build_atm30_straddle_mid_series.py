"""Build the first descriptive SPY ATM-straddle-mid series from archived chains.

This module is deliberately contemporaneous: it reads only the option chain and
unadjusted SPY close of each observation date.  It never reads returns after
that date, terminal prices, realised outcomes, or benchmark variables.
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
OUTPUT_PATH = PROJECT_ROOT / "data" / "derived" / "spy_atm30_straddle_mid_rel_2020-01-02_2026-08-31.csv"

DTE_MIN, DTE_MAX, TARGET_DTE = 27, 33, 30
MAX_RELATIVE_SPREAD = 0.10


class ConflictingContractIDError(RuntimeError):
    """Raised before output when one contract ID has non-identical raw rows."""


def _read_payload(path: Path) -> dict[str, Any]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def _chain_date(path: Path) -> str:
    match = re.search(r"(\d{4}-\d{2}-\d{2})", path.name)
    if match is None:
        raise ValueError(f"Cannot infer chain date from {path.name}")
    return match.group(1)


def _fingerprint(record: dict[str, Any]) -> str:
    return json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _retain_identical_duplicates_or_raise(records: list[dict[str, Any]], chain_date: str) -> tuple[list[dict[str, Any]], int]:
    """Retain one copy per identical contract ID; stop on a conflicting ID."""

    groups: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        contract_id = record.get("contractID")
        if contract_id is not None:
            groups[str(contract_id)].append(record)

    retained, identical_extra_rows = [], 0
    for contract_id, rows in groups.items():
        if len(rows) > 1:
            fingerprints = {_fingerprint(row) for row in rows}
            if len(fingerprints) != 1:
                raise ConflictingContractIDError(
                    f"Conflicting duplicate contractID {contract_id} in chain {chain_date}; no CSV was written."
                )
            identical_extra_rows += len(rows) - 1
        retained.append(rows[0])
    return retained, identical_extra_rows


def _quote_fields(record: dict[str, Any]) -> dict[str, float] | None:
    try:
        bid, ask = float(record["bid"]), float(record["ask"])
    except (KeyError, TypeError, ValueError):
        return None
    midpoint = (bid + ask) / 2
    if bid <= 0 or ask < bid or midpoint <= 0:
        return None
    relative_spread = (ask - bid) / midpoint
    return {"bid": bid, "ask": ask, "mid": midpoint, "relative_spread": relative_spread}


def _structural_pairs(records: list[dict[str, Any]], observation_date: date) -> list[dict[str, Any]]:
    """Pair same-strike, same-expiration calls and puts before quote filters."""

    grouped: defaultdict[tuple[str, float], dict[str, list[dict[str, Any]]]] = defaultdict(
        lambda: {"call": [], "put": []}
    )
    for record in records:
        try:
            option_type = str(record["type"])
            expiration = str(record["expiration"])
            strike = float(record["strike"])
            dte = (date.fromisoformat(expiration) - observation_date).days
        except (KeyError, TypeError, ValueError):
            continue
        if option_type in {"call", "put"} and DTE_MIN <= dte <= DTE_MAX:
            grouped[(expiration, strike)][option_type].append(record)

    pairs: list[dict[str, Any]] = []
    for (expiration, strike), sides in grouped.items():
        if not sides["call"] or not sides["put"]:
            continue
        # Any multiple raw logical side is resolved before looking at price by
        # contractID lexical order; in ordinary SPY chains each side is unique.
        call = min(sides["call"], key=lambda row: str(row.get("contractID")))
        put = min(sides["put"], key=lambda row: str(row.get("contractID")))
        pairs.append({
            "expiration": expiration,
            "strike": strike,
            "dte": (date.fromisoformat(expiration) - observation_date).days,
            "call": call,
            "put": put,
        })
    return pairs


def _select_pair(pairs: list[dict[str, Any]], spot: float) -> dict[str, Any] | None:
    """Apply quote/spread filters and deterministic DTE/ATM selection."""

    eligible: list[dict[str, Any]] = []
    for pair in pairs:
        call_quote, put_quote = _quote_fields(pair["call"]), _quote_fields(pair["put"])
        if call_quote is None or put_quote is None:
            continue
        if call_quote["relative_spread"] > MAX_RELATIVE_SPREAD or put_quote["relative_spread"] > MAX_RELATIVE_SPREAD:
            continue
        eligible.append(pair | {"call_quote": call_quote, "put_quote": put_quote})
    if not eligible:
        return None

    # Fixed tie-break order: nearest 30 DTE, nearest ATM, earlier expiration,
    # lower strike, then lexical call and put contract IDs.
    return min(
        eligible,
        key=lambda pair: (
            abs(pair["dte"] - TARGET_DTE),
            abs(pair["strike"] / spot - 1.0),
            pair["expiration"],
            pair["strike"],
            str(pair["call"].get("contractID")),
            str(pair["put"].get("contractID")),
        ),
    )


def _absence_reason(pairs: list[dict[str, Any]]) -> str:
    if not pairs:
        return "no_same_strike_expiration_pair_27_33_dte"
    quote_usable = [pair for pair in pairs if _quote_fields(pair["call"]) is not None and _quote_fields(pair["put"]) is not None]
    if not quote_usable:
        return "no_pair_with_valid_bid_ask"
    return "no_pair_passing_relative_spread_10pct"


def build_series(write_csv: bool = True) -> dict[str, Any]:
    """Return a session-complete descriptive series and coverage tables.

    A conflict raises before the optional CSV write, so no partially trusted
    output is created under the requested duplicate policy.
    """

    files = sorted(
        list(RAW_DIR.glob("spy_historical_options_*.json.gz"))
        + list(RAW_DIR.glob("spy_historical_options_*.json"))
    )
    prices = pd.read_csv(PRICE_PATH, parse_dates=["date"]).set_index("date")
    rows: list[dict[str, Any]] = []
    coverage: defaultdict[str, dict[str, int]] = defaultdict(
        lambda: {
            "sessions": 0,
            "after_identical_dedup": 0,
            "same_strike_expiration_pair_27_33_dte": 0,
            "valid_bid_ask_both_options": 0,
            "relative_spread_le_10pct_both_options": 0,
            "selected_pair": 0,
            "identical_duplicate_extra_rows": 0,
        }
    )

    for path in files:
        date_string = _chain_date(path)
        timestamp = pd.Timestamp(date_string)
        if timestamp not in prices.index:
            continue
        year, observation_date = date_string[:4], date.fromisoformat(date_string)
        raw_records = _read_payload(path).get("data", [])
        retained, identical_extra_rows = _retain_identical_duplicates_or_raise(raw_records, date_string)
        spot = float(prices.loc[timestamp, "close"])
        pairs = _structural_pairs(retained, observation_date)
        quote_usable = [pair for pair in pairs if _quote_fields(pair["call"]) is not None and _quote_fields(pair["put"]) is not None]
        spread_usable = [
            pair for pair in quote_usable
            if _quote_fields(pair["call"])["relative_spread"] <= MAX_RELATIVE_SPREAD
            and _quote_fields(pair["put"])["relative_spread"] <= MAX_RELATIVE_SPREAD
        ]
        selected = _select_pair(pairs, spot)
        stats = coverage[year]
        stats["sessions"] += 1
        stats["after_identical_dedup"] += 1
        stats["same_strike_expiration_pair_27_33_dte"] += bool(pairs)
        stats["valid_bid_ask_both_options"] += bool(quote_usable)
        stats["relative_spread_le_10pct_both_options"] += bool(spread_usable)
        stats["selected_pair"] += bool(selected)
        stats["identical_duplicate_extra_rows"] += identical_extra_rows

        base = {
            "observation_date": date_string,
            "source_file": str(path),
            "spy_close_t": spot,
            "pair_available": selected is not None,
            "absence_reason": None if selected is not None else _absence_reason(pairs),
        }
        if selected is None:
            rows.append(base)
            continue
        call, put = selected["call"], selected["put"]
        call_quote, put_quote = selected["call_quote"], selected["put_quote"]
        rows.append(base | {
            "call_contractID": call.get("contractID"),
            "put_contractID": put.get("contractID"),
            "expiration": selected["expiration"],
            "dte": selected["dte"],
            "strike": selected["strike"],
            "call_bid": call_quote["bid"],
            "call_ask": call_quote["ask"],
            "call_mid": call_quote["mid"],
            "call_relative_spread": call_quote["relative_spread"],
            "put_bid": put_quote["bid"],
            "put_ask": put_quote["ask"],
            "put_mid": put_quote["mid"],
            "put_relative_spread": put_quote["relative_spread"],
            "straddle_mid_rel_t": (call_quote["mid"] + put_quote["mid"]) / spot,
        })

    series = pd.DataFrame(rows).sort_values("observation_date").reset_index(drop=True)
    coverage_by_year = pd.DataFrame([{"year": year} | values for year, values in sorted(coverage.items())])
    totals = coverage_by_year.drop(columns="year").sum().to_dict()
    coverage_total = pd.DataFrame([{"year": "TOTAL"} | {key: int(value) for key, value in totals.items()}])
    if write_csv:
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        series.to_csv(OUTPUT_PATH, index=False)
    return {
        "series": series,
        "coverage_by_year": coverage_by_year,
        "coverage_total": coverage_total,
        "output_path": OUTPUT_PATH,
        "rules": {
            "dte_range": f"{DTE_MIN}-{DTE_MAX}",
            "target_dte": TARGET_DTE,
            "max_relative_spread": MAX_RELATIVE_SPREAD,
            "spot_field": "unadjusted close at t",
            "duplicate_policy": "retain one identical copy; stop on any conflict",
        },
    }


if __name__ == "__main__":
    result = build_series(write_csv=True)
    print(result["coverage_by_year"].to_string(index=False))
    print(f"Wrote {len(result['series']):,} rows to {result['output_path']}")
