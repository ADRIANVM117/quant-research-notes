"""Offline audit for the QR-DMN-11 isolated historical universe.

Reads only isolated staging files plus existing Gold/Silver references.  It
never contacts a provider and never writes to Raw, Silver, Gold, or Quality.
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
RUN_ROOT = ROOT / "data/staging/historical_2010/qr_dmn11"
TLT_ROOT = ROOT / "data/staging/historical_2010/tlt_pilot_20261127"
GOLD_ROOT = ROOT / "data/gold/daily_series/etf"
SILVER_ROOT = ROOT / "data/parquet/etf"
SYMBOLS = ("SPY", "QQQ", "IWM", "IWD", "IWF", "XLE", "XLF", "GLD", "SHY", "BIL")
ALL_SYMBOLS = (*SYMBOLS, "TLT")
FROZEN_GOLD = {
    "GLD": "bf1a21fd3f5e4f3a2f2464a4bbfe6dfa4912d845d108bb617927293d7009739c",
    "IWD": "d73576d8c83dcbe57392174cb341061321ab963cd4adbdd063f455342caea0e0",
    "IWF": "d0c4165277bc9167421dde15ef9ede395bc35d259326de22913a76ef5792314e",
    "IWM": "7913707e8a33b60780a7fe93617eb8114ef71b0e66e6a3b0b4dbab752cf09523",
    "QQQ": "69760c426b11238aca1f1200f1c44933938954115d944db3b5a3df77618475fc",
    "SPY": "b0767b45c2d67dbe8d99e11e1603682fd28468c31de65d037a4c0a50fefa67e9",
    "XLE": "f98e7468b5aee758298229a14443818ea0148bc46b26042a02abe1dee9af7a5a",
    "XLF": "52612673ab44bb3e222d5ac208bd3b9dfd0871c2259ff9fb472c59d902f170e0",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv(frame: pl.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.write_csv(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Offline QR-DMN-11 reconciliation.")
    parser.add_argument("--run-root", type=Path, default=RUN_ROOT)
    parser.add_argument("--output-dir", type=Path, default=RUN_ROOT / "analysis/results")
    return parser.parse_args()


def staging_paths(run_root: Path, symbol: str) -> tuple[Path, Path]:
    if symbol == "TLT":
        return (
            TLT_ROOT / "parquet/etf/TLT.parquet",
            TLT_ROOT / "raw/TLT_2026-11-27.json",
        )
    return (
        run_root / symbol / "parquet/etf" / f"{symbol}.parquet",
        run_root / symbol / "raw" / f"{symbol}_2026-11-27.json",
    )


def reference_path(symbol: str) -> tuple[str, Path | None]:
    gold = GOLD_ROOT / f"{symbol}.parquet"
    silver = SILVER_ROOT / f"{symbol}.parquet"
    if gold.exists():
        return "Gold", gold
    if silver.exists():
        return "Silver", silver
    return "None", None


def main() -> None:
    args = parse_args()
    run_root = args.run_root.resolve()
    output_dir = args.output_dir.resolve()
    calendar = xcals.get_calendar("XNYS")
    universe_rows: list[dict[str, object]] = []
    reconciliation_rows: list[dict[str, object]] = []
    calendar_rows: list[dict[str, object]] = []
    provenance_rows: list[dict[str, object]] = []
    quality_rows: list[dict[str, object]] = []
    frozen_gold_rows: list[dict[str, str]] = []
    date_sets: dict[str, set[object]] = {}

    for symbol in ALL_SYMBOLS:
        parquet_path, raw_path = staging_paths(run_root, symbol)
        if not parquet_path.is_file() or not raw_path.is_file():
            raise SystemExit(f"Missing isolated staging input for {symbol}.")
        frame = pl.read_parquet(parquet_path).sort("session_date")
        dates = frame.get_column("session_date").to_list()
        date_sets[symbol] = set(dates)
        start, end = dates[0], dates[-1]
        expected_dates = {
            session.date()
            for session in calendar.sessions_in_range(pd.Timestamp(start), pd.Timestamp(end))
        }
        observed_dates = set(dates)
        missing = sorted(expected_dates - observed_dates)
        extra = sorted(observed_dates - expected_dates)
        universe_rows.append(
            {
                "symbol": symbol,
                "rows": frame.height,
                "start_date": start,
                "end_date": end,
                "adjusted_close_nulls": frame.get_column("adjusted_close").null_count(),
                "positive_dividend_sessions": frame.filter(pl.col("dividend_amount") > 0).height,
                "non_unit_split_sessions": frame.filter(pl.col("split_coefficient") != 1).height,
                "staged_parquet_sha256": sha256(parquet_path),
            }
        )
        calendar_rows.append(
            {
                "symbol": symbol,
                "calendar": "XNYS",
                "expected_sessions": len(expected_dates),
                "observed_sessions": len(observed_dates),
                "missing_sessions": len(missing),
                "extraordinary_dates": len(extra),
                "missing_dates": ";".join(map(str, missing)),
                "extraordinary_dates_list": ";".join(map(str, extra)),
            }
        )
        payload = json.loads(raw_path.read_text(encoding="utf-8"))
        metadata = payload.get("Meta Data", {})
        provenance_rows.append(
            {
                "symbol": symbol,
                "raw_relative_path": raw_path.relative_to(ROOT).as_posix(),
                "raw_sha256": sha256(raw_path),
                "raw_size_bytes": raw_path.stat().st_size,
                "provider_last_refreshed": metadata.get("3. Last Refreshed", ""),
                "provider_timezone": metadata.get("5. Time Zone", ""),
                "parquet_relative_path": parquet_path.relative_to(ROOT).as_posix(),
                "parquet_sha256": sha256(parquet_path),
            }
        )
        if symbol != "TLT":
            status_path = run_root / "quality" / symbol / "series_status.csv"
            issues_path = run_root / "quality" / symbol / "quality_issues.csv"
            status = pl.read_csv(status_path).row(0, named=True)
            issues = pl.read_csv(issues_path)
            quality_rows.append(
                {
                    "symbol": symbol,
                    "status": status["status"],
                    "rejection_count": status["rejection_count"],
                    "warning_count": status["warning_count"],
                    "missing_session_count": status["missing_session_count"],
                    "identical_bar_run_count": status["identical_bar_run_count"],
                    "quality_issue_rules": ";".join(issues.get_column("rule_id").unique().sort().to_list()) if issues.height else "",
                }
            )

        layer, reference = reference_path(symbol)
        if reference is None:
            reconciliation_rows.append(
                {
                    "symbol": symbol,
                    "reference_layer": "None",
                    "reference_path": "",
                    "overlap_sessions": 0,
                    "ratio_min": None,
                    "ratio_median": None,
                    "ratio_max": None,
                    "ratio_std": None,
                    "max_abs_log_return_difference": None,
                    "dividend_field_mismatches": None,
                    "split_field_mismatches": None,
                    "post_reference_dividend_sessions": None,
                    "classification": "NO_PRIOR_REFERENCE",
                }
            )
            continue
        staged = frame.select("session_date", "adjusted_close", "dividend_amount", "split_coefficient")
        prior = pl.read_parquet(reference).select(
            "session_date", "adjusted_close", "dividend_amount", "split_coefficient"
        )
        overlap = staged.join(prior, on="session_date", how="inner", suffix="_reference").sort("session_date")
        overlap = overlap.with_columns(
            (pl.col("adjusted_close") / pl.col("adjusted_close_reference")).alias("ratio")
        )
        returns = overlap.with_columns(
            (pl.col("adjusted_close").log() - pl.col("adjusted_close").shift(1).log()).alias("log_return_staged"),
            (pl.col("adjusted_close_reference").log() - pl.col("adjusted_close_reference").shift(1).log()).alias("log_return_reference"),
        ).drop_nulls()
        ratio = overlap.select(
            pl.col("ratio").min().alias("min"), pl.col("ratio").median().alias("median"),
            pl.col("ratio").max().alias("max"), pl.col("ratio").std().alias("std"),
        ).row(0, named=True)
        max_return_diff = returns.select(
            (pl.col("log_return_staged") - pl.col("log_return_reference")).abs().max().alias("max")
        ).item()
        dividend_mismatches = overlap.filter(
            pl.col("dividend_amount") != pl.col("dividend_amount_reference")
        ).height
        split_mismatches = overlap.filter(
            pl.col("split_coefficient") != pl.col("split_coefficient_reference")
        ).height
        reference_end = prior.get_column("session_date").max()
        post_dividends = staged.filter(
            (pl.col("session_date") > reference_end) & (pl.col("dividend_amount") > 0)
        ).height
        classification = (
            "RETURNS_EQUIVALENT_CONSTANT_SCALE"
            if max_return_diff <= 1e-10 and (ratio["max"] - ratio["min"]) <= 1e-10
            else "RETURN_OR_SCALE_REVIEW_REQUIRED"
        )
        reconciliation_rows.append(
            {
                "symbol": symbol,
                "reference_layer": layer,
                "reference_path": reference.relative_to(ROOT).as_posix(),
                "overlap_sessions": overlap.height,
                "ratio_min": ratio["min"],
                "ratio_median": ratio["median"],
                "ratio_max": ratio["max"],
                "ratio_std": ratio["std"],
                "max_abs_log_return_difference": max_return_diff,
                "dividend_field_mismatches": dividend_mismatches,
                "split_field_mismatches": split_mismatches,
                "post_reference_dividend_sessions": post_dividends,
                "classification": classification,
            }
        )

    common = set.intersection(*date_sets.values())
    common_sorted = sorted(common)
    for symbol, expected_hash in FROZEN_GOLD.items():
        gold_path = GOLD_ROOT / f"{symbol}.parquet"
        actual_hash = sha256(gold_path)
        if actual_hash != expected_hash:
            raise SystemExit(f"Frozen Gold changed during QR-DMN-11: {symbol}")
        frozen_gold_rows.append(
            {
                "symbol": symbol,
                "gold_relative_path": gold_path.relative_to(ROOT).as_posix(),
                "expected_sha256": expected_hash,
                "actual_sha256": actual_hash,
                "match": "YES",
            }
        )
    intersection = pl.DataFrame(
        {
            "instruments": [len(ALL_SYMBOLS)],
            "common_sessions": [len(common_sorted)],
            "common_start": [common_sorted[0]],
            "common_end": [common_sorted[-1]],
        }
    )
    write_csv(pl.DataFrame(universe_rows).sort("symbol"), output_dir / "universe_coverage.csv")
    write_csv(pl.DataFrame(reconciliation_rows).sort("symbol"), output_dir / "reference_reconciliation.csv")
    write_csv(pl.DataFrame(calendar_rows).sort("symbol"), output_dir / "calendar_coverage.csv")
    write_csv(pl.DataFrame(provenance_rows).sort("symbol"), output_dir / "raw_provenance.csv")
    write_csv(pl.DataFrame(quality_rows).sort("symbol"), output_dir / "quality_summary.csv")
    write_csv(pl.DataFrame(frozen_gold_rows).sort("symbol"), output_dir / "frozen_gold_integrity.csv")
    write_csv(intersection, output_dir / "eleven_instrument_intersection.csv")

    classes = pl.DataFrame(reconciliation_rows).group_by("classification").len().sort("classification")
    summary = [
        "# QR-DMN-11 isolated historical universe", "",
        "## Acquisition boundary", "",
        "- Ten authorized `TIME_SERIES_DAILY_ADJUSTED` requests were made once each: SPY, QQQ, IWM, IWD, IWF, XLE, XLF, GLD, SHY, and BIL.",
        "- All were written under isolated staging with `--no-promote`; Raw, Silver, Gold, and normal Quality locations were not changed.",
        "- TLT is incorporated as the prior QR-DMN-09 isolated staging series only.",
        "", "## Coverage", "",
        f"- Eleven-instrument common intersection: {len(common_sorted)} XNYS sessions, {common_sorted[0]} through {common_sorted[-1]}.",
        "- Individual coverage and corporate-action counts: `universe_coverage.csv`.",
        "- XNYS completeness by staged instrument: `calendar_coverage.csv`.",
        "- The eight frozen Gold files still match their pre-acquisition SHA-256 baseline: `frozen_gold_integrity.csv`.",
        "", "## Quality", "",
        "- Per-symbol quality state: `quality_summary.csv`.",
        "- A `SUBGOLD_REVIEW` state remains staging-only and is not a promotion decision.",
        "", "## Reference reconciliation", "",
        "- Existing Gold is preferred as reference; Silver is used only where Gold is absent.",
        "- Ratio, return, dividend, and split comparisons: `reference_reconciliation.csv`.",
        "- `RETURNS_EQUIVALENT_CONSTANT_SCALE` means the staged and prior adjusted-close returns agree under the fixed diagnostic tolerance; it does not authorize combining raw price levels or promoting data.",
        "", "## Limits", "",
        "- No canonical vintage was selected, no adjusted-close series were merged, and no instrument was promoted to Gold.",
        "- Any later promotion requires separate review of quality status and reference-vintage policy.",
        "",
    ]
    (output_dir / "ANALYSIS_SUMMARY.md").write_text("\n".join(summary), encoding="utf-8", newline="\n")
    print(f"INSTRUMENTS={len(ALL_SYMBOLS)}")
    print(f"COMMON_SESSIONS={len(common_sorted)}")
    print(f"COMMON_START={common_sorted[0]}")
    print(f"COMMON_END={common_sorted[-1]}")
    for row in classes.to_dicts():
        print(f"{row['classification']}={row['len']}")


if __name__ == "__main__":
    main()
