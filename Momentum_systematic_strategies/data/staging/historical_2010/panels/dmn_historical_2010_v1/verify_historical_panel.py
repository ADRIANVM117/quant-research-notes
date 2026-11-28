"""Read-only verification for the QR-DMN-13 staging panel."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import polars as pl


PANEL_ROOT = Path(__file__).resolve().parent


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def recompute(adjusted: pl.DataFrame, symbols: list[str]) -> tuple[pl.DataFrame, pl.DataFrame]:
    simple = adjusted.select(
        "session_date", *[((pl.col(symbol) / pl.col(symbol).shift(1)) - 1).alias(symbol) for symbol in symbols]
    ).drop_nulls()
    log = adjusted.select(
        "session_date", *[(pl.col(symbol).log() - pl.col(symbol).shift(1).log()).alias(symbol) for symbol in symbols]
    ).drop_nulls()
    return simple, log


def verify_variant(prefix: str, symbols: list[str], manifest: dict[str, object]) -> None:
    adjusted_name = f"{prefix}adjusted_close.parquet"
    simple_name = f"{prefix}simple_returns.parquet"
    log_name = f"{prefix}log_returns.parquet"
    adjusted = pl.read_parquet(PANEL_ROOT / adjusted_name)
    simple = pl.read_parquet(PANEL_ROOT / simple_name)
    log = pl.read_parquet(PANEL_ROOT / log_name)
    expected_simple, expected_log = recompute(adjusted, symbols)
    if not simple.equals(expected_simple) or not log.equals(expected_log):
        raise RuntimeError(f"{prefix or 'main'} returns do not exactly match adjusted-close recomputation.")
    if adjusted.get_column("session_date").n_unique() != adjusted.height:
        raise RuntimeError(f"{prefix or 'main'} adjusted panel has duplicate dates.")
    if not all(
        all(frame.select(pl.all().exclude("session_date").is_finite().all()).row(0))
        for frame in (simple, log)
    ):
        raise RuntimeError(f"{prefix or 'main'} has non-finite saved returns.")
    for name in (adjusted_name, simple_name, log_name):
        if sha256(PANEL_ROOT / name) != manifest["matrix_sha256"][name]:
            raise RuntimeError(f"Hash mismatch: {name}")


def main() -> None:
    manifest = json.loads((PANEL_ROOT / "PANEL_MANIFEST.json").read_text(encoding="utf-8"))
    verify_variant("main_", manifest["main_symbols"], manifest)
    verify_variant("conditional_bil_", manifest["conditional_bil_symbols"], manifest)
    if manifest["bil_policy"] != "conditional variant only; quality status remains SUBGOLD_REVIEW":
        raise RuntimeError("BIL policy changed unexpectedly.")
    print("QR-DMN-13 read-only verification: PASS")


if __name__ == "__main__":
    main()
