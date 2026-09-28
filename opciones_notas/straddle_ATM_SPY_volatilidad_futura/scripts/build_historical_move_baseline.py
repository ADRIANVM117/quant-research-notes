"""Construct a no-look-ahead historical movement baseline for each straddle row.

The contract selection is read from the frozen terminal-alignment CSV. H comes
only from session-calendar indices between t and the selected expiration T.
The price windows used for the baseline all end at or before t.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
HMM_ROOT = PROJECT_ROOT.parents[1] / "HMM_regime_options"
INPUT_PATH = PROJECT_ROOT / "data" / "derived" / "spy_atm30_straddle_terminal_move_rel_2020-01-02_2026-08-31.csv"
PRICE_PATH = HMM_ROOT / "data" / "derived" / "spy_daily_adjusted_2020_2026.csv"
OUTPUT_PATH = PROJECT_ROOT / "data" / "derived" / "spy_atm30_straddle_with_historical_move_baseline_2020-01-02_2026-08-31.csv"
WINDOW_COUNT_REQUIRED = 252


def _split_prefix(split_coefficients: np.ndarray) -> np.ndarray:
    """Prefix count of non-unit split records, for conservative window flags."""

    split_event = ~np.isclose(split_coefficients.astype(float), 1.0)
    return np.concatenate(([0], np.cumsum(split_event, dtype=int)))


def _window_has_split(prefix: np.ndarray, start_index: int, end_index: int) -> bool:
    """Flag any split record from the first through last close, inclusive."""

    return bool(prefix[end_index + 1] - prefix[start_index])


def build_historical_move_baseline(write_csv: bool = True) -> dict[str, Any]:
    """Return the aligned baseline table without any predictive comparison.

    If one of the 252 most recent historical windows includes a split record,
    the row remains missing and is explicitly flagged; no split-affected value
    is silently incorporated into the average.
    """

    source = pd.read_csv(INPUT_PATH, parse_dates=["observation_date", "expiration"])
    prices = pd.read_csv(PRICE_PATH, parse_dates=["date"]).sort_values("date").reset_index(drop=True)
    sessions = prices["date"].to_numpy(dtype="datetime64[ns]")
    closes = prices["close"].to_numpy(dtype=float)
    split_prefix = _split_prefix(prices["split_coefficient"].to_numpy(dtype=float))
    session_index = {pd.Timestamp(session): idx for idx, session in enumerate(sessions)}

    records: list[dict[str, Any]] = []
    for row in source.to_dict("records"):
        observation_date = pd.Timestamp(row["observation_date"])
        pair_available = bool(row["pair_available"])
        record = dict(row)
        record.update({
            "observation_session_index": None,
            "expiration_session_index": None,
            "h_sessions": None,
            "k_strike_over_spot_t": None,
            "historical_window_count": 0,
            "historical_first_window_start": None,
            "historical_first_window_end": None,
            "historical_last_window_start": None,
            "historical_last_window_end": None,
            "historical_split_affected_window_count": 0,
            "historical_dates_through_t_only": False,
            "historical_move_baseline_t": None,
            "historical_baseline_absence_reason": None,
        })
        if not pair_available:
            record["historical_baseline_absence_reason"] = "no_straddle_available"
            records.append(record)
            continue
        if observation_date not in session_index:
            record["historical_baseline_absence_reason"] = "observation_not_in_available_session_calendar"
            records.append(record)
            continue
        expiration = pd.Timestamp(row["expiration"])
        if expiration not in session_index:
            record["historical_baseline_absence_reason"] = "expiration_not_in_available_session_calendar"
            records.append(record)
            continue

        t_index = session_index[observation_date]
        T_index = session_index[expiration]
        H = T_index - t_index
        record["observation_session_index"] = t_index
        record["expiration_session_index"] = T_index
        record["h_sessions"] = H
        record["k_strike_over_spot_t"] = float(row["strike"]) / float(row["spy_close_t"])
        if H <= 0:
            record["historical_baseline_absence_reason"] = "nonpositive_session_horizon"
            records.append(record)
            continue

        # End indices u may run through t_index only. Thus every close read
        # for the baseline is at an index <= t_index; T contributes only H.
        available_end_indices = np.arange(H, t_index + 1, dtype=int)
        if len(available_end_indices) < WINDOW_COUNT_REQUIRED:
            record["historical_window_count"] = int(len(available_end_indices))
            if len(available_end_indices):
                first_end, last_end = available_end_indices[0], available_end_indices[-1]
                record["historical_first_window_start"] = pd.Timestamp(sessions[first_end - H])
                record["historical_first_window_end"] = pd.Timestamp(sessions[first_end])
                record["historical_last_window_start"] = pd.Timestamp(sessions[last_end - H])
                record["historical_last_window_end"] = pd.Timestamp(sessions[last_end])
                record["historical_dates_through_t_only"] = bool(last_end <= t_index)
            record["historical_baseline_absence_reason"] = "fewer_than_252_complete_historical_windows"
            records.append(record)
            continue

        selected_ends = available_end_indices[-WINDOW_COUNT_REQUIRED:]
        first_end, last_end = int(selected_ends[0]), int(selected_ends[-1])
        split_affected = sum(_window_has_split(split_prefix, int(end - H), int(end)) for end in selected_ends)
        record["historical_window_count"] = int(len(selected_ends))
        record["historical_first_window_start"] = pd.Timestamp(sessions[first_end - H])
        record["historical_first_window_end"] = pd.Timestamp(sessions[first_end])
        record["historical_last_window_start"] = pd.Timestamp(sessions[last_end - H])
        record["historical_last_window_end"] = pd.Timestamp(sessions[last_end])
        record["historical_split_affected_window_count"] = int(split_affected)
        record["historical_dates_through_t_only"] = bool(last_end <= t_index)
        if split_affected:
            record["historical_baseline_absence_reason"] = "split_affected_historical_windows_require_policy"
            records.append(record)
            continue

        k = record["k_strike_over_spot_t"]
        movements = np.abs(closes[selected_ends] / closes[selected_ends - H] - k)
        record["historical_move_baseline_t"] = float(np.mean(movements))
        records.append(record)

    aligned = pd.DataFrame(records)
    complete = aligned["historical_move_baseline_t"].notna()
    audit = {
        "rows_total": len(aligned),
        "pairs_available": int(aligned["pair_available"].sum()),
        "h_resolved_from_session_calendar": int(aligned["h_sessions"].notna().sum()),
        "baseline_with_252_windows": int(complete.sum()),
        "fewer_than_252_windows": int((aligned["historical_baseline_absence_reason"] == "fewer_than_252_complete_historical_windows").sum()),
        "expiration_not_in_session_calendar": int((aligned["historical_baseline_absence_reason"] == "expiration_not_in_available_session_calendar").sum()),
        "split_affected_rows": int((aligned["historical_split_affected_window_count"] > 0).sum()),
        "all_completed_windows_through_t": bool(aligned.loc[complete, "historical_dates_through_t_only"].all()),
        "price_history_start": pd.Timestamp(sessions[0]).date().isoformat(),
        "price_history_end": pd.Timestamp(sessions[-1]).date().isoformat(),
    }
    if write_csv:
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        aligned.to_csv(OUTPUT_PATH, index=False)
    return {
        "aligned": aligned,
        "audit": audit,
        "input_path": INPUT_PATH,
        "price_path": PRICE_PATH,
        "output_path": OUTPUT_PATH,
    }


if __name__ == "__main__":
    result = build_historical_move_baseline(write_csv=True)
    print(result["audit"])
    print(f"Wrote {len(result['aligned']):,} rows to {result['output_path']}")
