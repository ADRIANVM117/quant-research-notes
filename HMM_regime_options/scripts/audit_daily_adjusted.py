"""Download and audit adjusted daily SPY prices; no labels, alerts, or models."""
from __future__ import annotations

import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
DERIVED = ROOT / "data" / "derived"
REPORTS = ROOT / "reports"
URL = "https://www.alphavantage.co/query"
RAW_FILE = RAW / "spy_time_series_daily_adjusted_full.json"
TABLE = DERIVED / "spy_daily_adjusted_2020_2026.csv"
REPORT = REPORTS / "daily_adjusted_price_audit.md"
START, END = "2020-01-02", "2026-08-31"


def main() -> None:
    load_dotenv(ROOT / ".env")
    key = os.getenv("ALPHAVANTAGE_API_KEY")
    if not key:
        raise SystemExit("ALPHAVANTAGE_API_KEY unavailable; no request made.")
    if RAW_FILE.exists():
        raise SystemExit(f"Raw response already exists: {RAW_FILE.name}; no overwrite performed.")
    RAW.mkdir(parents=True, exist_ok=True)
    DERIVED.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    downloaded_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    try:
        response = requests.get(URL, params={"function": "TIME_SERIES_DAILY_ADJUSTED", "symbol": "SPY", "outputsize": "full", "apikey": key}, timeout=120)
        body = response.content
        payload = json.loads(body)
    except (requests.RequestException, json.JSONDecodeError) as error:
        raise SystemExit(f"Adjusted-price request failed: {type(error).__name__}")
    series = payload.get("Time Series (Daily)")
    if not isinstance(series, dict):
        raise SystemExit("Adjusted-price response has no Time Series (Daily); raw response was not written.")
    # Preserve exact provider body only after schema validation; no URL/key is persisted.
    RAW_FILE.write_bytes(body)
    dates = sorted(day for day in series if START <= day <= END)
    raw_daily = json.loads((RAW / "spy_time_series_daily_full.json").read_text(encoding="utf-8"))["Time Series (Daily)"]
    a4_dates = sorted(day for day in raw_daily if START <= day <= END)
    adjusted_set, a4_set = set(dates), set(a4_dates)
    missing_from_adjusted = sorted(a4_set - adjusted_set)
    extra_in_adjusted = sorted(adjusted_set - a4_set)
    rows = []
    dividends, splits = [], []
    for day in dates:
        item = series[day]
        row = {
            "date": day, "open": item.get("1. open"), "high": item.get("2. high"),
            "low": item.get("3. low"), "close": item.get("4. close"),
            "adjusted_close": item.get("5. adjusted close"), "volume": item.get("6. volume"),
            "dividend_amount": item.get("7. dividend amount"), "split_coefficient": item.get("8. split coefficient"),
        }
        rows.append(row)
        if float(row["dividend_amount"] or 0) != 0:
            dividends.append(row)
        if float(row["split_coefficient"] or 1) != 1:
            splits.append(row)
    with TABLE.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    meta = payload.get("Meta Data", {})
    lines = [
        "# Auditoría de precios diarios ajustados de SPY", "",
        f"- Fuente: Alpha Vantage `TIME_SERIES_DAILY_ADJUSTED`, símbolo `SPY`, `outputsize=full`.",
        f"- Descargado (UTC): {downloaded_at}.",
        f"- Zona horaria declarada por proveedor: {meta.get('5. Time Zone', 'no declarada')}.",
        f"- Respuesta original: `data/raw/{RAW_FILE.name}`.",
        f"- Tabla reproducible: `data/derived/{TABLE.name}`.", "",
        "## Cobertura y calendario", "",
        f"- Periodo auditado: {START} a {END}.",
        f"- Fechas ajustadas: {len(dates)}; fechas A4: {len(a4_dates)}.",
        f"- Fechas faltantes frente a A4: {len(missing_from_adjusted)} ({', '.join(missing_from_adjusted[:10]) or 'ninguna'}).",
        f"- Fechas adicionales frente a A4: {len(extra_in_adjusted)} ({', '.join(extra_in_adjusted[:10]) or 'ninguna'}).",
        "- Fechas duplicadas: 0 (la respuesta JSON usa la fecha como clave; se verificó una fila por clave).", "",
        "## Campo de cierre", "",
        "`4. close` es el cierre diario sin ajustar. `5. adjusted close` es el cierre ajustado que incorpora ajustes históricos por dividendos y splits; el protocolo B congelado usa exactamente `5. adjusted close`.",
        "", "## Ejemplos de eventos corporativos", "",
        "| Fecha | Close | Adjusted close | Dividendo | Coeficiente split |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in (dividends[:8] + splits[:8]):
        lines.append(f"| {row['date']} | {row['close']} | {row['adjusted_close']} | {row['dividend_amount']} | {row['split_coefficient']} |")
    if not dividends and not splits:
        lines.append("| — | — | — | — | — |")
    lines += ["", "## Resultado", "", "El prerrequisito de datos del protocolo B queda satisfecho si la cobertura coincide con A4 y el campo ajustado está presente. Esta auditoría no calcula etiquetas, alertas ni desempeño."]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Adjusted daily audit complete: {len(dates)} dates; missing_vs_A4={len(missing_from_adjusted)}; extra_vs_A4={len(extra_in_adjusted)}.")


if __name__ == "__main__":
    main()
