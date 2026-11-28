"""Build the QR-DMN-13 candidate historical research panels offline.

The script writes only its versioned staging directory. It reads the eleven
preserved historical Parquets as separate, single-vintage inputs and never
contacts a provider or writes Raw, Silver, Gold, or normal Quality paths.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from math import sqrt
from pathlib import Path

import polars as pl


ROOT = Path(__file__).resolve().parents[5]
HISTORICAL_ROOT = ROOT / "data/staging/historical_2010"
QR11_ROOT = HISTORICAL_ROOT / "qr_dmn11"
TLT_ROOT = HISTORICAL_ROOT / "tlt_pilot_20261127"
PANEL_ROOT = ROOT / "data/staging/historical_2010/panels/dmn_historical_2010_v1"
MAIN_SYMBOLS = ("SPY", "QQQ", "IWM", "IWD", "IWF", "XLE", "XLF", "GLD", "TLT", "SHY")
CONDITIONAL_SYMBOLS = (*MAIN_SYMBOLS, "BIL")
EXPECTED_COLUMNS = (
    "symbol_requested", "session_date", "open", "high", "low", "close",
    "adjusted_close", "volume", "dividend_amount", "split_coefficient",
    "provider_timezone", "source", "provider_last_refreshed", "ingested_at_utc",
)
EXPECTED_SCHEMA = pl.Schema(
    {
        "symbol_requested": pl.String,
        "session_date": pl.Date,
        "open": pl.Float64,
        "high": pl.Float64,
        "low": pl.Float64,
        "close": pl.Float64,
        "adjusted_close": pl.Float64,
        "volume": pl.Int64,
        "dividend_amount": pl.Float64,
        "split_coefficient": pl.Float64,
        "provider_timezone": pl.String,
        "source": pl.String,
        "provider_last_refreshed": pl.String,
        "ingested_at_utc": pl.Datetime(time_zone="UTC"),
    }
)
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


def staging_paths(symbol: str) -> tuple[Path, Path, Path]:
    if symbol == "TLT":
        return (
            TLT_ROOT / "parquet/etf/TLT.parquet",
            TLT_ROOT / "raw/TLT_2026-11-27.json",
            TLT_ROOT.parent / "tlt_pilot_20261127_quality/series_status.csv",
        )
    return (
        QR11_ROOT / symbol / "parquet/etf" / f"{symbol}.parquet",
        QR11_ROOT / symbol / "raw" / f"{symbol}_2026-11-27.json",
        QR11_ROOT / "quality" / symbol / "series_status.csv",
    )


def quality_status(path: Path) -> str:
    return pl.read_csv(path).row(0, named=True)["status"]


def assemble_adjusted_close(frames: dict[str, pl.DataFrame], symbols: tuple[str, ...]) -> pl.DataFrame:
    panel = frames[symbols[0]].select("session_date", pl.col("adjusted_close").alias(symbols[0]))
    for symbol in symbols[1:]:
        panel = panel.join(
            frames[symbol].select("session_date", pl.col("adjusted_close").alias(symbol)),
            on="session_date", how="inner",
        )
    return panel.sort("session_date")


def return_panels(adjusted: pl.DataFrame, symbols: tuple[str, ...]) -> tuple[pl.DataFrame, pl.DataFrame]:
    simple = adjusted.select(
        "session_date", *[((pl.col(symbol) / pl.col(symbol).shift(1)) - 1).alias(symbol) for symbol in symbols]
    ).drop_nulls()
    log = adjusted.select(
        "session_date", *[(pl.col(symbol).log() - pl.col(symbol).shift(1).log()).alias(symbol) for symbol in symbols]
    ).drop_nulls()
    return simple, log


def assert_return_panel(frame: pl.DataFrame, symbols: tuple[str, ...], label: str) -> None:
    if frame.columns != ["session_date", *symbols]:
        raise RuntimeError(f"{label} columns do not match the explicit panel symbols.")
    for symbol in symbols:
        invalid = frame.filter(pl.col(symbol).is_null() | ~pl.col(symbol).is_finite()).height
        if invalid:
            raise RuntimeError(f"{label} contains {invalid} non-finite returns for {symbol}.")
    if frame.get_column("session_date").n_unique() != frame.height:
        raise RuntimeError(f"{label} has duplicate dates.")


def warmup_dates(dates: list[object]) -> dict[str, str]:
    # Index 0 is the first price. Return t needs price t-1, momentum needs t-126.
    return {
        "first_price": str(dates[0]),
        "first_return": str(dates[1]),
        "ewma_lambda_094_min_20_returns": str(dates[20]),
        "momentum_126_sessions": str(dates[126]),
        "lstm_63_return_sessions": str(dates[63]),
        "lstm_63_composite_feature_endpoint": str(dates[188]),
        "first_next_session_target_after_composite_sequence": str(dates[189]),
    }


def main() -> None:
    manifest_path = PANEL_ROOT / "PANEL_MANIFEST.json"
    if manifest_path.exists():
        raise SystemExit(f"Refusing to mutate existing immutable panel: {PANEL_ROOT}")
    PANEL_ROOT.mkdir(parents=True, exist_ok=True)
    frames: dict[str, pl.DataFrame] = {}
    lineage: list[dict[str, object]] = []
    date_sets: dict[str, set[object]] = {}
    for symbol in CONDITIONAL_SYMBOLS:
        parquet_path, raw_path, status_path = staging_paths(symbol)
        if not all(path.is_file() for path in (parquet_path, raw_path, status_path)):
            raise SystemExit(f"Missing preserved staging input for {symbol}.")
        frame = pl.read_parquet(parquet_path).sort("session_date")
        if tuple(frame.columns) != EXPECTED_COLUMNS:
            raise RuntimeError(f"{symbol} does not have the canonical daily schema.")
        if frame.schema != EXPECTED_SCHEMA:
            raise RuntimeError(f"{symbol} canonical daily schema types do not match.")
        if frame.get_column("session_date").n_unique() != frame.height:
            raise RuntimeError(f"{symbol} contains duplicate session dates.")
        if frame.filter(pl.col("adjusted_close").is_null() | (pl.col("adjusted_close") <= 0)).height:
            raise RuntimeError(f"{symbol} has invalid adjusted_close values.")
        frames[symbol] = frame
        dates = frame.get_column("session_date").to_list()
        date_sets[symbol] = set(dates)
        payload = json.loads(raw_path.read_text(encoding="utf-8"))
        metadata = payload.get("Meta Data", {})
        lineage.append(
            {
                "symbol": symbol,
                "panel_main": symbol in MAIN_SYMBOLS,
                "panel_conditional_bil": True,
                "source": "Alpha Vantage TIME_SERIES_DAILY_ADJUSTED",
                "raw_relative_path": raw_path.relative_to(ROOT).as_posix(),
                "raw_sha256": sha256(raw_path),
                "parquet_relative_path": parquet_path.relative_to(ROOT).as_posix(),
                "parquet_sha256": sha256(parquet_path),
                "provider_last_refreshed": metadata.get("3. Last Refreshed", ""),
                "provider_timezone": metadata.get("5. Time Zone", ""),
                "rows": frame.height,
                "start_date": str(dates[0]),
                "end_date": str(dates[-1]),
                "positive_dividend_sessions": frame.filter(pl.col("dividend_amount") > 0).height,
                "non_unit_split_sessions": frame.filter(pl.col("split_coefficient") != 1).height,
                "quality_status": quality_status(status_path),
                "vintage_rule": "single preserved staging Parquet; no level concatenation",
            }
        )

    common_dates = set.intersection(*(date_sets[symbol] for symbol in CONDITIONAL_SYMBOLS))
    common_sorted = sorted(common_dates)
    # QR-DMN-11 independently checked these exact staged vintages against XNYS.
    # Reuse its preserved coverage record rather than relying on a runtime
    # calendar package whose available session range can vary by environment.
    calendar_coverage = pl.read_csv(QR11_ROOT / "analysis/results/calendar_coverage.csv")
    coverage = calendar_coverage.filter(pl.col("symbol").is_in(list(CONDITIONAL_SYMBOLS)))
    if coverage.height != len(CONDITIONAL_SYMBOLS) or coverage.filter(
        (pl.col("calendar") != "XNYS")
        | (pl.col("expected_sessions") != pl.col("observed_sessions"))
        | (pl.col("missing_sessions") != 0)
        | (pl.col("extraordinary_dates") != 0)
    ).height:
        raise RuntimeError("The preserved XNYS coverage audit is not clean for every staging input.")
    intersection = pl.read_csv(QR11_ROOT / "analysis/results/eleven_instrument_intersection.csv").row(0, named=True)
    if (
        len(common_sorted) != int(intersection["common_sessions"])
        or str(common_sorted[0]) != intersection["common_start"]
        or str(common_sorted[-1]) != intersection["common_end"]
    ):
        raise RuntimeError("The common dates do not match the preserved eleven-instrument XNYS audit.")

    main_adjusted = assemble_adjusted_close(frames, MAIN_SYMBOLS)
    conditional_adjusted = assemble_adjusted_close(frames, CONDITIONAL_SYMBOLS)
    if main_adjusted.height != len(common_sorted) or conditional_adjusted.height != len(common_sorted):
        raise RuntimeError("Panel construction dropped a common session.")
    main_simple, main_log = return_panels(main_adjusted, MAIN_SYMBOLS)
    conditional_simple, conditional_log = return_panels(conditional_adjusted, CONDITIONAL_SYMBOLS)
    for frame, symbols, label in (
        (main_simple, MAIN_SYMBOLS, "main simple"), (main_log, MAIN_SYMBOLS, "main log"),
        (conditional_simple, CONDITIONAL_SYMBOLS, "conditional simple"), (conditional_log, CONDITIONAL_SYMBOLS, "conditional log"),
    ):
        assert_return_panel(frame, symbols, label)

    outputs = {
        "main_adjusted_close.parquet": main_adjusted,
        "main_simple_returns.parquet": main_simple,
        "main_log_returns.parquet": main_log,
        "conditional_bil_adjusted_close.parquet": conditional_adjusted,
        "conditional_bil_simple_returns.parquet": conditional_simple,
        "conditional_bil_log_returns.parquet": conditional_log,
    }
    for name, frame in outputs.items():
        frame.write_parquet(PANEL_ROOT / name)
        saved = pl.read_parquet(PANEL_ROOT / name)
        if not saved.equals(frame):
            raise RuntimeError(f"Saved matrix does not match recomputation: {name}")

    pl.DataFrame(lineage).sort("symbol").write_csv(PANEL_ROOT / "LINEAGE.csv")
    prior_reconciliation = pl.read_csv(QR11_ROOT / "analysis/results/reference_reconciliation.csv")
    if prior_reconciliation.filter(pl.col("classification") != "RETURNS_EQUIVALENT_CONSTANT_SCALE").height:
        raise RuntimeError("A prior reference reconciliation is not returns-equivalent.")
    prior_reconciliation.write_csv(PANEL_ROOT / "PRIOR_REFERENCE_RECONCILIATION.csv")
    gold_rows = []
    for symbol, expected_hash in FROZEN_GOLD.items():
        path = ROOT / "data/gold/daily_series/etf" / f"{symbol}.parquet"
        actual_hash = sha256(path)
        if actual_hash != expected_hash:
            raise RuntimeError(f"Frozen Gold changed: {symbol}")
        gold_rows.append({"symbol": symbol, "sha256_expected": expected_hash, "sha256_actual": actual_hash, "match": "YES"})
    pl.DataFrame(gold_rows).sort("symbol").write_csv(PANEL_ROOT / "FROZEN_GOLD_INTEGRITY.csv")

    samples = {
        "main_adjusted_close_sample.csv": main_adjusted,
        "main_simple_returns_sample.csv": main_simple,
        "conditional_bil_adjusted_close_sample.csv": conditional_adjusted,
        "conditional_bil_simple_returns_sample.csv": conditional_simple,
    }
    for name, frame in samples.items():
        pl.concat([frame.head(3), frame.tail(3)]).write_csv(PANEL_ROOT / name)

    dates = main_adjusted.get_column("session_date").to_list()
    panel_hashes = {name: sha256(PANEL_ROOT / name) for name in outputs}
    manifest = {
        "panel_version": "dmn_historical_2010_v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "staging-only candidate; no Gold promotion",
        "calendar": "XNYS",
        "common_sessions": len(common_sorted),
        "common_start": str(common_sorted[0]),
        "common_end": str(common_sorted[-1]),
        "main_symbols": list(MAIN_SYMBOLS),
        "conditional_bil_symbols": list(CONDITIONAL_SYMBOLS),
        "bil_policy": "conditional variant only; quality status remains SUBGOLD_REVIEW",
        "returns": {
            "simple": "adjusted_close[t] / adjusted_close[t-1] - 1",
            "log": "log(adjusted_close[t]) - log(adjusted_close[t-1])",
            "missing_price_policy": "no imputation; construction requires complete consecutive XNYS sessions",
        },
        "warmup": warmup_dates(dates),
        "matrix_sha256": panel_hashes,
        "lineage_file_sha256": sha256(PANEL_ROOT / "LINEAGE.csv"),
        "prior_reference_reconciliation_sha256": sha256(PANEL_ROOT / "PRIOR_REFERENCE_RECONCILIATION.csv"),
        "frozen_gold_integrity_sha256": sha256(PANEL_ROOT / "FROZEN_GOLD_INTEGRITY.csv"),
    }
    with manifest_path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)
        handle.write("\n")
    validation = [
        "# QR-DMN-13 panel validation", "",
        "- Canonical schema: PASS for all eleven staging inputs.",
        f"- Common XNYS calendar: PASS ({len(common_sorted)} sessions; {common_sorted[0]} through {common_sorted[-1]}).",
        "- Duplicate session dates: none.",
        "- Simple and log return matrices: no null or non-finite values.",
        "- Saved matrices equal their direct adjusted-close recomputation.",
        "- Prior Gold/Silver overlap reconciliations: all returns-equivalent constant scales.",
        "- Eight frozen Gold hashes: PASS.",
        "- Main panel: ten assets; BIL is excluded.",
        "- Conditional panel: eleven assets; BIL remains SUBGOLD_REVIEW and is not Gold-approved.",
        "- No imputation, vintage splicing, Gold promotion, or write to existing Raw/Silver/Gold/Quality paths.",
        "",
    ]
    (PANEL_ROOT / "PANEL_VALIDATION.md").write_text("\n".join(validation), encoding="utf-8", newline="\n")
    print(f"PANEL_ROOT={PANEL_ROOT}")
    print(f"COMMON_SESSIONS={len(common_sorted)}")
    print(f"MAIN_ROWS={main_adjusted.height} RETURNS={main_simple.height}")
    print(f"CONDITIONAL_ROWS={conditional_adjusted.height} RETURNS={conditional_simple.height}")
    print("PANEL_VALIDATION=PASS")


if __name__ == "__main__":
    main()
