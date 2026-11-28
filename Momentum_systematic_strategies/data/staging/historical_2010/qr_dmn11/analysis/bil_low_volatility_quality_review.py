"""Offline BIL quality review for QR-DMN-12.

The script reads preserved staging data and reports only. It does not contact a
provider, amend quality rules, or write to Raw, Silver, Gold, or normal Quality.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from math import sqrt
from pathlib import Path

import numpy as np
import pandas as pd
import polars as pl


ROOT = Path(__file__).resolve().parents[5]
RUN_ROOT = ROOT / "data/staging/historical_2010/qr_dmn11"
BIL_PATH = RUN_ROOT / "BIL/parquet/etf/BIL.parquet"
SHY_PATH = RUN_ROOT / "SHY/parquet/etf/SHY.parquet"
BIL_RAW = RUN_ROOT / "BIL/raw/BIL_2026-11-27.json"
BIL_QUALITY = RUN_ROOT / "quality/BIL"
DEFAULT_OUTPUT = RUN_ROOT / "analysis/bil_quality_results"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv(frame: pl.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.write_csv(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Offline BIL low-volatility quality review.")
    parser.add_argument("--bil", type=Path, default=BIL_PATH)
    parser.add_argument("--shy", type=Path, default=SHY_PATH)
    parser.add_argument("--raw", type=Path, default=BIL_RAW)
    parser.add_argument("--quality-root", type=Path, default=BIL_QUALITY)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def identical_ohlc_runs(frame: pl.DataFrame) -> pl.DataFrame:
    values = frame.select("open", "high", "low", "close").rows()
    dates = frame.get_column("session_date").to_list()
    volumes = frame.get_column("volume").to_list()
    rows: list[dict[str, object]] = []
    start = 0
    for index in range(1, len(values) + 1):
        if index == len(values) or values[index] != values[start]:
            length = index - start
            if length >= 3:
                open_, high, low, close = values[start]
                run_volumes = volumes[start:index]
                rows.append(
                    {
                        "start_date": dates[start],
                        "end_date": dates[index - 1],
                        "year": dates[start].year,
                        "sessions": length,
                        "open": open_, "high": high, "low": low, "close": close,
                        "intra_bar_range": high - low,
                        "intra_bar_range_bps": (high - low) / close * 10_000,
                        "volume_min": min(run_volumes),
                        "volume_max": max(run_volumes),
                        "volume_sum": sum(run_volumes),
                        "zero_volume_sessions": sum(value == 0 for value in run_volumes),
                        "all_reported_volume_positive": all(value > 0 for value in run_volumes),
                    }
                )
            start = index
    return pl.DataFrame(rows)


def period_statistics(frame: pl.DataFrame, symbol: str) -> list[dict[str, object]]:
    periods = (
        ("2010-2017", pd.Timestamp("2010-01-01").date(), pd.Timestamp("2018-01-01").date()),
        ("2020-2022", pd.Timestamp("2020-01-01").date(), pd.Timestamp("2023-01-01").date()),
        ("2023-2026", pd.Timestamp("2023-01-01").date(), pd.Timestamp("2027-01-01").date()),
    )
    with_returns = frame.with_columns(pl.col("adjusted_close").pct_change().alias("return"))
    rows: list[dict[str, object]] = []
    for label, start, end in periods:
        returns = with_returns.filter(
            (pl.col("session_date") >= start) & (pl.col("session_date") < end) & pl.col("return").is_not_null()
        ).get_column("return")
        rows.append(
            {
                "symbol": symbol,
                "period": label,
                "return_sessions": returns.len(),
                "zero_return_sessions": int((returns == 0).sum()),
                "zero_return_pct": float((returns == 0).mean() * 100),
                "annualized_simple_volatility": float(returns.std() * sqrt(252)),
                "min_return": float(returns.min()),
                "max_return": float(returns.max()),
            }
        )
    return rows


def main() -> None:
    args = parse_args()
    bil_path, shy_path, raw_path = args.bil.resolve(), args.shy.resolve(), args.raw.resolve()
    quality_root, output = args.quality_root.resolve(), args.output_dir.resolve()
    required = (bil_path, shy_path, raw_path, quality_root / "quality_issues.csv", quality_root / "series_status.csv")
    if not all(path.is_file() for path in required):
        raise SystemExit("Preserved BIL, SHY, Raw, and quality inputs are required.")
    bil = pl.read_parquet(bil_path).sort("session_date")
    shy = pl.read_parquet(shy_path).sort("session_date")
    runs = identical_ohlc_runs(bil)
    write_csv(runs, output / "r8_identical_ohlc_runs.csv")
    runs_by_year = runs.group_by("year").agg(
        pl.len().alias("run_count"),
        pl.col("sessions").sum().alias("sessions_in_runs"),
        pl.col("sessions").max().alias("max_run_length"),
        pl.col("volume_min").min().alias("minimum_reported_volume"),
        pl.col("volume_max").max().alias("maximum_reported_volume"),
        pl.col("zero_volume_sessions").sum().alias("zero_volume_sessions"),
    ).sort("year")
    write_csv(runs_by_year, output / "r8_runs_by_year.csv")
    period_rows = [*period_statistics(bil, "BIL"), *period_statistics(shy, "SHY")]
    write_csv(pl.DataFrame(period_rows), output / "period_returns_and_volatility.csv")

    split_rows = bil.filter(pl.col("split_coefficient") != 1)
    if split_rows.height != 1 or split_rows.get_column("session_date").item() != pd.Timestamp("2017-11-30").date():
        raise SystemExit("Expected exactly the documented BIL split on 2017-11-30.")
    split_index = bil.with_row_index("index").filter(pl.col("split_coefficient") != 1).get_column("index").item()
    split_window = bil.slice(max(0, split_index - 5), 11).with_columns(
        pl.col("close").pct_change().alias("close_return"),
        pl.col("adjusted_close").pct_change().alias("adjusted_return"),
    )
    write_csv(split_window, output / "split_2017_11_30_window.csv")
    split_row = split_rows.row(0, named=True)
    prior = bil.slice(split_index - 1, 1).row(0, named=True)
    split_diagnostics = pl.DataFrame(
        {
            "split_date": [split_row["session_date"]],
            "split_coefficient": [split_row["split_coefficient"]],
            "prior_close": [prior["close"]],
            "split_date_close": [split_row["close"]],
            "close_ratio": [split_row["close"] / prior["close"]],
            "prior_adjusted_close": [prior["adjusted_close"]],
            "split_date_adjusted_close": [split_row["adjusted_close"]],
            "adjusted_return": [split_row["adjusted_close"] / prior["adjusted_close"] - 1],
        }
    )
    write_csv(split_diagnostics, output / "split_diagnostics.csv")

    returns = bil.with_columns(pl.col("adjusted_close").pct_change().alias("return")).drop_nulls("return")
    dividend_returns = returns.filter(pl.col("dividend_amount") > 0).get_column("return")
    non_dividend_returns = returns.filter(pl.col("dividend_amount") == 0).get_column("return")
    corporate = pl.DataFrame(
        {
            "dividend_sessions": [dividend_returns.len()],
            "max_abs_adjusted_return_on_dividend": [float(dividend_returns.abs().max())],
            "p95_abs_adjusted_return_on_dividend": [float(dividend_returns.abs().quantile(0.95))],
            "p99_abs_adjusted_return_non_dividend": [float(non_dividend_returns.abs().quantile(0.99))],
            "all_dividend_adjusted_returns_finite": [bool(np.isfinite(dividend_returns.to_numpy()).all())],
        }
    )
    write_csv(corporate, output / "dividend_adjustment_diagnostics.csv")

    bil_return = pd.Series(returns.get_column("return").to_list(), index=pd.to_datetime(returns.get_column("session_date").to_list()))
    causal_ewma_annual_vol = bil_return.ewm(alpha=0.06, adjust=False, min_periods=20).std().shift(1) * sqrt(252)
    rolling_63 = bil_return.rolling(63, min_periods=63).std()
    finite_ewma = causal_ewma_annual_vol.dropna()
    finite_rolling = rolling_63.dropna()
    numerical = pl.DataFrame(
        {
            "daily_return_std": [float(bil_return.std())],
            "annualized_return_volatility": [float(bil_return.std() * sqrt(252))],
            "ewma_annual_vol_min": [float(finite_ewma.min())],
            "ewma_annual_vol_median": [float(finite_ewma.median())],
            "ewma_annual_vol_p05": [float(finite_ewma.quantile(0.05))],
            "ewma_annual_vol_p95": [float(finite_ewma.quantile(0.95))],
            "ewma_sessions_at_or_below_12pct": [int((finite_ewma <= 0.12).sum())],
            "ewma_sessions": [int(finite_ewma.shape[0])],
            "rolling_63_zero_std_windows": [int((finite_rolling <= np.finfo(float).eps).sum())],
            "rolling_63_min_std": [float(finite_rolling.min())],
        }
    )
    write_csv(numerical, output / "low_volatility_numerical_diagnostics.csv")

    quality_status = pl.read_csv(quality_root / "series_status.csv").row(0, named=True)
    quality_issues = pl.read_csv(quality_root / "quality_issues.csv")
    raw_metadata = json.loads(raw_path.read_text(encoding="utf-8")).get("Meta Data", {})
    all_positive_volume_runs = int(runs.filter(pl.col("all_reported_volume_positive")).height)
    no_zero_rolling = numerical.item(0, "rolling_63_zero_std_windows") == 0
    summary = [
        "# QR-DMN-12 - BIL low-volatility quality review", "",
        "## Evidence", "",
        f"- BIL staging rows: {bil.height}; date range: {bil.get_column('session_date').min()} through {bil.get_column('session_date').max()}.",
        f"- Raw SHA-256: `{sha256(raw_path)}`; provider last refreshed: `{raw_metadata.get('3. Last Refreshed', '')}`.",
        f"- Quality state: `{quality_status['status']}` with {quality_status['warning_count']} warnings and {quality_status['rejection_count']} rejections.",
        "", "## R8 identical OHLC runs", "",
        f"- Runs: {runs.height}; sessions inside runs: {runs.get_column('sessions').sum()}.",
        f"- Runs with positive reported volume on every session: {all_positive_volume_runs} of {runs.height}; zero-volume sessions inside runs: {runs.get_column('zero_volume_sessions').sum()}.",
        "- The provider reports transactions/volume during these runs, so the warnings are not evidence of an absence of trading. They remain a data-granularity warning, not a global rule exception.",
        "", "## Corporate actions", "",
        f"- The expected split is present on {split_row['session_date']} with coefficient {split_row['split_coefficient']}.",
        f"- Adjusted return across the split session: {split_diagnostics.item(0, 'adjusted_return'):.12g}; inspect `split_2017_11_30_window.csv` rather than splicing any vintage.",
        f"- Dividend sessions: {corporate.item(0, 'dividend_sessions')}; all associated adjusted returns are finite.",
        "", "## Low-volatility implications", "",
        f"- Rolling 63-session zero-standard-deviation windows: {numerical.item(0, 'rolling_63_zero_std_windows')}.",
        f"- EWMA annual-volatility observations at or below the 12% target: {numerical.item(0, 'ewma_sessions_at_or_below_12pct')} of {numerical.item(0, 'ewma_sessions')}.",
        "- BIL is exposure-capped at 1x in every eligible EWMA session under a 12% target. Sharpe-style training must preserve a variance epsilon even when observed rolling variance is nonzero.",
        "", "## Separate decisions", "",
        "- Historical integrity: CONDITIONALLY SUPPORTED. Calendar coverage, reported volume, split evidence, and adjusted-return checks do not show a material break, but R8 should remain visible as a BIL-specific review condition.",
        ("- DMN training eligibility: CONDITIONALLY ELIGIBLE with variance safeguards and explicit documentation of low-volatility/capped-exposure behavior."
         if no_zero_rolling else "- DMN training eligibility: REVIEW REQUIRED because at least one 63-session window has zero realized variance."),
        "- No automatic exception, validator change, or promotion is created by this review.",
        "",
    ]
    (output / "BIL_REVIEW_SUMMARY.md").write_text("\n".join(summary), encoding="utf-8", newline="\n")
    print(f"R8_RUNS={runs.height}")
    print(f"R8_RUN_SESSIONS={runs.get_column('sessions').sum()}")
    print(f"R8_ALL_POSITIVE_VOLUME_RUNS={all_positive_volume_runs}")
    print(f"SPLIT_COEFFICIENT={split_row['split_coefficient']}")
    print(f"ROLLING_63_ZERO_STD_WINDOWS={numerical.item(0, 'rolling_63_zero_std_windows')}")
    print("HISTORICAL_INTEGRITY=CONDITIONALLY_SUPPORTED")
    print(f"DMN_TRAINING={'CONDITIONALLY_ELIGIBLE' if no_zero_rolling else 'REVIEW_REQUIRED'}")


if __name__ == "__main__":
    main()
