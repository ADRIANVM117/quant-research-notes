"""Reevaluate checkpoint-A raw option chains using the frozen paired-expiry rule v2."""

from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
REPORT = ROOT / "reports" / "checkpoint_a_pair_selection_v2.md"
CSV = ROOT / "reports" / "checkpoint_a_pair_selection_v2.csv"
DATES = ("2025-04-04", "2025-01-17", "2024-08-05", "2023-10-27", "2022-06-13", "2021-11-26")
TARGET_DTE, MIN_DTE, MAX_DTE, DELTA_TOL, WIDE_SPREAD = 30, 21, 45, 0.10, 0.20


def as_number(value: Any) -> float | None:
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def as_date(value: Any) -> date | None:
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def valid_id(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and value.strip().lower() not in {"none", "null", "nan", "-"}


def eligible_contract(record: dict[str, Any], side: str) -> tuple[int, float] | None:
    if str(record.get("type", "")).lower() != side or not valid_id(record.get("contractID")):
        return None
    chain_day, expiry = as_date(record.get("date")), as_date(record.get("expiration"))
    strike, iv, delta = as_number(record.get("strike")), as_number(record.get("implied_volatility")), as_number(record.get("delta"))
    if not chain_day or not expiry or strike is None or iv is None or delta is None:
        return None
    dte = (expiry - chain_day).days
    target = -0.25 if side == "put" else 0.25
    error = abs(delta - target)
    return (dte, error) if MIN_DTE <= dte <= MAX_DTE and error <= DELTA_TOL else None


def quote_audit(record: dict[str, Any]) -> dict[str, Any]:
    bid, ask = as_number(record.get("bid")), as_number(record.get("ask"))
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
        if bid > 0 and ask > 0 and ask >= bid:
            mid = (ask + bid) / 2
            if mid and spread / mid > WIDE_SPREAD:
                flags.append("wide_spread")
    return {"bid": bid, "ask": ask, "spread": spread, "flags": "; ".join(flags) or "none"}


def choose_pair(records: list[dict[str, Any]]) -> dict[str, Any] | None:
    by_expiry: dict[str, dict[str, list[tuple[dict[str, Any], int, float]]]] = defaultdict(lambda: {"put": [], "call": []})
    for record in records:
        if not isinstance(record, dict):
            continue
        for side in ("put", "call"):
            result = eligible_contract(record, side)
            if result:
                dte, delta_error = result
                by_expiry[str(record["expiration"])][side].append((record, dte, delta_error))
    pairs: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
    for expiry, sides in by_expiry.items():
        for put, dte, put_error in sides["put"]:
            for call, call_dte, call_error in sides["call"]:
                if dte != call_dte:
                    raise ValueError(f"DTE mismatch within expiration {expiry}")
                ranking = (abs(dte - TARGET_DTE), put_error + call_error, max(put_error, call_error), str(put["contractID"]), str(call["contractID"]))
                pairs.append((ranking, {"expiry": expiry, "dte": dte, "put": put, "call": call, "put_error": put_error, "call_error": call_error}))
    return min(pairs, key=lambda item: item[0])[1] if pairs else None


def compact_contract(record: dict[str, Any], delta_error: float) -> dict[str, Any]:
    quote = quote_audit(record)
    return {"id": record["contractID"], "delta": as_number(record["delta"]), "iv": as_number(record["implied_volatility"]), "delta_error": delta_error, **quote}


def main() -> None:
    rows = []
    for chosen_day in DATES:
        payload = json.loads((RAW / f"spy_historical_options_{chosen_day}.json").read_text(encoding="utf-8"))
        pair = choose_pair(payload.get("data", []))
        if not pair:
            rows.append({"date": chosen_day, "eligible": "no", "expiry": "", "dte": "", "put": None, "call": None})
        else:
            rows.append({"date": chosen_day, "eligible": "yes", "expiry": pair["expiry"], "dte": pair["dte"], "put": compact_contract(pair["put"], pair["put_error"]), "call": compact_contract(pair["call"], pair["call_error"])})

    CSV.parent.mkdir(parents=True, exist_ok=True)
    headers = ["date", "eligible", "expiration", "dte", "put_id", "put_delta", "put_iv", "put_delta_error", "put_bid", "put_ask", "put_spread", "put_flags", "call_id", "call_delta", "call_iv", "call_delta_error", "call_bid", "call_ask", "call_spread", "call_flags"]
    with CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            put, call = row["put"], row["call"]
            writer.writerow({"date": row["date"], "eligible": row["eligible"], "expiration": row["expiry"], "dte": row["dte"], **({} if not put else {f"put_{key}": value for key, value in put.items()}), **({} if not call else {f"call_{key}": value for key, value in call.items()})})

    survivors = sum(row["eligible"] == "yes" for row in rows)
    lines = ["# Checkpoint A — reevaluación por par v2", "", "Esta salida usa exclusivamente respuestas crudas existentes. No modifica `docs/checkpoint_a_protocol.md` ni `reports/checkpoint_a_report.md`.", "", f"**Fechas elegibles: {survivors} de {len(rows)}.**", "", "| Fecha | Elegible | Vencimiento / DTE | Put (ID; delta; IV; bid / ask / spread; banderas) | Call (ID; delta; IV; bid / ask / spread; banderas) |", "|---|---|---|---|---|"]
    for row in rows:
        if row["eligible"] == "no":
            lines.append(f"| {row['date']} | no | — | — | — |")
            continue
        def display(side: dict[str, Any]) -> str:
            return f"{side['id']}; Δ={side['delta']:.6g} (err={side['delta_error']:.6g}); IV={side['iv']:.6g}; {side['bid']:.6g} / {side['ask']:.6g} / {side['spread']:.6g}; {side['flags']}"
        lines.append(f"| {row['date']} | sí | {row['expiry']} / {row['dte']} | {display(row['put'])} | {display(row['call'])} |")
    lines += ["", "## Interpretación de banderas", "", "`missing_or_invalid_bid_ask` se refiere exclusivamente a ausencia/valor no numérico/no finito. `bid_zero`, `ask_below_bid` y `wide_spread` se reportan por separado, con `wide_spread` definido antes del cálculo como spread/mid > 20%. La selección no usa cotizaciones.", "", "Regla y desempates: `docs/checkpoint_a_pair_selection_v2.md`."]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Reevaluated {len(rows)} raw chains; eligible paired expiries: {survivors}.")


if __name__ == "__main__":
    main()
