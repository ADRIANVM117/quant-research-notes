"""Prepare or atomically freeze the approved QR-DMN-13 main panel.

The default action is read-only preflight. A caller must explicitly pass
``--execute-freeze`` after a separate authorization. The conditional BIL
variant is intentionally never copied by this script.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[5]
SOURCE_PANEL = ROOT / "data/staging/historical_2010/panels/dmn_historical_2010_v1"
GOLD_VERSIONS_ROOT = ROOT / "data/gold_versions"
VERSION = "dmn_historical_2010_v1"
MATRICES = (
    "main_adjusted_close.parquet",
    "main_simple_returns.parquet",
    "main_log_returns.parquet",
)
SUPPORTING_FILES = (
    "PANEL_MANIFEST.json",
    "LINEAGE.csv",
    "PANEL_VALIDATION.md",
    "PANEL_TEST_RESULTS.md",
    "FROZEN_GOLD_INTEGRITY.csv",
    "PRIOR_REFERENCE_RECONCILIATION.csv",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def require_target(
    destination: Path,
    versions_root: Path,
    *,
    authorized_versions_root: Path | None = None,
    protected_roots: tuple[Path, ...] | None = None,
    path_resolver=Path.resolve,
) -> None:
    """Allow only the physical, direct approved version directory.

    The approved root is deliberately built from the resolved ``data`` parent
    without resolving its final ``gold_versions`` component. Consequently a
    symlink or redirection of that final component into Raw/Silver/Gold/Quality
    cannot silently become an authorized target.
    """
    approved_root = authorized_versions_root or ((ROOT / "data").resolve() / "gold_versions")
    protected = protected_roots or tuple((ROOT / "data" / name).resolve() for name in ("raw", "silver", "gold", "quality", "staging"))
    root = path_resolver(versions_root)
    target = path_resolver(destination)
    if root != approved_root:
        raise RuntimeError(f"Version root is not the authorized physical path: {approved_root}.")
    if any(is_within(root, protected_root) or is_within(protected_root, root) for protected_root in protected):
        raise RuntimeError("Version root resolves within or around a protected data tree.")
    if target.name != VERSION or target.parent != root:
        raise RuntimeError(f"Destination must be exactly {root / VERSION}.")
    if target.exists():
        raise RuntimeError("Destination already exists or is partial; refusing to overwrite it.")


def source_record(source: Path) -> dict[str, object]:
    manifest_path = source / "PANEL_MANIFEST.json"
    if not manifest_path.is_file():
        raise RuntimeError("Missing source PANEL_MANIFEST.json.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("panel_version") != VERSION:
        raise RuntimeError("Unexpected source panel version.")
    if manifest.get("bil_policy") != "conditional variant only; quality status remains SUBGOLD_REVIEW":
        raise RuntimeError("BIL policy is not the approved conditional policy.")
    expected_hashes = manifest.get("matrix_sha256", {})
    if set(expected_hashes) != {
        *MATRICES,
        "conditional_bil_adjusted_close.parquet",
        "conditional_bil_simple_returns.parquet",
        "conditional_bil_log_returns.parquet",
    }:
        raise RuntimeError("Source manifest matrix inventory is not the approved six-file inventory.")
    for name, expected in expected_hashes.items():
        path = source / name
        if not path.is_file() or sha256(path) != expected:
            raise RuntimeError(f"Source hash mismatch: {name}")
    for name in SUPPORTING_FILES:
        if not (source / name).is_file():
            raise RuntimeError(f"Missing source support artifact: {name}")
    for name, manifest_key in (
        ("LINEAGE.csv", "lineage_file_sha256"),
        ("FROZEN_GOLD_INTEGRITY.csv", "frozen_gold_integrity_sha256"),
        ("PRIOR_REFERENCE_RECONCILIATION.csv", "prior_reference_reconciliation_sha256"),
    ):
        expected = manifest.get(manifest_key)
        if not isinstance(expected, str) or sha256(source / name) != expected:
            raise RuntimeError(f"Source provenance hash mismatch: {name}")

    with (source / "LINEAGE.csv").open(encoding="utf-8", newline="") as handle:
        lineage = list(csv.DictReader(handle))
    main_symbols = set(manifest["main_symbols"])
    approved = {row["symbol"] for row in lineage if row["panel_main"].lower() == "true" and row["quality_status"] == "GOLD_APPROVED"}
    if approved != main_symbols:
        raise RuntimeError("Every and only main symbols must be GOLD_APPROVED.")
    bil = [row for row in lineage if row["symbol"] == "BIL"]
    if len(bil) != 1 or bil[0]["panel_main"].lower() != "false" or bil[0]["quality_status"] != "SUBGOLD_REVIEW":
        raise RuntimeError("BIL must remain a separate SUBGOLD_REVIEW input.")
    return {"manifest": manifest, "source_hashes": {name: sha256(source / name) for name in (*MATRICES, *SUPPORTING_FILES)}}


def freeze(
    source: Path,
    destination: Path,
    versions_root: Path,
    *,
    authorized_versions_root: Path | None = None,
    protected_roots: tuple[Path, ...] | None = None,
    path_resolver=Path.resolve,
) -> dict[str, object]:
    """Copy to a same-volume temporary directory, verify, then atomically rename."""
    require_target(
        destination,
        versions_root,
        authorized_versions_root=authorized_versions_root,
        protected_roots=protected_roots,
        path_resolver=path_resolver,
    )
    record = source_record(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    require_target(
        destination,
        versions_root,
        authorized_versions_root=authorized_versions_root,
        protected_roots=protected_roots,
        path_resolver=path_resolver,
    )
    temporary = destination.parent / f".{VERSION}.freeze-{uuid.uuid4().hex}"
    if temporary.exists():
        raise RuntimeError("Unexpected temporary freeze directory already exists.")
    try:
        temporary.mkdir()
        for name in (*MATRICES, *SUPPORTING_FILES):
            shutil.copy2(source / name, temporary / name)
        copied_hashes = {name: sha256(temporary / name) for name in (*MATRICES, *SUPPORTING_FILES)}
        if copied_hashes != record["source_hashes"]:
            raise RuntimeError("Temporary copy differs from its verified source.")
        try:
            source_label = source.resolve().relative_to(ROOT.resolve()).as_posix()
        except ValueError:  # Offline fixture used by the safety tests.
            source_label = source.resolve().as_posix()
        freeze_manifest = {
            "dataset_version": VERSION,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "source_panel_relative_path": source_label,
            "promotion_method": "same-volume temporary copy, complete SHA-256 verification, atomic directory rename",
            "included_files": list((*MATRICES, *SUPPORTING_FILES)),
            "sha256": copied_hashes,
            "excluded": ["all conditional_bil_* matrices", "BIL"],
            "bil_policy": "SUBGOLD_REVIEW; not promoted",
        }
        (temporary / "FREEZE_MANIFEST.json").write_text(
            json.dumps(freeze_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
        )
        os.replace(temporary, destination)
    except Exception:
        if temporary.exists():
            shutil.rmtree(temporary)
        raise
    destination_hashes = {name: sha256(destination / name) for name in (*MATRICES, *SUPPORTING_FILES)}
    if destination_hashes != record["source_hashes"]:
        raise RuntimeError("Post-rename destination verification failed.")
    return {"destination": str(destination), "sha256": destination_hashes}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute-freeze", action="store_true", help="perform the atomic copy; otherwise run only preflight")
    args = parser.parse_args()
    destination = GOLD_VERSIONS_ROOT / VERSION
    require_target(destination, GOLD_VERSIONS_ROOT)
    record = source_record(SOURCE_PANEL)
    print("PRECHECK=PASS")
    print(f"SOURCE={SOURCE_PANEL}")
    print(f"DESTINATION={destination}")
    print("MAIN_SYMBOLS=" + ",".join(record["manifest"]["main_symbols"]))
    print("BIL=SUBGOLD_REVIEW (excluded)")
    if not args.execute_freeze:
        print("DRY_RUN=PASS (no destination directory created)")
        return
    result = freeze(SOURCE_PANEL, destination, GOLD_VERSIONS_ROOT)
    print("FREEZE=PASS")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
