"""Actualiza series diarias estadounidenses del catálogo local."""

from __future__ import annotations

import argparse
import csv
import sys
import time
from collections import Counter
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
UNIVERSE_PATH = PROJECT_ROOT / "data_ingest" / "daily_universe.csv"


def load_symbols(universe_path: Path, asset_class: str) -> list[str]:
    """Devuelve símbolos INCLUDE sin duplicados para una clase de activo."""
    with universe_path.open("r", encoding="utf-8", newline="") as handle:
        rows = csv.DictReader(handle)
        required = {"asset_class", "ticker_alpha_vantage", "download_decision"}
        if rows.fieldnames is None or not required.issubset(rows.fieldnames):
            raise ValueError("El catálogo no contiene las columnas requeridas.")
        symbols: list[str] = []
        seen: set[str] = set()
        for number, row in enumerate(rows, start=2):
            if (row.get("asset_class") or "").strip().lower() != asset_class:
                continue
            if (row.get("download_decision") or "").strip() != "INCLUDE":
                continue
            symbol = (row.get("ticker_alpha_vantage") or "").strip().upper()
            if not symbol:
                raise ValueError(f"Fila {number}: falta ticker_alpha_vantage.")
            if symbol in seen:
                raise ValueError(f"Catálogo duplicado para {symbol}.")
            seen.add(symbol)
            symbols.append(symbol)
    return symbols


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Actualiza daily adjusted y conserva raw por símbolo.")
    parser.add_argument("--target-date", required=True, type=date.fromisoformat)
    parser.add_argument("--destination-root", type=Path, default=PROJECT_ROOT / "data")
    parser.add_argument("--universe-path", type=Path, default=UNIVERSE_PATH)
    parser.add_argument("--asset-class", choices=("equity", "etf"), default="equity")
    parser.add_argument("--requests-per-minute", type=int, default=5)
    parser.add_argument("--max-total-requests", type=int, default=103)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.requests_per_minute <= 0 or args.max_total_requests <= 0:
        raise ValueError("Los límites de solicitudes deben ser positivos.")
    symbols = load_symbols(args.universe_path, args.asset_class)
    if len(symbols) > args.max_total_requests:
        raise ValueError(f"El catálogo seleccionó {len(symbols)} símbolos y el máximo es {args.max_total_requests}.")
    if args.dry_run:
        print(f"PLAN symbols={len(symbols)} target_date={args.target_date.isoformat()} destination={args.destination_root}")
        for symbol in symbols:
            print(f"PLAN symbol={symbol}")
        return

    from alpha_vantage_daily import update_isolated_daily

    counts: Counter[str] = Counter()
    for index, symbol in enumerate(symbols):
        try:
            result = update_isolated_daily(symbol, args.asset_class, args.destination_root, args.target_date)
        except Exception as exc:
            counts["FAILED"] += 1
            print(f"FAILED symbol={symbol} reason={type(exc).__name__}", file=sys.stderr)
        else:
            status = str(result["status"])
            counts[status] += 1
            print(
                f"{status} symbol={symbol} effective_date={result['effective_date']} "
                f"raw_sha256={result['raw_sha256']} validation={result['validation']}"
            )
        if index < len(symbols) - 1:
            time.sleep(60 / args.requests_per_minute)
    print(
        f"SUMMARY selected={len(symbols)} COMPLETE={counts['COMPLETE']} "
        f"STALE={counts['STALE']} FAILED={counts['FAILED']}"
    )
    if counts["FAILED"] or counts["STALE"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
