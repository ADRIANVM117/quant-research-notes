"""Align the frozen descriptive straddle selection with exact-date SPY closes.

This module does not select contracts, calculate a benchmark, or evaluate any
predictive relationship. It only obtains the unadjusted SPY close on the exact
expiration date already stored in each selected straddle row.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
HMM_ROOT = PROJECT_ROOT.parents[1] / "HMM_regime_options"
INPUT_PATH = PROJECT_ROOT / "data" / "derived" / "spy_atm30_straddle_mid_rel_2020-01-02_2026-08-31.csv"
PRICE_PATH = HMM_ROOT / "data" / "derived" / "spy_daily_adjusted_2020_2026.csv"
OUTPUT_PATH = PROJECT_ROOT / "data" / "derived" / "spy_atm30_straddle_terminal_move_rel_2020-01-02_2026-08-31.csv"


def align_terminal_move(write_csv: bool = True) -> dict[str, Any]:
    """Return the one-to-one terminal-move table while preserving every row.

    An exact expiration-date close is required. No previous/next business-day
    substitution is permitted, so holidays and end-of-history expirations stay
    missing with an explicit reason.
    """

    source = pd.read_csv(INPUT_PATH, parse_dates=["observation_date", "expiration"])
    source.insert(0, "series_row_index", range(len(source)))
    prices = pd.read_csv(PRICE_PATH, parse_dates=["date"])
    closes = prices.set_index("date")["close"]
    history_start, history_end = closes.index.min(), closes.index.max()

    output_rows: list[dict[str, Any]] = []
    for row in source.to_dict("records"):
        available = bool(row["pair_available"])
        result = {
            "series_row_index": row["series_row_index"],
            "observation_date": row["observation_date"],
            "pair_available": available,
            "absence_reason": row.get("absence_reason"),
            "call_contractID": row.get("call_contractID"),
            "put_contractID": row.get("put_contractID"),
            "expiration": row.get("expiration"),
            "dte": row.get("dte"),
            "strike": row.get("strike"),
            "spy_close_t": row.get("spy_close_t"),
            "straddle_mid_rel_t": row.get("straddle_mid_rel_t"),
            "spy_close_T": None,
            "terminal_move_rel": None,
            "terminal_followup_complete": False,
            "terminal_absence_reason": None,
            "censored_at_history_end": False,
        }
        if not available:
            result["terminal_absence_reason"] = "no_straddle_available"
            output_rows.append(result)
            continue

        expiration = pd.Timestamp(row["expiration"])
        if expiration > history_end:
            result["terminal_absence_reason"] = "expiration_after_available_price_history"
            result["censored_at_history_end"] = True
            output_rows.append(result)
            continue
        if expiration < history_start:
            result["terminal_absence_reason"] = "expiration_before_available_price_history"
            output_rows.append(result)
            continue
        if expiration not in closes.index:
            result["terminal_absence_reason"] = "no_spy_close_exactly_on_expiration"
            output_rows.append(result)
            continue

        close_t = float(row["spy_close_t"])
        strike = float(row["strike"])
        close_T = float(closes.loc[expiration])
        result["spy_close_T"] = close_T
        result["terminal_move_rel"] = abs(close_T - strike) / close_t
        result["terminal_followup_complete"] = True
        output_rows.append(result)

    aligned = pd.DataFrame(output_rows)
    audits = {
        "rows_total": len(aligned),
        "pairs_available": int(aligned["pair_available"].sum()),
        "expiration_closes_observed": int(aligned["terminal_followup_complete"].sum()),
        "censored_at_history_end": int(aligned["censored_at_history_end"].sum()),
        "no_exact_expiration_close": int((aligned["terminal_absence_reason"] == "no_spy_close_exactly_on_expiration").sum()),
        "no_straddle_available": int((aligned["terminal_absence_reason"] == "no_straddle_available").sum()),
        "price_history_start": history_start.date().isoformat(),
        "price_history_end": history_end.date().isoformat(),
    }
    if write_csv:
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        aligned.to_csv(OUTPUT_PATH, index=False)
    return {
        "aligned": aligned,
        "audit": audits,
        "input_path": INPUT_PATH,
        "price_path": PRICE_PATH,
        "output_path": OUTPUT_PATH,
    }


if __name__ == "__main__":
    result = align_terminal_move(write_csv=True)
    print(result["audit"])
    print(f"Wrote {len(result['aligned']):,} rows to {result['output_path']}")
