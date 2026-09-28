"""Auditoría reproducible de la resolución de ``implied_volatility`` de SPY.

No modifica las cadenas originales ni construye una serie IV30.  La función
principal conserva la regla descriptiva de la auditoría de factibilidad:
21--45 DTE y strike dentro de ±2 % del cierre contemporáneo de SPY.
"""

from __future__ import annotations

import gzip
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
HMM_ROOT = PROJECT_ROOT.parents[1] / "HMM_regime_options"
RAW_DIR = HMM_ROOT / "data" / "raw"
PRICE_PATH = HMM_ROOT / "data" / "derived" / "spy_daily_adjusted_2020_2026.csv"

PROBE_DTE_MIN = 21
PROBE_DTE_MAX = 45
PROBE_ABS_MONEYNESS_MAX = 0.02
TRACE_DATES = ("2020-01-02", "2022-10-03", "2025-04-03")
IV_RECONSTRUCTION_PROBE_DATES = TRACE_DATES


def _read_payload(path: Path) -> dict[str, Any]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def _chain_date(path: Path) -> str | None:
    match = re.search(r"(\d{4}-\d{2}-\d{2})", path.name)
    return match.group(1) if match else None


def _top_values(counter: Counter[str], count: int = 5) -> list[dict[str, Any]]:
    return [
        {"iv_raw": value, "contracts": contracts}
        for value, contracts in sorted(counter.items(), key=lambda item: (-item[1], item[0]))[:count]
    ]


def audit_iv_resolution() -> dict[str, Any]:
    """Return descriptive tables and trace examples for raw-provider IV values."""

    files = sorted(
        list(RAW_DIR.glob("spy_historical_options_*.json.gz"))
        + list(RAW_DIR.glob("spy_historical_options_*.json"))
    )
    prices = pd.read_csv(PRICE_PATH, parse_dates=["date"]).set_index("date")

    by_year: dict[str, dict[str, Any]] = {}
    overall_values: Counter[str] = Counter()
    decimal_places: Counter[int] = Counter()
    examples: dict[str, dict[str, Any]] = {}
    raw_records = unique_contracts = duplicate_records = sessions = 0

    for path in files:
        date_string = _chain_date(path)
        if date_string is None:
            continue
        date = pd.Timestamp(date_string)
        if date not in prices.index:
            continue
        try:
            records = _read_payload(path).get("data", [])
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue

        spot = float(prices.loc[date, "close"])
        candidates: list[dict[str, Any]] = []
        for record in records:
            try:
                dte = (pd.Timestamp(record["expiration"]) - date).days
                strike = float(record["strike"])
            except (KeyError, TypeError, ValueError):
                continue
            if PROBE_DTE_MIN <= dte <= PROBE_DTE_MAX and abs(strike / spot - 1.0) <= PROBE_ABS_MONEYNESS_MAX:
                candidates.append(record)

        year = date_string[:4]
        if year not in by_year:
            by_year[year] = {
                "raw_records": 0,
                "unique_contracts": 0,
                "nonmissing_iv": 0,
                "iv_values": Counter(),
            }
        year_stats = by_year[year]
        year_stats["raw_records"] += len(candidates)
        raw_records += len(candidates)
        sessions += 1

        # A repeated contract in the same raw response must not inflate the
        # apparent concentration of a provider value.
        unique = {
            str(record["contractID"]): record
            for record in candidates
            if record.get("contractID") is not None
        }
        year_stats["unique_contracts"] += len(unique)
        unique_contracts += len(unique)
        duplicate_records += len(candidates) - len(unique)

        for record in unique.values():
            iv = record.get("implied_volatility")
            if iv in (None, ""):
                continue
            iv_raw = str(iv)  # preserve the representation supplied in JSON
            year_stats["nonmissing_iv"] += 1
            year_stats["iv_values"][iv_raw] += 1
            overall_values[iv_raw] += 1
            if isinstance(iv, str) and "." in iv:
                decimal_places[len(iv.split(".", 1)[1])] += 1

        if date_string in TRACE_DATES:
            grouped: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
            for record in unique.values():
                iv = record.get("implied_volatility")
                if iv not in (None, ""):
                    grouped[str(iv)].append(record)
            eligible = []
            for iv_raw, same_iv in grouped.items():
                strikes = {str(record.get("strike")) for record in same_iv}
                quotes = {(str(record.get("bid")), str(record.get("ask"))) for record in same_iv}
                if len(same_iv) >= 2 and (len(strikes) >= 2 or len(quotes) >= 2):
                    eligible.append((len(strikes), len(quotes), len(same_iv), iv_raw, same_iv))
            if eligible:
                _, _, _, iv_raw, same_iv = max(eligible, key=lambda item: item[:4])
                rows = sorted(
                    same_iv,
                    key=lambda record: (
                        str(record.get("expiration")),
                        str(record.get("type")),
                        float(record.get("strike") or 0),
                    ),
                )[:8]
                examples[date_string] = {
                    "source_file": str(path),
                    "spot_close": spot,
                    "iv_raw": iv_raw,
                    "same_iv_contracts": len(same_iv),
                    "distinct_strikes": len({str(record.get("strike")) for record in same_iv}),
                    "distinct_bid_ask": len({(str(record.get("bid")), str(record.get("ask"))) for record in same_iv}),
                    "contracts": [
                        {field: record.get(field) for field in (
                            "contractID", "type", "expiration", "strike",
                            "implied_volatility", "bid", "ask", "last", "delta",
                        )}
                        for record in rows
                    ],
                }

    year_rows: list[dict[str, Any]] = []
    for year, stats in sorted(by_year.items()):
        values: Counter[str] = stats["iv_values"]
        total = sum(values.values())
        top_five = _top_values(values)
        top_five_contracts = sum(item["contracts"] for item in top_five)
        year_rows.append({
            "year": year,
            "raw_records": stats["raw_records"],
            "unique_session_contracts": stats["unique_contracts"],
            "nonmissing_iv": stats["nonmissing_iv"],
            "distinct_iv_raw": len(values),
            "top_five": top_five,
            "top_five_pct": 100 * top_five_contracts / total if total else float("nan"),
        })

    top_ten = _top_values(overall_values, 10)
    total_nonmissing = sum(overall_values.values())
    return {
        "probe": {
            "dte_min": PROBE_DTE_MIN,
            "dte_max": PROBE_DTE_MAX,
            "abs_moneyness_max": PROBE_ABS_MONEYNESS_MAX,
            "spot_field": "close",
            "price_path": str(PRICE_PATH),
        },
        "files_scanned": len(files),
        "sessions_scanned": sessions,
        "candidate_raw_records": raw_records,
        "candidate_unique_session_contracts": unique_contracts,
        "duplicate_candidate_records": duplicate_records,
        "precision_decimals": dict(sorted(decimal_places.items())),
        "total_nonmissing_iv": total_nonmissing,
        "distinct_iv_raw": len(overall_values),
        "top_ten": top_ten,
        "top_ten_pct": 100 * sum(item["contracts"] for item in top_ten) / total_nonmissing,
        "by_year": pd.DataFrame(year_rows),
        "examples": examples,
    }


def iv_reconstruction_probe() -> pd.DataFrame:
    """Return a fixed, small ATM/30-DTE price-inversion probe.

    Contract selection is set before looking at any price inversion: choose the
    expiration whose DTE is closest to 30 (earliest expiration breaks a tie),
    then the closest strike to the unadjusted SPY close separately for a call
    and a put (lower strike, then contract ID, break ties).  This function
    intentionally does *not* calculate implied volatility because the local
    repository has no dated risk-free curve nor a forward dividend schedule.
    """

    prices = pd.read_csv(PRICE_PATH, parse_dates=["date"]).set_index("date")
    rows: list[dict[str, Any]] = []
    for date_string in IV_RECONSTRUCTION_PROBE_DATES:
        date = pd.Timestamp(date_string)
        price_row = prices.loc[date]
        source_files = sorted(
            list(RAW_DIR.glob(f"spy_historical_options_{date_string}.json.gz"))
            + list(RAW_DIR.glob(f"spy_historical_options_{date_string}.json"))
        )
        if len(source_files) != 1:
            raise FileNotFoundError(f"Expected exactly one raw chain for {date_string}; found {len(source_files)}")
        source_file = source_files[0]
        records = _read_payload(source_file).get("data", [])
        eligible: list[tuple[int, dict[str, Any]]] = []
        for record in records:
            try:
                dte = (pd.Timestamp(record["expiration"]) - date).days
                if dte > 0 and record.get("type") in {"call", "put"}:
                    eligible.append((dte, record))
            except (KeyError, TypeError, ValueError):
                continue
        dtes = sorted({dte for dte, _ in eligible})
        selected_dte = min(dtes, key=lambda value: (abs(value - 30), value))
        for option_type in ("call", "put"):
            contracts = [record for dte, record in eligible if dte == selected_dte and record["type"] == option_type]
            contract = min(
                contracts,
                key=lambda record: (
                    abs(float(record["strike"]) / float(price_row["close"]) - 1.0),
                    float(record["strike"]),
                    str(record.get("contractID")),
                ),
            )
            bid = float(contract["bid"])
            ask = float(contract["ask"])
            rows.append({
                "observation_date": date_string,
                "source_file": str(source_file),
                "spot_close_unadjusted": float(price_row["close"]),
                "same_day_recorded_dividend": float(price_row["dividend_amount"]),
                "same_day_split_coefficient": float(price_row["split_coefficient"]),
                "risk_free_curve_available_at_t": False,
                "forward_dividend_schedule_available_at_t": False,
                "contractID": contract.get("contractID"),
                "type": option_type,
                "expiration": contract.get("expiration"),
                "dte": selected_dte,
                "strike": float(contract["strike"]),
                "bid": bid,
                "ask": ask,
                "midpoint": (bid + ask) / 2,
                "provider_iv_raw": contract.get("implied_volatility"),
                "delta": contract.get("delta"),
                "inversion_status": "BLOCKED: missing dated risk-free curve and forward dividend schedule",
            })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    result = audit_iv_resolution()
    print(result["by_year"].to_string(index=False))
    print(f"IV distintas: {result['distinct_iv_raw']}")
