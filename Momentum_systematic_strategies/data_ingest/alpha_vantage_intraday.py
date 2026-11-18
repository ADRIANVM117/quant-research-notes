"""Captura intradía Alpha Vantage sin registrar credenciales ni URLs."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import polars as pl
import requests
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
API_URL = "https://www.alphavantage.co/query"
SCHEMA = {
    "symbol": pl.String, "bar_timestamp": pl.Datetime, "open": pl.Float64,
    "high": pl.Float64, "low": pl.Float64, "close": pl.Float64,
    "volume": pl.Int64, "provider_timezone": pl.String,
}


class IntradayError(RuntimeError):
    pass


def parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise argparse.ArgumentTypeError("BOOLEAN_MUST_BE_TRUE_OR_FALSE")


def api_key() -> str:
    value = os.getenv("ALPHAVANTAGE_API_KEY") or dotenv_values(ROOT / ".env").get("ALPHAVANTAGE_API_KEY")
    if not value:
        raise IntradayError("API_KEY_UNAVAILABLE")
    return value


def parse(payload: dict[str, object], symbol: str) -> tuple[pl.DataFrame, dict[str, str]]:
    if any(key in payload for key in ("Error Message", "Information", "Note")):
        raise IntradayError("API_MESSAGE")
    meta = payload.get("Meta Data")
    series = payload.get("Time Series (1min)")
    if not isinstance(meta, dict) or not isinstance(series, dict):
        raise IntradayError("PAYLOAD_STRUCTURE_INVALID")
    returned = str(meta.get("2. Symbol", "")).upper()
    interval = str(meta.get("4. Interval", ""))
    zone = str(meta.get("6. Time Zone", ""))
    if returned != symbol or interval != "1min" or not zone:
        raise IntradayError("METADATA_MISMATCH")
    rows = []
    for stamp, values in series.items():
        if not isinstance(values, dict):
            raise IntradayError("BAR_STRUCTURE_INVALID")
        try:
            row = {"symbol": symbol, "bar_timestamp": datetime.strptime(str(stamp), "%Y-%m-%d %H:%M:%S"),
                   "open": float(values["1. open"]), "high": float(values["2. high"]),
                   "low": float(values["3. low"]), "close": float(values["4. close"]),
                   "volume": int(values["5. volume"]), "provider_timezone": zone}
        except (KeyError, TypeError, ValueError) as exc:
            raise IntradayError("BAR_VALUE_INVALID") from exc
        if any(not math.isfinite(float(row[key])) or float(row[key]) <= 0 for key in ("open", "high", "low", "close")) or row["volume"] < 0:
            raise IntradayError("BAR_VALUE_INVALID")
        if row["high"] < max(row["open"], row["close"], row["low"]) or row["low"] > min(row["open"], row["close"], row["high"]):
            raise IntradayError("OHLC_INVALID")
        rows.append(row)
    frame = pl.DataFrame(rows, schema=SCHEMA, strict=True).sort("bar_timestamp")
    if frame.is_empty() or frame.get_column("bar_timestamp").n_unique() != frame.height:
        raise IntradayError("EMPTY_OR_DUPLICATE_TIMESTAMPS")
    return frame, {"symbol": returned, "interval": interval, "timezone": zone, "last_refreshed": str(meta.get("3. Last Refreshed", ""))}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--raw-root", type=Path, default=ROOT / "data" / "raw" / "intraday")
    parser.add_argument("--parquet-root", type=Path, default=ROOT / "data" / "parquet" / "intraday")
    parser.add_argument("--month", help="Historical month in YYYY-MM; requires --outputsize full")
    parser.add_argument("--outputsize", choices=("compact", "full"), default="compact")
    parser.add_argument("--adjusted", type=parse_bool, default=False)
    parser.add_argument("--extended-hours", type=parse_bool, default=False)
    parser.add_argument("--entitlement", default="realtime")
    args = parser.parse_args(); symbol = args.symbol.strip().upper()
    if args.month and (not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", args.month) or args.outputsize != "full"):
        raise IntradayError("HISTORICAL_MONTH_REQUIRES_YYYY_MM_AND_FULL_OUTPUT")
    captured = datetime.now(timezone.utc)
    try:
        parameters = {"function": "TIME_SERIES_INTRADAY", "symbol": symbol, "interval": "1min",
                      "entitlement": args.entitlement, "adjusted": str(args.adjusted).lower(),
                      "extended_hours": str(args.extended_hours).lower(), "outputsize": args.outputsize,
                      "apikey": api_key()}
        if args.month:
            parameters["month"] = args.month
        response = requests.get(API_URL, params=parameters, timeout=30)
        status = response.status_code; raw = response.content; response.raise_for_status()
    except requests.RequestException as exc:
        raise IntradayError("TRANSPORT_OR_HTTP_ERROR") from None
    args.raw_root.mkdir(parents=True, exist_ok=True)
    month_label = f"_{args.month}" if args.month else ""
    raw_path = args.raw_root / f"{symbol}{month_label}_{captured.strftime('%Y%m%dT%H%M%SZ')}.json"
    raw_path.write_bytes(raw)
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise IntradayError("RESPONSE_NOT_JSON") from exc
    frame, meta = parse(payload, symbol)
    destination = args.parquet_root / f"{symbol}_1min{month_label}.parquet"; destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        frame = pl.concat([pl.read_parquet(destination), frame]).unique(subset=["bar_timestamp"], keep="last").sort("bar_timestamp")
    frame.write_parquet(destination)
    print(json.dumps({"http_status":status,"capture_utc":captured.isoformat(),"raw_path":str(raw_path),"raw_sha256":hashlib.sha256(raw).hexdigest(),"parquet_path":str(destination),"count":frame.height,"first_bar":str(frame.get_column('bar_timestamp').min()),"last_bar":str(frame.get_column('bar_timestamp').max()),"month":args.month,"outputsize":args.outputsize,"adjusted":args.adjusted,"extended_hours":args.extended_hours,"entitlement":args.entitlement,**meta}, sort_keys=True))


if __name__ == "__main__":
    main()
