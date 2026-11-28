"""One-command daily ingestion and quality gate for a portable research project."""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import date
from pathlib import Path

from alpha_vantage_daily import (
    START_DATE,
    require_historical_staging,
    require_versioned_gold_destination,
    update_isolated_daily,
)


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download one daily adjusted series, then validate and promote it to Gold."
    )
    parser.add_argument("--symbol", required=True, help="Alpha Vantage symbol, e.g. SPY")
    parser.add_argument("--asset-class", required=True, choices=("equity", "etf"))
    parser.add_argument(
        "--expected-session-date",
        required=True,
        type=date.fromisoformat,
        help="Latest session that must be present, in YYYY-MM-DD. Use the last completed US session.",
    )
    parser.add_argument(
        "--start-date",
        type=date.fromisoformat,
        default=START_DATE,
        help="Earliest retained session; defaults to 2018-01-01 for ordinary updates.",
    )
    parser.add_argument(
        "--destination-root",
        type=Path,
        help="Isolated data root for a historical backfill. Required when --start-date is before 2018-01-01.",
    )
    parser.add_argument(
        "--quality-root",
        type=Path,
        help="Isolated quality-report root for a historical backfill.",
    )
    parser.add_argument(
        "--gold-root",
        type=Path,
        help="Explicit versioned Gold root; required only for a historical promotion.",
    )
    parser.add_argument(
        "--no-promote",
        action="store_true",
        help="Validate only; never write Gold.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    historical = args.start_date < START_DATE
    destination_root = (args.destination_root or ROOT / "data").resolve()
    quality_root = (args.quality_root or ROOT / "data" / "quality").resolve()

    if historical:
        if args.destination_root is None:
            raise SystemExit("Historical backfill requires an explicit isolated --destination-root.")
        if args.quality_root is None:
            raise SystemExit("Historical backfill requires an explicit isolated --quality-root.")
        try:
            destination_root = require_historical_staging(destination_root, "--destination-root")
            quality_root = require_historical_staging(quality_root, "--quality-root")
        except Exception as exc:
            raise SystemExit(str(exc)) from exc
        if not args.no_promote:
            if args.gold_root is None:
                raise SystemExit(
                    "Historical promotion requires an explicit versioned --gold-root."
                )
            try:
                require_versioned_gold_destination(args.gold_root)
            except Exception as exc:
                raise SystemExit(str(exc)) from exc

    result = update_isolated_daily(
        args.symbol,
        args.asset_class,
        destination_root,
        args.expected_session_date,
        args.start_date,
    )
    print(
        "INGEST "
        f"symbol={result['symbol']} status={result['status']} "
        f"effective_date={result['effective_date']} validation={result['validation']}"
    )
    if result["status"] != "COMPLETE":
        raise SystemExit("Ingestion completed but did not reach --expected-session-date.")

    validator = ROOT / "data_quality" / "validate_daily_sanity.py"
    command = [
        sys.executable,
        str(validator),
        "--asset-class",
        args.asset_class,
        "--symbol",
        str(result["symbol"]),
    ]
    if historical or args.destination_root is not None:
        command.extend(["--silver-root", str(destination_root / "parquet")])
    if historical or args.quality_root is not None:
        command.extend(["--quality-root", str(quality_root)])
    if args.no_promote:
        command.append("--no-promote")
    elif args.gold_root is not None:
        command.extend(["--gold-root", str(args.gold_root.resolve())])
    completed = subprocess.run(command, check=False)
    if completed.returncode:
        raise SystemExit(completed.returncode)
    print("PIPELINE=PASS")


if __name__ == "__main__":
    main()
