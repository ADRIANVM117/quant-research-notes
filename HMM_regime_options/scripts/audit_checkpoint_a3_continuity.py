"""Bounded daily-continuity audit; no models or alert evaluation."""
from __future__ import annotations

import concurrent.futures
import csv
import json
import math
import os
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
REPORTS = ROOT / "reports"
DAILY_RAW = RAW / "spy_time_series_daily_full.json"
MONTHS = ("2025-01", "2023-01", "2021-01")
TARGET_DTE, MIN_DTE, MAX_DTE, DELTA_TOL = 30, 21, 45, 0.10
WIDE_SPREAD, SKEW_JUMP = 0.20, 0.05
URL = "https://www.alphavantage.co/query"


def number(value: Any) -> float | None:
    try:
        candidate = float(value)
        return candidate if math.isfinite(candidate) else None
    except (TypeError, ValueError):
        return None


def as_date(value: Any) -> date | None:
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def valid_id(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and value.strip().lower() not in {"none", "null", "nan", "-"}


def expected_days() -> dict[str, list[str]]:
    series = json.loads(DAILY_RAW.read_text(encoding="utf-8"))["Time Series (Daily)"]
    return {month: sorted(day for day in series if day.startswith(month)) for month in MONTHS}


def fetch(day: str, key: str) -> tuple[str, str, dict[str, Any]]:
    destination = RAW / f"spy_historical_options_{day}.json"
    if destination.exists():
        return day, "cached", json.loads(destination.read_text(encoding="utf-8"))
    try:
        response = requests.get(URL, params={"function": "HISTORICAL_OPTIONS", "symbol": "SPY", "date": day, "apikey": key}, timeout=120)
        payload = response.json()
        source = "downloaded"
    except (requests.RequestException, ValueError) as error:
        payload = {"audit_fetch_error": type(error).__name__}
        source = "api_failure"
    destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return day, source, payload


def contract_eligibility(record: dict[str, Any], side: str) -> tuple[int, float] | None:
    if str(record.get("type", "")).lower() != side or not valid_id(record.get("contractID")):
        return None
    chain_day, expiration = as_date(record.get("date")), as_date(record.get("expiration"))
    strike, iv, delta = number(record.get("strike")), number(record.get("implied_volatility")), number(record.get("delta"))
    if not chain_day or not expiration or strike is None or iv is None or delta is None:
        return None
    dte = (expiration - chain_day).days
    error = abs(delta - (-0.25 if side == "put" else 0.25))
    return (dte, error) if MIN_DTE <= dte <= MAX_DTE and error <= DELTA_TOL else None


def quote(record: dict[str, Any]) -> dict[str, Any]:
    bid, ask = number(record.get("bid")), number(record.get("ask"))
    flags: list[str] = []
    spread: float | None = None
    if bid is None or ask is None:
        flags.append("missing_or_invalid_bid_ask")
    else:
        spread = ask - bid
        if bid == 0:
            flags.append("bid_zero")
        if ask < bid:
            flags.append("ask_below_bid")
        if bid > 0 and ask > 0 and ask >= bid and spread / ((ask + bid) / 2) > WIDE_SPREAD:
            flags.append("wide_spread")
    return {"bid": bid, "ask": ask, "spread": spread, "flags": ";".join(flags) or "none", "usable": bid is not None and ask is not None and bid > 0 and ask >= bid}


def choose_pair(records: list[dict[str, Any]]) -> dict[str, Any] | None:
    grouped: dict[str, dict[str, list[tuple[dict[str, Any], int, float]]]] = defaultdict(lambda: {"put": [], "call": []})
    for record in records:
        if not isinstance(record, dict):
            continue
        for side in ("put", "call"):
            eligible = contract_eligibility(record, side)
            if eligible:
                dte, error = eligible
                grouped[str(record["expiration"])][side].append((record, dte, error))
    alternatives = []
    for expiry, sides in grouped.items():
        for put, dte, put_error in sides["put"]:
            for call, call_dte, call_error in sides["call"]:
                if dte != call_dte:
                    continue
                rank = (abs(dte - TARGET_DTE), put_error + call_error, max(put_error, call_error), str(put["contractID"]), str(call["contractID"]))
                alternatives.append((rank, {"expiration": expiry, "dte": dte, "put": put, "call": call, "put_error": put_error, "call_error": call_error}))
    return min(alternatives, key=lambda item: item[0])[1] if alternatives else None


def analyse(day: str, source: str, payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("audit_fetch_error"):
        return {"date": day, "source": source, "status": "api_failure", "detail": payload["audit_fetch_error"]}
    records = payload.get("data")
    if not isinstance(records, list):
        return {"date": day, "source": source, "status": "api_failure", "detail": payload.get("Note") or payload.get("Information") or payload.get("Error Message") or "invalid_response"}
    pair = choose_pair(records)
    if not pair:
        return {"date": day, "source": source, "status": "no_eligible_pair", "detail": "no_same_expiry_pair_within_fixed_DTE_delta_limits"}
    put_quote, call_quote = quote(pair["put"]), quote(pair["call"])
    status = "usable_pair" if put_quote["usable"] and call_quote["usable"] else "quote_problem"
    return {"date": day, "source": source, "status": status, "detail": "", "chain_date": pair["put"]["date"], "expiration": pair["expiration"], "dte": pair["dte"], "put_id": pair["put"]["contractID"], "call_id": pair["call"]["contractID"], "put_delta": number(pair["put"]["delta"]), "call_delta": number(pair["call"]["delta"]), "put_error": pair["put_error"], "call_error": pair["call_error"], "put_iv": number(pair["put"]["implied_volatility"]), "call_iv": number(pair["call"]["implied_volatility"]), "skew": number(pair["put"]["implied_volatility"]) - number(pair["call"]["implied_volatility"]), "put_bid": put_quote["bid"], "put_ask": put_quote["ask"], "put_spread": put_quote["spread"], "put_flags": put_quote["flags"], "call_bid": call_quote["bid"], "call_ask": call_quote["ask"], "call_spread": call_quote["spread"], "call_flags": call_quote["flags"]}


def longest_gap(rows: list[dict[str, Any]]) -> int:
    current = longest = 0
    for row in rows:
        current = 0 if row["status"] == "usable_pair" else current + 1
        longest = max(longest, current)
    return longest


def main() -> None:
    load_dotenv(ROOT / ".env")
    key = os.getenv("ALPHAVANTAGE_API_KEY")
    if not key:
        raise SystemExit("ALPHAVANTAGE_API_KEY unavailable; no requests made.")
    RAW.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    calendar = expected_days()
    all_days = [day for month in MONTHS for day in calendar[month]]
    fetched: dict[str, tuple[str, dict[str, Any]]] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(fetch, day, key) for day in all_days]
        for future in concurrent.futures.as_completed(futures):
            day, source, payload = future.result()
            fetched[day] = (source, payload)
    rows = [analyse(day, *fetched[day]) for day in all_days]
    previous_skew = previous_expiry = None
    for row in rows:
        if row["status"] in {"usable_pair", "quote_problem"}:
            change = None if previous_skew is None else row["skew"] - previous_skew
            expiry_change = previous_expiry is not None and row["expiration"] != previous_expiry
            row["skew_change"] = change
            row["expiry_change"] = expiry_change
            row["jump_with_expiry_change"] = bool(change is not None and abs(change) > SKEW_JUMP and expiry_change)
            previous_skew, previous_expiry = row["skew"], row["expiration"]
        else:
            row["skew_change"] = row["expiry_change"] = row["jump_with_expiry_change"] = ""
    headers = ["date", "source", "status", "detail", "chain_date", "expiration", "dte", "put_id", "call_id", "put_delta", "call_delta", "put_error", "call_error", "put_iv", "call_iv", "skew", "skew_change", "expiry_change", "jump_with_expiry_change", "put_bid", "put_ask", "put_spread", "put_flags", "call_bid", "call_ask", "call_spread", "call_flags"]
    with (REPORTS / "checkpoint_a3_continuity_daily.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
    month_rows = {month: [row for row in rows if row["date"].startswith(month)] for month in MONTHS}
    summaries = []
    for month, subset in month_rows.items():
        counts = {status: sum(row["status"] == status for row in subset) for status in ("api_failure", "no_eligible_pair", "quote_problem", "usable_pair")}
        eligible = counts["usable_pair"] + counts["quote_problem"]
        dtes = [row["dte"] for row in subset if "dte" in row]
        errors = [value for row in subset if "put_error" in row for value in (row["put_error"], row["call_error"])]
        summaries.append({"month": month, "expected": len(subset), "responses": len(subset) - counts["api_failure"], "eligible": eligible, "usable": counts["usable_pair"], "gap": longest_gap(subset), "api": counts["api_failure"], "no_pair": counts["no_eligible_pair"], "quote": counts["quote_problem"], "dte": f"{min(dtes)}–{max(dtes)}" if dtes else "—", "errors": f"{min(errors):.6g}–{max(errors):.6g}" if errors else "—"})
    go = all(summary["eligible"] / summary["expected"] >= .95 and summary["gap"] <= 1 for summary in summaries)
    stop = any(summary["responses"] == 0 for summary in summaries)
    decision = "STOP" if stop else ("GO" if go else "REVISAR")
    lines = ["# Checkpoint A3 — continuidad diaria", "", "Se usaron cadenas de todos los días de mercado preespecificados y se aplicó la regla v2 sin ajustes por fecha. La fecha de cadena es t; la disponibilidad se asume para la sesión siguiente.", "", "| Mes | Sesiones esperadas | Respuestas obtenidas | Par elegible | Cotizaciones utilizables | Hueco más largo | DTE | Error delta (mín–máx) | API / sin par / cotización |", "|---|---:|---:|---:|---:|---:|---|---|---|"]
    for summary in summaries:
        lines.append(f"| {summary['month']} | {summary['expected']} | {summary['responses']} | {summary['eligible']} | {summary['usable']} | {summary['gap']} | {summary['dte']} | {summary['errors']} | {summary['api']} / {summary['no_pair']} / {summary['quote']} |")
    lines += ["", "## Skew diario y cambios de vencimiento", "", "| Fecha | Cadena | Vencimiento / DTE | Skew (IV put − IV call) | Cambio | Cambio de vencimiento | Salto > .05 coincidente | Estado |", "|---|---|---|---:|---:|---|---|---|"]
    for row in rows:
        if "skew" not in row:
            lines.append(f"| {row['date']} | — | — | — | — | — | — | {row['status']} |")
        else:
            change = "—" if row["skew_change"] is None else f"{row['skew_change']:.6g}"
            lines.append(f"| {row['date']} | {row['chain_date']} | {row['expiration']} / {row['dte']} | {row['skew']:.6g} | {change} | {'sí' if row['expiry_change'] else 'no'} | {'sí' if row['jump_with_expiry_change'] else 'no'} | {row['status']} |")
    lines += ["", "## Decisión", "", f"**{decision} para ampliar a varios años, solo en viabilidad de datos.**", "", "Las fallas API, ausencia de par y problemas de cotización se separan en la tabla mensual y el CSV diario. `wide_spread`, bid cero, ask menor que bid y valores bid/ask inválidos aparecen por contrato en el CSV; no modifican la regla de selección."]
    (REPORTS / "checkpoint_a3_continuity_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"A3 complete: {len(rows)} expected sessions, decision={decision}; no model training performed.")


if __name__ == "__main__":
    main()
