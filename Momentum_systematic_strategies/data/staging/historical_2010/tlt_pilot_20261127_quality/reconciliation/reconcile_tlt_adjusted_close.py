"""Offline reconciliation of the historical TLT adjusted-close vintages.

This diagnostic never contacts a provider and never writes to Raw, Silver, or
Gold.  It compares only the isolated TLT staging Parquet with the pre-existing
Silver Parquet and records compact evidence in the requested output directory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import exchange_calendars as xcals
import pandas as pd
import polars as pl


ROOT = Path(__file__).resolve().parents[5]
STAGING = ROOT / "data/staging/historical_2010/tlt_pilot_20261127"
QUALITY = ROOT / "data/staging/historical_2010/tlt_pilot_20261127_quality"
DEFAULT_STAGING = STAGING / "parquet/etf/TLT.parquet"
DEFAULT_SILVER = ROOT / "data/parquet/etf/TLT.parquet"
DEFAULT_RAW = STAGING / "raw/TLT_2026-11-27.json"
DEFAULT_OUTPUT = QUALITY / "reconciliation/results"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv(frame: pl.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.write_csv(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Offline TLT adjusted-close reconciliation.")
    parser.add_argument("--staging", type=Path, default=DEFAULT_STAGING)
    parser.add_argument("--silver", type=Path, default=DEFAULT_SILVER)
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    staging_path = args.staging.resolve()
    silver_path = args.silver.resolve()
    raw_path = args.raw.resolve()
    output_dir = args.output_dir.resolve()
    if not all(path.is_file() for path in (staging_path, silver_path, raw_path)):
        raise SystemExit("Staging Parquet, Silver Parquet, and preserved Raw JSON are required.")

    staging = pl.read_parquet(staging_path).select(
        "session_date", "close", "adjusted_close", "dividend_amount", "split_coefficient"
    ).sort("session_date")
    silver = pl.read_parquet(silver_path).select("session_date", "adjusted_close").sort("session_date")
    overlap = staging.join(silver, on="session_date", how="inner", suffix="_silver").sort("session_date")
    overlap = overlap.with_columns(
        (pl.col("adjusted_close") / pl.col("adjusted_close_silver")).alias("scale_ratio")
    )
    if overlap.height < 2:
        raise SystemExit("At least two overlapping sessions are required.")

    ratio_stats = overlap.select(
        pl.len().alias("overlap_sessions"),
        pl.col("scale_ratio").min().alias("ratio_min"),
        pl.col("scale_ratio").median().alias("ratio_median"),
        pl.col("scale_ratio").max().alias("ratio_max"),
        pl.col("scale_ratio").std().alias("ratio_std"),
        pl.col("scale_ratio").quantile(0.25).alias("ratio_q25"),
        pl.col("scale_ratio").quantile(0.75).alias("ratio_q75"),
    )
    write_csv(ratio_stats, output_dir / "ratio_summary.csv")
    ratio_by_year = overlap.with_columns(pl.col("session_date").dt.year().alias("year")).group_by("year").agg(
        pl.len().alias("sessions"),
        pl.col("scale_ratio").min().alias("ratio_min"),
        pl.col("scale_ratio").median().alias("ratio_median"),
        pl.col("scale_ratio").max().alias("ratio_max"),
        pl.col("scale_ratio").std().alias("ratio_std"),
    ).sort("year")
    write_csv(ratio_by_year, output_dir / "ratio_by_year.csv")

    returns = overlap.with_columns(
        pl.col("adjusted_close").pct_change().alias("simple_return_staging"),
        pl.col("adjusted_close_silver").pct_change().alias("simple_return_silver"),
        (pl.col("adjusted_close").log() - pl.col("adjusted_close").shift(1).log()).alias("log_return_staging"),
        (pl.col("adjusted_close_silver").log() - pl.col("adjusted_close_silver").shift(1).log()).alias("log_return_silver"),
    ).with_columns(
        (pl.col("simple_return_staging") - pl.col("simple_return_silver")).alias("simple_return_difference"),
        (pl.col("log_return_staging") - pl.col("log_return_silver")).alias("log_return_difference"),
    ).drop_nulls()
    returns = returns.with_columns(
        pl.col("simple_return_difference").abs().alias("abs_simple_return_difference"),
        pl.col("log_return_difference").abs().alias("abs_log_return_difference"),
    )
    return_summary = returns.select(
        pl.len().alias("return_pairs"),
        pl.col("abs_simple_return_difference").max().alias("simple_abs_max"),
        pl.col("abs_simple_return_difference").median().alias("simple_abs_median"),
        pl.col("abs_simple_return_difference").quantile(0.95).alias("simple_abs_p95"),
        pl.col("abs_simple_return_difference").quantile(0.99).alias("simple_abs_p99"),
        pl.col("abs_log_return_difference").max().alias("log_abs_max"),
        pl.col("abs_log_return_difference").median().alias("log_abs_median"),
        pl.col("abs_log_return_difference").quantile(0.95).alias("log_abs_p95"),
        pl.col("abs_log_return_difference").quantile(0.99).alias("log_abs_p99"),
    )
    write_csv(return_summary, output_dir / "return_difference_summary.csv")
    write_csv(
        returns.sort("abs_log_return_difference", descending=True).head(20).select(
            "session_date", "simple_return_staging", "simple_return_silver",
            "simple_return_difference", "log_return_staging", "log_return_silver",
            "log_return_difference", "abs_log_return_difference",
        ),
        output_dir / "largest_return_differences.csv",
    )

    silver_end = silver.get_column("session_date").max()
    staging_with_prior_close = staging.with_columns(
        pl.col("close").shift(1).alias("prior_close")
    )
    post_silver_dividends = staging_with_prior_close.filter(
        (pl.col("session_date") > silver_end) & (pl.col("dividend_amount") > 0)
    ).with_columns(
        (1 - pl.col("dividend_amount") / pl.col("prior_close")).alias(
            "candidate_dividend_factor"
        ),
        (pl.lit(ratio_stats.item(0, "ratio_median")) - (1 - pl.col("dividend_amount") / pl.col("prior_close"))).alias(
            "observed_ratio_minus_candidate_factor"
        ),
    )
    write_csv(post_silver_dividends, output_dir / "dividends_after_silver_end.csv")
    boundary = staging.with_columns(
        pl.col("adjusted_close").pct_change().alias("staging_simple_return")
    ).filter(
        (pl.col("session_date") >= silver_end - pd.Timedelta(days=10).to_pytimedelta())
        & (pl.col("session_date") <= silver_end + pd.Timedelta(days=20).to_pytimedelta())
    )
    write_csv(boundary, output_dir / "staging_boundary_continuity.csv")

    calendar = xcals.get_calendar("XNYS")
    start = staging.get_column("session_date").min()
    end = staging.get_column("session_date").max()
    expected = {stamp.date() for stamp in calendar.sessions_in_range(pd.Timestamp(start), pd.Timestamp(end))}
    observed = set(staging.get_column("session_date").to_list())
    missing = sorted(expected - observed)
    extraordinary = sorted(observed - expected)
    calendar_summary = pl.DataFrame({
        "calendar": ["XNYS"], "start_date": [start], "end_date": [end],
        "expected_sessions": [len(expected)], "observed_sessions": [len(observed)],
        "missing_sessions": [len(missing)], "extraordinary_dates": [len(extraordinary)],
    })
    write_csv(calendar_summary, output_dir / "calendar_coverage_summary.csv")
    write_csv(pl.DataFrame({"session_date": missing}), output_dir / "calendar_missing_sessions.csv")
    write_csv(pl.DataFrame({"session_date": extraordinary}), output_dir / "calendar_extraordinary_dates.csv")

    ratio = ratio_stats.row(0, named=True)
    ret = return_summary.row(0, named=True)
    ratio_range = ratio["ratio_max"] - ratio["ratio_min"]
    if post_silver_dividends.height:
        latest_dividend = post_silver_dividends.row(-1, named=True)
        dividend_detail = (
            f"- On {latest_dividend['session_date']}, the simple prior-close dividend factor is "
            f"{latest_dividend['candidate_dividend_factor']:.12f}; the observed historical ratio differs by "
            f"{latest_dividend['observed_ratio_minus_candidate_factor']:.12g}. This is similar in magnitude, "
            "but not exact and is not causal proof."
        )
    else:
        dividend_detail = "- No positive dividend after the Silver endpoint was available for an arithmetic comparison."
    return_tolerance = 1e-10
    return_consistent = ret["log_abs_max"] <= return_tolerance
    decision = (
        "INNOCUOUS_SCALE_FOR_RETURNS" if return_consistent else "REVIEW_REQUIRED"
    )
    raw_metadata = json.loads(raw_path.read_text(encoding="utf-8")).get("Meta Data", {})
    summary = [
        "# TLT adjusted-close reconciliation", "",
        "## Inputs", "",
        f"- Staging Parquet SHA-256: `{sha256(staging_path)}`",
        f"- Silver Parquet SHA-256: `{sha256(silver_path)}`",
        f"- Preserved Raw SHA-256: `{sha256(raw_path)}`",
        f"- Provider metadata last refreshed: `{raw_metadata.get('3. Last Refreshed', '')}`",
        "", "## Scale ratio", "",
        f"- Overlap sessions: {ratio['overlap_sessions']}",
        f"- Min / median / max: {ratio['ratio_min']:.12f} / {ratio['ratio_median']:.12f} / {ratio['ratio_max']:.12f}",
        f"- Standard deviation: {ratio['ratio_std']:.12g}; range: {ratio_range:.12g}",
        "- Annual detail is in `ratio_by_year.csv`.",
        "", "## Return comparison", "",
        f"- Return pairs: {ret['return_pairs']}",
        f"- Maximum absolute simple-return difference: {ret['simple_abs_max']:.12g}",
        f"- Maximum absolute log-return difference: {ret['log_abs_max']:.12g}",
        f"- Absolute log-return p95 / p99: {ret['log_abs_p95']:.12g} / {ret['log_abs_p99']:.12g}",
        "- Largest differences are listed in `largest_return_differences.csv`.",
        "", "## Post-Silver dividends and boundary", "",
        f"- Silver ends on {silver_end}; staging has {post_silver_dividends.height} positive-dividend sessions after that date.",
        "- `dividends_after_silver_end.csv` contrasts the observed historical ratio with a simple prior-close dividend factor. It is an arithmetic compatibility check, not causal attribution.",
        dividend_detail,
        "- `staging_boundary_continuity.csv` uses the staging vintage alone; no synthetic splice was created.",
        "", "## Calendar coverage", "",
        f"- XNYS expected / observed: {len(expected)} / {len(observed)}.",
        f"- Missing XNYS sessions: {len(missing)}; extraordinary observed dates: {len(extraordinary)}.",
        "", "## Decision", "",
        f"- `{decision}`.",
    ]
    if return_consistent:
        summary.append("- Within the recorded numerical tolerance, the adjusted-close difference preserves daily returns and behaves as a scale transformation.")
    else:
        summary.append("- The adjusted-close difference changes at least some daily returns beyond the recorded numerical tolerance; a canonical-series decision needs additional review before promotion.")
    summary.append("")
    (output_dir / "RECONCILIATION_SUMMARY.md").write_text("\n".join(summary), encoding="utf-8", newline="\n")

    print(f"OVERLAP_SESSIONS={ratio['overlap_sessions']}")
    print(f"RATIO_MIN={ratio['ratio_min']:.12f}")
    print(f"RATIO_MEDIAN={ratio['ratio_median']:.12f}")
    print(f"RATIO_MAX={ratio['ratio_max']:.12f}")
    print(f"LOG_RETURN_MAX_ABS_DIFF={ret['log_abs_max']:.12g}")
    print(f"XNYS_MISSING={len(missing)}")
    print(f"XNYS_EXTRAORDINARY={len(extraordinary)}")
    print(f"DECISION={decision}")


if __name__ == "__main__":
    main()
