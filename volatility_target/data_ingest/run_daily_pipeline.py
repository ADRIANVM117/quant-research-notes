"""One-command daily ingestion and quality gate for a portable research project."""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import date
from pathlib import Path

from alpha_vantage_daily import update_isolated_daily


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
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = update_isolated_daily(
        args.symbol,
        args.asset_class,
        ROOT / "data",
        args.expected_session_date,
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
    completed = subprocess.run(command, check=False)
    if completed.returncode:
        raise SystemExit(completed.returncode)
    print("PIPELINE=PASS")


if __name__ == "__main__":
    main()
