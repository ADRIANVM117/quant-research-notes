"""Resumable, raw-preserving audit of SPY option-chain continuity (A4 only)."""
from __future__ import annotations

import argparse
import concurrent.futures
import csv
import gzip
import json
import math
import os
import shutil
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from statistics import quantiles
from typing import Any

import requests
from dotenv import load_dotenv

import audit_checkpoint_a3_continuity as a3

ROOT = Path(__file__).resolve().parents[1]
RAW, REPORTS = ROOT / "data" / "raw", ROOT / "reports"
FAILURES, DAILY = RAW / "failures", RAW / "spy_time_series_daily_full.json"
START, END, URL = "2020-01-01", "2026-08-31", "https://www.alphavantage.co/query"


def raw_paths(day: str) -> tuple[Path, Path]:
    return RAW / f"spy_historical_options_{day}.json", RAW / f"spy_historical_options_{day}.json.gz"


def read_payload(path: Path) -> dict[str, Any]:
    content = gzip.open(path, "rt", encoding="utf-8").read() if path.suffix == ".gz" else path.read_text(encoding="utf-8")
    return json.loads(content)


def valid_payload(path: Path | None) -> bool:
    if not path:
        return False
    try:
        return isinstance(read_payload(path).get("data"), list)
    except (OSError, json.JSONDecodeError):
        return False


def existing(day: str) -> Path | None:
    plain, compressed = raw_paths(day)
    # Main-path files are written only after validating `data` as a list. Failed
    # provider payloads live under failures/, so existence is the resumable
    # validity manifest and avoids decompressing every saved chain per batch.
    for candidate in (plain, compressed):
        if candidate.exists():
            return candidate
    return None


def archive_failure(day: str, source: Path | None, payload: bytes | None, label: str) -> None:
    FAILURES.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%dT%H%M%S%f")
    destination = FAILURES / f"spy_historical_options_{day}_{label}_{stamp}.json.gz"
    if source:
        with gzip.open(destination, "wb") as out:
            out.write(source.read_bytes())
    elif payload is not None:
        with gzip.open(destination, "wb") as out:
            out.write(payload)


def fetch(day: str, key: str) -> tuple[str, str]:
    present = existing(day)
    if present:
        return day, "cached"
    plain, compressed = raw_paths(day)
    stale = plain if plain.exists() else (compressed if compressed.exists() else None)
    if stale:
        archive_failure(day, stale, None, "pre_retry")
    try:
        response = requests.get(URL, params={"function": "HISTORICAL_OPTIONS", "symbol": "SPY", "date": day, "apikey": key}, timeout=120)
        body = response.content
        payload = json.loads(body)
    except (requests.RequestException, json.JSONDecodeError) as error:
        archive_failure(day, None, (body if "body" in locals() else json.dumps({"audit_fetch_error": type(error).__name__}).encode()), "api_failure")
        return day, "api_failure"
    if not isinstance(payload.get("data"), list):
        archive_failure(day, None, body, "provider_error")
        return day, "api_failure"
    with gzip.open(compressed, "wb") as out:
        out.write(body)
    return day, "downloaded"


def expected_days() -> list[str]:
    series = json.loads(DAILY.read_text(encoding="utf-8"))["Time Series (Daily)"]
    return sorted(day for day in series if START <= day <= END)


def pair_with_raw_iv(records: list[dict[str, Any]]) -> dict[str, Any] | None:
    pair = a3.choose_pair(records)
    if not pair:
        return None
    pair["put_iv_raw"] = pair["put"].get("implied_volatility")
    pair["call_iv_raw"] = pair["call"].get("implied_volatility")
    return pair


def classify_no_pair(records: list[dict[str, Any]]) -> str:
    sides = {"put": set(), "call": set()}
    for record in records:
        if isinstance(record, dict):
            for side in sides:
                result = a3.contract_eligibility(record, side)
                if result:
                    sides[side].add(str(record["expiration"]))
    if not sides["put"]:
        return "no_eligible_put"
    if not sides["call"]:
        return "no_eligible_call"
    return "no_common_eligible_expiration"


def analyse(day: str) -> dict[str, Any]:
    path = existing(day)
    if not path:
        return {"date": day, "status": "api_failure", "reason": "no_valid_saved_response"}
    payload = read_payload(path)
    records = payload["data"]
    pair = pair_with_raw_iv(records)
    if not pair:
        return {"date": day, "status": "no_eligible_pair", "reason": classify_no_pair(records), "response_path": path.name}
    put_q, call_q = a3.quote(pair["put"]), a3.quote(pair["call"])
    status = "usable_pair" if put_q["usable"] and call_q["usable"] else "quote_problem"
    return {
        "date": day, "status": status, "reason": "", "response_path": path.name,
        "chain_date": pair["put"]["date"], "expiration": pair["expiration"], "dte": pair["dte"],
        "put_id": pair["put"]["contractID"], "call_id": pair["call"]["contractID"],
        "put_delta": a3.number(pair["put"]["delta"]), "call_delta": a3.number(pair["call"]["delta"]),
        "put_error": pair["put_error"], "call_error": pair["call_error"],
        "put_iv": a3.number(pair["put"]["implied_volatility"]), "call_iv": a3.number(pair["call"]["implied_volatility"]),
        "put_iv_raw": pair["put_iv_raw"], "call_iv_raw": pair["call_iv_raw"],
        "skew": a3.number(pair["put"]["implied_volatility"]) - a3.number(pair["call"]["implied_volatility"]),
        "put_bid": put_q["bid"], "put_ask": put_q["ask"], "put_spread": put_q["spread"], "put_flags": put_q["flags"],
        "call_bid": call_q["bid"], "call_ask": call_q["ask"], "call_spread": call_q["spread"], "call_flags": call_q["flags"],
    }


def longest_gap(rows: list[dict[str, Any]]) -> int:
    run = best = 0
    for row in rows:
        run = 0 if row["status"] == "usable_pair" else run + 1
        best = max(best, run)
    return best


def descriptor(values: list[float]) -> str:
    if not values:
        return "—"
    ordered = sorted(values)
    q05, q50, q95 = quantiles(ordered, n=100, method="inclusive")[4], quantiles(ordered, n=100, method="inclusive")[49], quantiles(ordered, n=100, method="inclusive")[94]
    return f"n={len(values)}; min={ordered[0]:.6g}; p05={q05:.6g}; p50={q50:.6g}; p95={q95:.6g}; max={ordered[-1]:.6g}"


def summary(label: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(row["status"] for row in rows)
    reasons = Counter(row.get("reason", "") for row in rows if row.get("reason"))
    flags = Counter(flag for row in rows for field in ("put_flags", "call_flags") for flag in row.get(field, "none").split(";") if flag != "none")
    selected = [row for row in rows if row["status"] in {"usable_pair", "quote_problem"}]
    spreads = [value for row in selected for value in (row["put_spread"], row["call_spread"]) if value is not None]
    errors = [value for row in selected for value in (row["put_error"], row["call_error"])]
    return {"period": label, "expected": len(rows), "responses": len(rows) - counts["api_failure"], "eligible": len(selected), "usable": counts["usable_pair"], "gap": longest_gap(rows), "api_failure": counts["api_failure"], "no_pair": counts["no_eligible_pair"], "quote_problem": counts["quote_problem"], "reasons": json.dumps(reasons, ensure_ascii=False), "quote_flags": json.dumps(flags, ensure_ascii=False), "dte": descriptor([row["dte"] for row in selected]), "delta_error": descriptor(errors), "spread": descriptor(spreads), "skew": descriptor([row["skew"] for row in selected])}


def write_csv(path: Path, rows: list[dict[str, Any]], headers: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, extrasaction="ignore")
        writer.writeheader(); writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-new", type=int, default=250)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--analyse-only", action="store_true")
    parser.add_argument("--until-complete", action="store_true", help="repeat bounded batches with a provider-cooldown pause")
    parser.add_argument("--cooldown-seconds", type=int, default=35)
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    key = os.getenv("ALPHAVANTAGE_API_KEY")
    if not key:
        raise SystemExit("ALPHAVANTAGE_API_KEY unavailable; no requests made.")
    RAW.mkdir(parents=True, exist_ok=True); REPORTS.mkdir(parents=True, exist_ok=True)
    days = expected_days()
    outcomes = Counter()
    while True:
        missing = [day for day in days if not existing(day)]
        selected = [] if args.analyse_only else missing[:max(args.max_new, 0)]
        if selected:
            with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
                for _, outcome in pool.map(lambda day: fetch(day, key), selected):
                    outcomes[outcome] += 1
        remaining = len([day for day in days if not existing(day)])
        if not (args.until_complete and remaining and selected):
            break
        print(f"A4 batch complete: outcomes={dict(outcomes)}, remaining={remaining}; cooling down.", flush=True)
        outcomes = Counter()
        time.sleep(max(args.cooldown_seconds, 1))
    if remaining:
        print(f"A4 download batch: attempted={len(selected)}, outcomes={dict(outcomes)}, remaining={remaining}; report deferred.")
        return

    rows = [analyse(day) for day in days]
    previous_skew = previous_expiry = None
    jumps = []
    for row in rows:
        if "skew" not in row:
            row.update({"skew_change": "", "expiry_change": "", "extreme_jump": "", "jump_with_expiry_change": ""})
            continue
        change = None if previous_skew is None else row["skew"] - previous_skew
        changed = previous_expiry is not None and row["expiration"] != previous_expiry
        extreme = change is not None and abs(change) > a3.SKEW_JUMP
        row.update({"skew_change": change, "expiry_change": changed, "extreme_jump": extreme, "jump_with_expiry_change": bool(extreme and changed)})
        if extreme:
            jumps.append(row.copy())
        previous_skew, previous_expiry = row["skew"], row["expiration"]
    headers = ["date", "status", "reason", "response_path", "chain_date", "expiration", "dte", "put_id", "call_id", "put_delta", "call_delta", "put_error", "call_error", "put_iv", "call_iv", "put_iv_raw", "call_iv_raw", "skew", "skew_change", "expiry_change", "extreme_jump", "jump_with_expiry_change", "put_bid", "put_ask", "put_spread", "put_flags", "call_bid", "call_ask", "call_spread", "call_flags"]
    write_csv(REPORTS / "checkpoint_a4_daily.csv", rows, headers)
    year_groups = {str(year): [row for row in rows if row["date"].startswith(str(year))] for year in range(2020, 2027)}
    month_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows: month_groups[row["date"][:7]].append(row)
    year_summary = [summary(label, subset) for label, subset in year_groups.items()]
    month_summary = [summary(label, subset) for label, subset in sorted(month_groups.items())]
    summary_headers = ["period", "expected", "responses", "eligible", "usable", "gap", "api_failure", "no_pair", "quote_problem", "reasons", "quote_flags", "dte", "delta_error", "spread", "skew"]
    write_csv(REPORTS / "checkpoint_a4_yearly.csv", year_summary, summary_headers)
    write_csv(REPORTS / "checkpoint_a4_monthly.csv", month_summary, summary_headers)
    write_csv(REPORTS / "checkpoint_a4_extreme_jumps.csv", jumps, headers)

    sample_days = []
    for year in range(2020, 2027):
        for month in ("01", "07"):
            candidates = [day for day in days if day.startswith(f"{year}-{month}")]
            if candidates: sample_days.append(candidates[0])
    samples = [row for row in rows if row["date"] in sample_days]
    write_csv(REPORTS / "checkpoint_a4_iv_raw_sample.csv", samples, headers)
    iv_occurrences: dict[tuple[str, str], list[str]] = defaultdict(list)
    for row in samples:
        if "put_iv_raw" in row:
            iv_occurrences[("put", str(row["put_iv_raw"]))].append(row["date"])
            iv_occurrences[("call", str(row["call_iv_raw"]))].append(row["date"])
    repeats = [(side, value, dates) for (side, value), dates in iv_occurrences.items() if len(dates) > 1]

    annual_ok = all(s["responses"] / s["expected"] >= .95 and s["eligible"] / s["expected"] >= .95 and s["usable"] / s["expected"] >= .95 and s["gap"] <= 5 for s in year_summary[:6])
    material = sum(s["usable"] for s in year_summary) >= 500
    decision = "GO" if annual_ok else ("REVISAR" if material else "STOP")
    lines = ["# Checkpoint A4 — auditoría de cobertura completa", "", "Solo calidad y suficiencia de datos; no hay modelo ni evaluación de alerta.", "", "## Cobertura anual", "", "| Año | Esperadas | Respuestas | Elegibles | Utilizables | Hueco | API / sin par / cotización |", "|---|---:|---:|---:|---:|---:|---|"]
    for s in year_summary:
        lines.append(f"| {s['period']} | {s['expected']} | {s['responses']} | {s['eligible']} | {s['usable']} | {s['gap']} | {s['api_failure']} / {s['no_pair']} / {s['quote_problem']} |")
    lines += ["", "## Cobertura mensual", "", "| Mes | Esperadas | Respuestas | Elegibles | Utilizables | Hueco | API / sin par / cotización |", "|---|---:|---:|---:|---:|---:|---|"]
    for s in month_summary:
        lines.append(f"| {s['period']} | {s['expected']} | {s['responses']} | {s['eligible']} | {s['usable']} | {s['gap']} | {s['api_failure']} / {s['no_pair']} / {s['quote_problem']} |")
    all_summary = summary("all", rows)
    lines += ["", "## Distribuciones seleccionadas", "", f"- DTE: {all_summary['dte']}", f"- Error absoluto de delta (ambos lados): {all_summary['delta_error']}", f"- Spread absoluto (ambos lados): {all_summary['spread']}", f"- Skew (IV put − IV call): {all_summary['skew']}", f"- Banderas de cotización: `{all_summary['quote_flags']}`", "", "## Saltos extremos de skew", "", f"Se hallaron {len(jumps)} cambios con magnitud > .05; {sum(bool(r['jump_with_expiry_change']) for r in jumps)} coincidieron con un cambio de vencimiento. El detalle completo está en `checkpoint_a4_extreme_jumps.csv`.", "", "## Verificación de IV idénticas", "", f"Muestra calendario fija: {', '.join(sample_days)}.", f"Valores de IV textualmente idénticos repetidos entre fechas en la muestra: {len(repeats)} grupos. El detalle bruto está en `checkpoint_a4_iv_raw_sample.csv`."]
    for side, value, dates in repeats:
        lines.append(f"- {side} IV `{value}`: {', '.join(dates)}")
    lines += ["", "## Decisión", "", f"**{decision} para suficiencia de datos.** El tramo efectivamente disponible en esta auditoría es {days[0]} a {days[-1]} si las filas utilizables conservan la cobertura indicada. Las conclusiones no implican que el skew anticipe caídas ni autorizan entrenamiento HMM."]
    (REPORTS / "checkpoint_a4_full_history_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"A4 analysis complete: sessions={len(rows)}, decision={decision}, extreme_jumps={len(jumps)}.")


if __name__ == "__main__":
    main()
