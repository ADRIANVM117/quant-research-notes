"""Offline safety tests for QR-DMN-14; no production path is written."""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import shutil
import unittest
from contextlib import contextmanager
from pathlib import Path


MODULE = Path(__file__).resolve().parents[1] / "freeze_historical_panel.py"
SPEC = importlib.util.spec_from_file_location("freeze_historical_panel", MODULE)
freeze_module = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(freeze_module)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class HistoricalFreezeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        # Run from the extracted review root or repository root to stay under MAX_PATH.
        cls.fixture_root = Path.cwd() / ".qr_dmn14_tests"
        cls.fixture_root.mkdir(exist_ok=True)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.fixture_root.rmdir()

    @contextmanager
    def fixture_directory(self):
        # Reuse a short name sequentially: tests must also work after a normal
        # Windows extraction into a potentially long temporary directory.
        directory = self.fixture_root / "x"
        if directory.exists():
            raise RuntimeError("Stale offline fixture directory.")
        directory.mkdir()
        try:
            yield directory
        finally:
            shutil.rmtree(directory)

    def build_source(self, root: Path, bil_status: str = "SUBGOLD_REVIEW") -> Path:
        source = root / "source"
        source.mkdir()
        hashes = {}
        for name in freeze_module.MATRICES:
            path = source / name
            path.write_bytes((name + " fixture\n").encode())
            hashes[name] = digest(path)
        for name in ("conditional_bil_adjusted_close.parquet", "conditional_bil_simple_returns.parquet", "conditional_bil_log_returns.parquet"):
            path = source / name
            path.write_bytes((name + " fixture\n").encode())
            hashes[name] = digest(path)
        main_symbols = ["SPY", "QQQ", "IWM", "IWD", "IWF", "XLE", "XLF", "GLD", "TLT", "SHY"]
        for name in ("PANEL_VALIDATION.md", "PANEL_TEST_RESULTS.md", "FROZEN_GOLD_INTEGRITY.csv", "PRIOR_REFERENCE_RECONCILIATION.csv"):
            (source / name).write_text(f"{name} fixture\n", encoding="utf-8")
        rows = [{"symbol": symbol, "panel_main": "true", "quality_status": "GOLD_APPROVED"} for symbol in main_symbols]
        rows.append({"symbol": "BIL", "panel_main": "false", "quality_status": bil_status})
        with (source / "LINEAGE.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        manifest = {
            "panel_version": freeze_module.VERSION,
            "bil_policy": "conditional variant only; quality status remains SUBGOLD_REVIEW",
            "main_symbols": main_symbols,
            "matrix_sha256": hashes,
            "lineage_file_sha256": digest(source / "LINEAGE.csv"),
            "frozen_gold_integrity_sha256": digest(source / "FROZEN_GOLD_INTEGRITY.csv"),
            "prior_reference_reconciliation_sha256": digest(source / "PRIOR_REFERENCE_RECONCILIATION.csv"),
        }
        (source / "PANEL_MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")
        return source

    def freeze_arguments(self, root: Path) -> dict[str, object]:
        versions = root / "data/gold_versions"
        return {
            "authorized_versions_root": versions,
            "protected_roots": tuple(root / "data" / name for name in ("raw", "silver", "gold", "quality", "staging")),
        }

    def test_atomic_freeze_preserves_verified_bytes_and_excludes_bil(self) -> None:
        with self.fixture_directory() as root:
            source = self.build_source(root)
            versions = root / "data/gold_versions"
            destination = versions / freeze_module.VERSION
            result = freeze_module.freeze(source, destination, versions, **self.freeze_arguments(root))
            self.assertTrue((destination / "FREEZE_MANIFEST.json").is_file())
            self.assertEqual(result["sha256"], {name: digest(source / name) for name in (*freeze_module.MATRICES, *freeze_module.SUPPORTING_FILES)})
            self.assertFalse(any(path.name.startswith("conditional_bil_") for path in destination.iterdir()))

    def test_existing_or_partial_destination_is_rejected(self) -> None:
        with self.fixture_directory() as root:
            source = self.build_source(root)
            destination = root / "data/gold_versions" / freeze_module.VERSION
            destination.mkdir(parents=True)
            (destination / "partial").write_text("keep", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "already exists or is partial"):
                freeze_module.freeze(source, destination, destination.parent, **self.freeze_arguments(root))
            self.assertEqual((destination / "partial").read_text(encoding="utf-8"), "keep")

    def test_wrong_destination_is_rejected_before_copy(self) -> None:
        with self.fixture_directory() as root:
            source = self.build_source(root)
            with self.assertRaisesRegex(RuntimeError, "Destination must be exactly"):
                freeze_module.freeze(source, root / "data/gold/dmn_historical_2010_v1", root / "data/gold_versions", **self.freeze_arguments(root))

    def test_nonapproved_bil_is_not_silently_accepted_as_approved(self) -> None:
        with self.fixture_directory() as root:
            source = self.build_source(root, bil_status="GOLD_APPROVED")
            with self.assertRaisesRegex(RuntimeError, "BIL must remain"):
                freeze_module.source_record(source)

    def test_protected_fixture_roots_remain_unchanged(self) -> None:
        with self.fixture_directory() as root:
            source = self.build_source(root)
            protected = [root / "data/raw/sentinel", root / "data/silver/sentinel", root / "data/gold/sentinel", root / "data/quality/sentinel"]
            for path in protected:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("immutable", encoding="utf-8")
            before = {path: digest(path) for path in protected}
            freeze_module.freeze(
                source,
                root / "data/gold_versions" / freeze_module.VERSION,
                root / "data/gold_versions",
                **self.freeze_arguments(root),
            )
            self.assertEqual(before, {path: digest(path) for path in protected})

    def test_resolved_symlink_or_redirection_into_gold_is_rejected(self) -> None:
        with self.fixture_directory() as root:
            versions = root / "data/gold_versions"
            destination = versions / freeze_module.VERSION
            redirected_root = root / "data/gold"

            def redirected(path: Path) -> Path:
                return redirected_root if Path(path) == versions else redirected_root / freeze_module.VERSION

            with self.assertRaisesRegex(RuntimeError, "not the authorized physical path"):
                freeze_module.require_target(destination, versions, path_resolver=redirected, **self.freeze_arguments(root))

    def test_lineage_hash_mismatch_is_rejected_before_copy(self) -> None:
        with self.fixture_directory() as root:
            source = self.build_source(root)
            (source / "LINEAGE.csv").write_text("tampered\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "Source provenance hash mismatch: LINEAGE.csv"):
                freeze_module.source_record(source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
