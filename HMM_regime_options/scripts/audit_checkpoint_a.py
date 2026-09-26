"""Run the fixed, bounded data-feasibility audit for checkpoint A only."""

from __future__ import annotations

import csv
import json
import math
import os
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
REPORTS = ROOT / "reports"
DATES = {
    "2025-04-04": "Tensión: venta global posterior a anuncios arancelarios de EE. UU.",
    "2025-01-17": "Contraste reciente: entorno relativamente tranquilo de comienzos de año.",
    "2024-08-05": "Tensión: episodio de volatilidad global de inicios de agosto.",
    "2023-10-27": "Tensión: venta de renta variable de octubre de 2023.",
    "2022-06-13": "Tensión: ajuste por inflación y tipos de interés.",
    "2021-11-26": "Tensión: reacción inicial a la variante Ómicron.",
}
TARGET_DTE, MIN_DTE, MAX_DTE, DELTA_TOL = 30, 21, 45, 0.10
REQUIRED = ("date", "contractID", "type", "expiration", "strike", "implied_volatility", "delta")
MARKET_FIELDS = ("last", "mark", "bid", "ask", "volume", "open_interest")
URL = "https://www.alphavantage.co/query"


def number(value: Any) -> float | None:
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def valid_text(value: Any) -> bool:
    return isinstance(value, str) and value.strip() and value.strip().lower() not in {"none", "null", "nan", "-"}


def valid_date(value: Any) -> date | None:
    if not valid_text(value):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def safe_fetch(params: dict[str, str], destination: Path) -> dict[str, Any]:
    """Fetch without logging request URLs/parameters; raw payload contains no credential."""
    try:
        response = requests.get(URL, params=params, timeout=90)
        payload: dict[str, Any] = response.json()
    except (requests.RequestException, ValueError) as exc:
        payload = {"audit_fetch_error": type(exc).__name__}
    destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def load_raw(source: Path) -> dict[str, Any]:
    """Rebuild a report from an already-saved provider response without a new call."""
    return json.loads(source.read_text(encoding="utf-8"))


def record_valid(record: dict[str, Any]) -> tuple[bool, list[str], int | None]:
    problems: list[str] = []
    chain_day = valid_date(record.get("date"))
    expiration = valid_date(record.get("expiration"))
    for name in ("contractID", "type"):
        if not valid_text(record.get(name)):
            problems.append(name)
    for name in ("strike", "implied_volatility", "delta"):
        if number(record.get(name)) is None:
            problems.append(name)
    if chain_day is None:
        problems.append("date")
    if expiration is None:
        problems.append("expiration")
    dte = (expiration - chain_day).days if chain_day and expiration else None
    if dte is not None and dte < 0:
        problems.append("negative_dte")
    return not problems, problems, dte


def audit_chain(chosen_day: str, payload: dict[str, Any]) -> dict[str, Any]:
    records = payload.get("data") if isinstance(payload.get("data"), list) else []
    field_issues = Counter()
    market_issues = Counter()
    market_presence = Counter()
    candidates: dict[str, list[tuple[dict[str, Any], int, float]]] = {"put": [], "call": []}
    exclusions = Counter()
    reported_dates = Counter()

    for record in records:
        if not isinstance(record, dict):
            exclusions["non_object_record"] += 1
            continue
        for field in REQUIRED:
            if field in ("date", "contractID", "type", "expiration"):
                invalid = not valid_text(record.get(field))
            else:
                invalid = number(record.get(field)) is None
            if invalid:
                field_issues[field] += 1
        for field in MARKET_FIELDS:
            if field in record:
                market_presence[field] += 1
            if field not in record or number(record.get(field)) is None:
                market_issues[field] += 1
        if valid_text(record.get("date")):
            reported_dates[str(record["date"])] += 1

        usable, problems, dte = record_valid(record)
        if not usable:
            for problem in problems:
                exclusions[f"invalid_{problem}"] += 1
            continue
        option_type = str(record["type"]).lower()
        target = -0.25 if option_type == "put" else 0.25 if option_type == "call" else None
        if target is None:
            exclusions["unsupported_option_type"] += 1
            continue
        delta_error = abs(number(record["delta"]) - target)  # valid above
        if not (MIN_DTE <= dte <= MAX_DTE):
            exclusions["DTE_outside_21_45"] += 1
            continue
        if delta_error > DELTA_TOL:
            exclusions["delta_outside_tolerance"] += 1
            continue
        candidates[option_type].append((record, dte, delta_error))

    selected: dict[str, dict[str, Any] | None] = {}
    for option_type, items in candidates.items():
        if not items:
            selected[option_type] = None
            continue
        record, dte, delta_error = min(
            items,
            key=lambda item: (item[2], abs(item[1] - TARGET_DTE), str(item[0]["contractID"])),
        )
        selected[option_type] = {
            "contractID": record["contractID"], "dte": dte, "delta": number(record["delta"]),
            "iv": number(record["implied_volatility"]), "strike": number(record["strike"]),
            "delta_error": delta_error, "dte_error": abs(dte - TARGET_DTE),
        }

    return {
        "date": chosen_day, "records": len(records), "api_note": payload.get("Note") or payload.get("Information") or payload.get("Error Message"),
        "fetch_error": payload.get("audit_fetch_error"),
        "reported_dates": dict(reported_dates), "required_missing_or_invalid": dict(field_issues),
        "market_missing_or_invalid": dict(market_issues), "candidates_put": len(candidates["put"]),
        "market_present": dict(market_presence),
        "candidates_call": len(candidates["call"]), "selected_put": selected["put"],
        "selected_call": selected["call"], "exclusions": dict(exclusions),
    }


def daily_prices(payload: dict[str, Any]) -> dict[str, Any]:
    series = payload.get("Time Series (Daily)") if isinstance(payload.get("Time Series (Daily)"), dict) else {}
    return {day: series.get(day) for day in DATES}


def render_contract(contract: dict[str, Any] | None) -> str:
    if not contract:
        return "—"
    return (f"{contract['contractID']}; DTE={contract['dte']}; delta={contract['delta']:.6g}; "
            f"IV={contract['iv']:.6g}; |Δ error|={contract['delta_error']:.6g}; "
            f"|DTE−30|={contract['dte_error']}")


def main() -> int:
    load_dotenv(ROOT / ".env")
    key = os.getenv("ALPHAVANTAGE_API_KEY")
    if not key:
        print("ALPHAVANTAGE_API_KEY is not available after loading .env; no request made.")
        return 2
    RAW.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)

    results = []
    reuse_raw = "--reuse-raw" in sys.argv
    for day in DATES:
        raw_path = RAW / f"spy_historical_options_{day}.json"
        payload = (load_raw(raw_path) if reuse_raw else safe_fetch(
            {"function": "HISTORICAL_OPTIONS", "symbol": "SPY", "date": day, "apikey": key}, raw_path
        ))
        results.append(audit_chain(day, payload))
    price_path = RAW / "spy_time_series_daily_full.json"
    price_payload = (load_raw(price_path) if reuse_raw else safe_fetch(
        {"function": "TIME_SERIES_DAILY", "symbol": "SPY", "outputsize": "full", "apikey": key}, price_path
    ))
    prices = daily_prices(price_payload)

    columns = ["date", "selection_reason", "response_records", "reported_dates", "daily_price_present", "daily_close", "put_candidates", "call_candidates", "selected_put", "selected_call", "required_invalid", "market_invalid", "exclusions", "api_note"]
    with (REPORTS / "checkpoint_a_summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for result in results:
            price = prices[result["date"]]
            writer.writerow({
                "date": result["date"], "selection_reason": DATES[result["date"]], "response_records": result["records"],
                "reported_dates": json.dumps(result["reported_dates"], ensure_ascii=False), "daily_price_present": bool(price),
                "daily_close": price.get("4. close") if isinstance(price, dict) else "", "put_candidates": result["candidates_put"],
                "call_candidates": result["candidates_call"], "selected_put": render_contract(result["selected_put"]),
                "selected_call": render_contract(result["selected_call"]), "required_invalid": json.dumps(result["required_missing_or_invalid"]),
                "market_invalid": json.dumps(result["market_missing_or_invalid"]), "exclusions": json.dumps(result["exclusions"]),
                "api_note": result["api_note"] or result["fetch_error"] or "",
            })

    lines = ["# Checkpoint A — resultado de auditoría", "", "La metodología, muestra y límites se fijaron antes de las consultas en `docs/checkpoint_a_protocol.md`.", "", "| Fecha | Candidatos put/call | Put seleccionado | Call seleccionado | Precio diario | Alineación |", "|---|---:|---|---|---:|---|"]
    for result in results:
        price = prices[result["date"]]
        aligned = "sí" if result["date"] in result["reported_dates"] and price else "no / revisar"
        close = price.get("4. close", "—") if isinstance(price, dict) else "—"
        lines.append(f"| {result['date']} | {result['candidates_put']}/{result['candidates_call']} | {render_contract(result['selected_put'])} | {render_contract(result['selected_call'])} | {close} | {aligned} |")
    lines += ["", "## Cobertura de campos y exclusiones", ""]
    for result in results:
        lines += [f"### {result['date']}", f"- Registros recibidos: {result['records']}", f"- Fechas reportadas en cadena: `{json.dumps(result['reported_dates'])}`", f"- Requeridos faltantes/inválidos: `{json.dumps(result['required_missing_or_invalid'])}`", f"- Presencia de last/mark/bid/ask/volume/open_interest: `{json.dumps(result['market_present'])}`", f"- Precio/bid/ask/volumen/OI faltantes o inválidos: `{json.dumps(result['market_missing_or_invalid'])}`", f"- Exclusiones: `{json.dumps(result['exclusions'])}`"]
        if result["fetch_error"]:
            lines.append(f"- Fallo de transporte al consultar: `{result['fetch_error']}`")
        elif result["api_note"]:
            lines.append(f"- Respuesta del proveedor: `{result['api_note']}`")
        lines.append("")
    transport_failed = any(item["fetch_error"] for item in results) or "audit_fetch_error" in price_payload
    complete_candidates = all(item["selected_put"] and item["selected_call"] for item in results)
    aligned = all(prices[day] and day in item["reported_dates"] for day, item in zip(DATES, results))
    decision = "STOP por datos" if transport_failed else ("GO" if complete_candidates and aligned else "REVISAR")
    rationale = ("No fue posible obtener las respuestas del proveedor; no se puede evaluar cobertura ni calidad."
                 if transport_failed else ("Las seis fechas tienen selección put/call y calendario alineado."
                 if decision == "GO" else "Hay respuestas, pero falta cobertura completa de contratos comparables o alineación de calendario."))
    lines += ["## Disponibilidad temporal", "", "La documentación de Alpha Vantage especifica que `HISTORICAL_OPTIONS` devuelve la cadena para una fecha y que el parámetro de fecha omitido devuelve la sesión previa, pero no publica una marca de tiempo histórica de disponibilidad EOD. Se aplica por tanto la regla conservadora fijada: una cadena de t no se considera utilizable antes de una decisión posterior al cierre de t y, operativamente, se reserva para la siguiente sesión. Falta confirmar un SLA/timestamp de publicación del proveedor.", "", "## Decisión de viabilidad", "", f"**{decision}.** {rationale}", "", "Aspectos no verificados: hora exacta de publicación EOD, campos de liquidez suficientes, estabilidad de contrato al extender la muestra y coherencia de ajustes del subyacente."]
    (REPORTS / "checkpoint_a_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    if reuse_raw:
        print(f"Rebuilt audit from {len(results)} saved option chains and 1 saved daily-price response. Raw responses: {RAW}")
    else:
        print(f"Completed bounded audit: {len(results)} option-chain requests and 1 daily-price request. Raw responses: {RAW}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
