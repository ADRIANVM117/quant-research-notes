"""Offline safety tests for the isolated historical-backfill path."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[3]
INGEST = ROOT / "Momentum_systematic_strategies" / "data_ingest"
QUALITY_MODULE = ROOT / "Momentum_systematic_strategies" / "data_quality"
sys.path.insert(0, str(INGEST))
sys.path.insert(0, str(QUALITY_MODULE))

import alpha_vantage_daily as daily  # noqa: E402
import run_daily_pipeline as pipeline  # noqa: E402
import validate_daily_sanity as sanity  # noqa: E402


def synthetic_payload(symbol: str = "TLT") -> dict[str, object]:
    dates = ("2010-01-04", "2018-01-02", "2018-01-03")
    series = {}
    for index, session in enumerate(dates, start=1):
        close = 100.0 + index
        series[session] = {
            "1. open": str(close - 0.5), "2. high": str(close + 0.5),
            "3. low": str(close - 1.0), "4. close": str(close),
            "5. adjusted close": str(close), "6. volume": str(1000 + index),
            "7. dividend amount": "0.0", "8. split coefficient": "1.0",
        }
    return {
        "Meta Data": {"2. Symbol": symbol, "3. Last Refreshed": "2018-01-03", "5. Time Zone": "US/Eastern"},
        "Time Series (Daily)": series,
    }


class HistoricalBackfillSafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.gold_dir = ROOT / "Momentum_systematic_strategies" / "data" / "gold" / "daily_series" / "etf"
        cls.gold_hashes = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in cls.gold_dir.glob("*.parquet")}

    def tearDown(self) -> None:
        observed = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in self.gold_dir.glob("*.parquet")}
        self.assertEqual(observed, self.gold_hashes, "A fixture test changed an existing Gold file.")
        shutil.rmtree(self.workspace)
        if not any(self.workspace.parent.iterdir()):
            self.workspace.parent.rmdir()

    def setUp(self) -> None:
        workspace_root = ROOT / "Momentum_systematic_strategies" / "data" / "staging" / ".offline_test_workspace"
        case_id = hashlib.sha256(self._testMethodName.encode("utf-8")).hexdigest()[:10]
        self.workspace = workspace_root / case_id
        if self.workspace.exists():
            shutil.rmtree(self.workspace)
        self.workspace.mkdir(parents=True)

    def test_parser_retains_2010_only_when_requested(self) -> None:
        payload = synthetic_payload()
        ordinary = daily.parse_daily_payload(payload, "TLT")
        historical = daily.parse_daily_payload(payload, "TLT", start_date=date(2010, 1, 1))
        self.assertEqual(ordinary.get_column("session_date").min(), date(2018, 1, 2))
        self.assertEqual(historical.get_column("session_date").min(), date(2010, 1, 4))
        self.assertEqual(historical.height, 3)

    def test_isolated_function_writes_only_staging(self) -> None:
        payload = synthetic_payload()
        raw = json.dumps(payload).encode("utf-8")
        staging = self.workspace / "staging"
        with patch.object(daily, "request_daily_adjusted_raw", return_value=(200, raw, payload)):
            result = daily.update_isolated_daily("TLT", "etf", staging, date(2018, 1, 3), date(2010, 1, 1))
        frame = daily.pl.read_parquet(staging / "parquet" / "etf" / "TLT.parquet")
        self.assertEqual(frame.get_column("session_date").min(), date(2010, 1, 4))
        self.assertTrue((staging / "raw" / "TLT_2018-01-03.json").exists())
        self.assertEqual(Path(str(result["parquet_path"])).parent, staging / "parquet" / "etf")

    def test_isolated_default_start_retains_ordinary_2018_cutoff(self) -> None:
        payload = synthetic_payload()
        raw = json.dumps(payload).encode("utf-8")
        staging = self.workspace / "ordinary_update"
        with patch.object(daily, "request_daily_adjusted_raw", return_value=(200, raw, payload)):
            daily.update_isolated_daily("TLT", "etf", staging, date(2018, 1, 3))
        frame = daily.pl.read_parquet(staging / "parquet" / "etf" / "TLT.parquet")
        self.assertEqual(frame.get_column("session_date").min(), date(2018, 1, 2))

    def test_historical_mode_rejects_default_data_root(self) -> None:
        with self.assertRaises(daily.AlphaVantageDailyError):
            daily.update_isolated_daily("TLT", "etf", ROOT / "Momentum_systematic_strategies" / "data", date(2018, 1, 3), date(2010, 1, 1))

    def test_alpha_cli_requires_explicit_isolated_destination(self) -> None:
        arguments = ["alpha_vantage_daily.py", "--symbol", "TLT", "--asset-class", "etf", "--start-date", "2010-01-01"]
        with patch.object(sys, "argv", arguments):
            with self.assertRaises(daily.AlphaVantageDailyError):
                daily.main()

    def test_pipeline_cli_validates_staging_without_gold_promotion(self) -> None:
        payload = synthetic_payload()
        staging = self.workspace / "historical_2010" / "pilot_tlt"
        quality_root = self.workspace / "historical_2010" / "quality"

        def fixture_ingest(symbol, asset_class, destination_root, target_date, start_date):
            frame = daily.parse_daily_payload(payload, symbol, start_date=start_date)
            destination = destination_root / "parquet" / asset_class / f"{symbol}.parquet"
            daily.write_daily_atomically(frame, destination)
            return {"symbol": symbol, "status": "COMPLETE", "effective_date": target_date.isoformat(), "validation": "PASS"}

        arguments = [
            "run_daily_pipeline.py", "--symbol", "TLT", "--asset-class", "etf",
            "--expected-session-date", "2018-01-03", "--start-date", "2010-01-01",
            "--destination-root", str(staging), "--quality-root", str(quality_root), "--no-promote",
        ]
        with patch.object(pipeline, "update_isolated_daily", side_effect=fixture_ingest), patch.object(sys, "argv", arguments):
            pipeline.main()

        self.assertTrue((staging / "parquet" / "etf" / "TLT.parquet").exists())
        self.assertTrue((quality_root / "series_status.csv").exists())
        self.assertFalse((staging / "gold").exists())

    def test_pipeline_cli_rejects_historical_backfill_without_staging(self) -> None:
        arguments = [
            "run_daily_pipeline.py", "--symbol", "TLT", "--asset-class", "etf",
            "--expected-session-date", "2018-01-03", "--start-date", "2010-01-01",
        ]
        with patch.object(sys, "argv", arguments):
            with self.assertRaises(SystemExit):
                pipeline.main()

    def test_pipeline_cli_rejects_historical_promotion_to_current_gold(self) -> None:
        arguments = [
            "run_daily_pipeline.py", "--symbol", "TLT", "--asset-class", "etf",
            "--expected-session-date", "2018-01-03", "--start-date", "2010-01-01",
            "--destination-root", str(self.workspace / "staging"),
            "--quality-root", str(self.workspace / "quality"),
        ]
        with patch.object(sys, "argv", arguments):
            with self.assertRaises(SystemExit):
                pipeline.main()

    def test_protected_paths_and_dotdot_fail_before_ingest(self) -> None:
        destination = self.workspace / "run"
        quality_root = self.workspace / "quality"
        protected_gold = self.gold_dir.parent
        cases = [
            ["--destination-root", str(protected_gold), "--quality-root", str(quality_root), "--no-promote"],
            ["--destination-root", str(destination), "--quality-root", str(protected_gold), "--no-promote"],
            ["--destination-root", str(destination), "--quality-root", str(quality_root), "--gold-root", str(self.gold_dir)],
            ["--destination-root", str(ROOT / "Momentum_systematic_strategies" / "data" / "staging" / ".." / "gold" / "daily_series"), "--quality-root", str(quality_root), "--no-promote"],
        ]
        for extra in cases:
            arguments = [
                "run_daily_pipeline.py", "--symbol", "TLT", "--asset-class", "etf",
                "--expected-session-date", "2018-01-03", "--start-date", "2010-01-01", *extra,
            ]
            ingest = Mock()
            with patch.object(pipeline, "update_isolated_daily", ingest), patch.object(sys, "argv", arguments):
                with self.assertRaises(SystemExit):
                    pipeline.main()
            ingest.assert_not_called()

    def test_resolved_symlink_to_protected_gold_fails_before_ingest(self) -> None:
        link = self.workspace / "gold_link"
        original_resolver = daily._resolved_path

        def resolve_with_symlink(path):
            candidate = Path(path)
            if candidate == link or candidate.is_relative_to(link):
                return self.gold_dir / candidate.relative_to(link)
            return original_resolver(candidate)

        with patch.object(daily, "_resolved_path", side_effect=resolve_with_symlink):
            with self.assertRaises(daily.AlphaVantageDailyError):
                daily.update_isolated_daily("TLT", "etf", link / "run", date(2018, 1, 3), date(2010, 1, 1))

    def test_validator_rejects_protected_quality_and_gold_roots(self) -> None:
        arguments = [
            "validate_daily_sanity.py", "--asset-class", "etf", "--symbol", "TLT",
            "--silver-root", str(self.workspace / "silver"),
            "--quality-root", str(self.gold_dir.parent), "--no-promote",
        ]
        with patch.object(sys, "argv", arguments):
            with self.assertRaises(SystemExit):
                sanity.main()
        arguments = [
            "validate_daily_sanity.py", "--asset-class", "etf", "--symbol", "TLT",
            "--silver-root", str(self.workspace / "silver"),
            "--quality-root", str(self.workspace / "quality"),
            "--gold-root", str(self.gold_dir),
        ]
        with patch.object(sys, "argv", arguments):
            with self.assertRaises(SystemExit):
                sanity.main()


if __name__ == "__main__":
    unittest.main(verbosity=2)
