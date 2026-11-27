"""Consulta educativa y acotada de ThetaData para SPY.

No es un descargador general. Solicita exclusivamente cinco minutos del
24-11-2026 y escribe las respuestas del SDK, sin cambios, en ``raw``.
Las copias ``processed`` añaden sólo metadatos de procedencia.
"""

from __future__ import annotations

import json
import os
import platform
from datetime import date, time
from importlib.metadata import version
from pathlib import Path
from typing import Any, Callable

import pandas as pd
from dotenv import load_dotenv
from thetadata import ThetaClient
import thetadata


SYMBOL = "SPY"
TRADE_DATE = date(2026, 11, 24)
START_TIME = time(10, 0)
END_TIME = time(10, 5)
TIMEZONE = "America/New_York"
STOCK_FEED = "nqb"


def _empty_frame() -> pd.DataFrame:
    return pd.DataFrame()


def _failure_kind(error: Exception) -> str:
    """Clasifica sin guardar ni mostrar el texto de una excepción."""
    message = str(error).lower()
    if any(word in message for word in ("unauth", "auth", "api key", "credential", "401")):
        return "authentication"
    if any(word in message for word in ("permission", "forbidden", "subscription", "entitlement", "403")):
        return "permission"
    if any(word in message for word in ("no data", "not found", "unavailable", "404")):
        return "availability"
    return "format_or_transport"


def _safe_call(name: str, call: Callable[[], pd.DataFrame], log: list[dict[str, Any]]) -> pd.DataFrame:
    """Ejecuta un endpoint y registra sólo estado y tipo de error seguro."""
    try:
        frame = call()
        if not isinstance(frame, pd.DataFrame):
            frame = pd.DataFrame(frame)
        log.append({"request": name, "status": "ok", "rows": len(frame), "failure_kind": None, "exception_type": None})
        return frame
    except Exception as error:  # La prueba debe continuar para aislar capacidades.
        log.append(
            {
                "request": name,
                "status": "failed",
                "rows": 0,
                "failure_kind": _failure_kind(error),
                "exception_type": type(error).__name__,
            }
        )
        return _empty_frame()


def _write_frame(frame: pd.DataFrame, raw_path: Path, processed_path: Path, endpoint: str, retrieved_at_utc: pd.Timestamp) -> None:
    """Guarda la respuesta intacta y una copia con metadatos de procedencia."""
    frame.to_parquet(raw_path, index=False)
    normalized = frame.copy()
    normalized["source_endpoint"] = endpoint
    normalized["retrieved_at_utc"] = retrieved_at_utc
    normalized.to_parquet(processed_path, index=False)


def _first_number(frame: pd.DataFrame, candidates: tuple[str, ...]) -> float | None:
    """Obtiene el primer número disponible sin asumir nombres de columnas."""
    for column in candidates:
        if column in frame.columns:
            values = pd.to_numeric(frame[column], errors="coerce").dropna()
            if not values.empty:
                return float(values.iloc[0])
    return None


def _initial_quote_mid(frame: pd.DataFrame) -> float | None:
    """Punto medio de la primera quote: el proxy de spot disponible al inicio."""
    if {"bid", "ask"}.issubset(frame.columns):
        quotes = frame[["bid", "ask"]].apply(pd.to_numeric, errors="coerce").dropna()
        if not quotes.empty:
            return float((quotes.iloc[0]["bid"] + quotes.iloc[0]["ask"]) / 2)
    return None


def _date_column(frame: pd.DataFrame) -> str | None:
    for column in ("expiration", "exp", "date"):
        if column in frame.columns:
            return column
    return None


def _pick_expiration(expirations: pd.DataFrame) -> date | None:
    column = _date_column(expirations)
    if column is None:
        return None
    candidates = pd.to_datetime(expirations[column], errors="coerce").dropna().dt.date
    candidates = sorted({value for value in candidates if 27 <= (value - TRADE_DATE).days <= 33})
    return min(candidates, key=lambda value: (abs((value - TRADE_DATE).days - 30), value)) if candidates else None


def _pick_strike(strikes: pd.DataFrame, spot: float | None) -> float | None:
    if spot is None:
        return None
    for column in ("strike", "strike_price"):
        if column in strikes.columns:
            values = pd.to_numeric(strikes[column], errors="coerce").dropna()
            if not values.empty:
                return float(min(values, key=lambda value: (abs(float(value) - spot), float(value))))
    return None


def _request_metadata(selected_expiration: date | None, selected_strike: float | None) -> dict[str, Any]:
    return {
        "symbol": SYMBOL,
        "trade_date": TRADE_DATE.isoformat(),
        "timezone": TIMEZONE,
        "requested_start_time": START_TIME.isoformat(),
        "requested_end_time": END_TIME.isoformat(),
        "stock_feed": STOCK_FEED,
        "sdk": "thetadata",
        "sdk_version": version("thetadata"),
        "python_version": platform.python_version(),
        "selected_expiration": selected_expiration.isoformat() if selected_expiration else None,
        "selected_strike": selected_strike,
        "timestamp_semantics": {
            "stock_ohlc": "En barras de 1m, timestamp es la apertura de la barra; incluye operaciones t <= trade_time < t+1m.",
            "stock_quote": "Con interval=1m, representa la última quote anterior al timestamp del intervalo.",
            "option_quote": "Con interval=1m, representa la última NBBO quote en el timestamp del intervalo.",
            "greeks": "Se calcula con midpoint de opción y subyacente; con intervalo, la quote de opción sigue las reglas de option_history_quote y el precio subyacente es el último en timestamp.",
        },
    }


def run_connection_check(project_root: Path) -> dict[str, Any]:
    """Ejecuta y archiva una sola prueba de conexión; devuelve tablas para la notebook."""
    project_root = Path(project_root).resolve()
    load_dotenv(project_root / ".env")
    api_key = os.getenv("THETADATA_API_KEY")
    if not api_key:
        raise RuntimeError("No se encontró la variable THETADATA_API_KEY; no se intentó ninguna petición.")

    stocks_raw = project_root / "data" / "stocks_data" / "raw"
    stocks_processed = project_root / "data" / "stocks_data" / "processed"
    options_raw = project_root / "data" / "options_data" / "raw"
    options_processed = project_root / "data" / "options_data" / "processed"
    for directory in (stocks_raw, stocks_processed, options_raw, options_processed):
        directory.mkdir(parents=True, exist_ok=True)

    log: list[dict[str, Any]] = []
    retrieved_at_utc = pd.Timestamp.now(tz="UTC")
    client = ThetaClient(api_key=api_key, dataframe_type="pandas")

    stock_ohlc = _safe_call(
        "stock_history_ohlc",
        lambda: client.stock_history_ohlc(SYMBOL, interval="1m", date=TRADE_DATE, start_time=START_TIME, end_time=END_TIME, venue=STOCK_FEED),
        log,
    )
    stock_quotes = _safe_call(
        "stock_history_quote",
        lambda: client.stock_history_quote(SYMBOL, interval="1m", date=TRADE_DATE, start_time=START_TIME, end_time=END_TIME, venue=STOCK_FEED),
        log,
    )
    expirations = _safe_call("option_list_expirations", lambda: client.option_list_expirations(SYMBOL), log)

    # La quote a 10:00 es la referencia inicial; OHLC sólo es respaldo si falta.
    spot = _initial_quote_mid(stock_quotes) or _first_number(stock_ohlc, ("open", "Open", "close", "Close"))
    selected_expiration = _pick_expiration(expirations)
    strikes = _empty_frame()
    if selected_expiration:
        strikes = _safe_call("option_list_strikes", lambda: client.option_list_strikes(SYMBOL, selected_expiration), log)
    else:
        log.append({"request": "option_list_strikes", "status": "not_run", "rows": 0, "failure_kind": "availability", "exception_type": None})
    selected_strike = _pick_strike(strikes, spot)

    option_quotes = _empty_frame()
    greeks = _empty_frame()
    if selected_expiration and selected_strike is not None:
        request_kwargs = dict(
            symbol=SYMBOL,
            expiration=selected_expiration,
            interval="1m",
            date=TRADE_DATE,
            strike=str(selected_strike),
            right="both",
            start_time=START_TIME,
            end_time=END_TIME,
        )
        option_quotes = _safe_call("option_history_quote", lambda: client.option_history_quote(**request_kwargs), log)
        greeks = _safe_call("option_history_greeks_first_order", lambda: client.option_history_greeks_first_order(**request_kwargs), log)
    else:
        for name in ("option_history_quote", "option_history_greeks_first_order"):
            log.append({"request": name, "status": "not_run", "rows": 0, "failure_kind": "availability", "exception_type": None})

    prefix = "spy_2026-11-24_1000_1005"
    datasets = [
        (stock_ohlc, stocks_raw / f"{prefix}_ohlc_1m_raw.parquet", stocks_processed / f"{prefix}_ohlc_1m_normalized.parquet", "stock_history_ohlc"),
        (stock_quotes, stocks_raw / f"{prefix}_quotes_1m_raw.parquet", stocks_processed / f"{prefix}_quotes_1m_normalized.parquet", "stock_history_quote"),
        (expirations, options_raw / f"{prefix}_expirations_raw.parquet", options_processed / f"{prefix}_expirations_normalized.parquet", "option_list_expirations"),
        (strikes, options_raw / f"{prefix}_strikes_raw.parquet", options_processed / f"{prefix}_strikes_normalized.parquet", "option_list_strikes"),
        (option_quotes, options_raw / f"{prefix}_selected_option_quotes_1m_raw.parquet", options_processed / f"{prefix}_selected_option_quotes_1m_normalized.parquet", "option_history_quote"),
        (greeks, options_raw / f"{prefix}_selected_option_greeks_1m_raw.parquet", options_processed / f"{prefix}_selected_option_greeks_1m_normalized.parquet", "option_history_greeks_first_order"),
    ]
    for frame, raw_path, processed_path, endpoint in datasets:
        _write_frame(frame, raw_path, processed_path, endpoint, retrieved_at_utc)

    metadata = _request_metadata(selected_expiration, selected_strike)
    metadata["responses"] = log
    metadata["raw_response_note"] = "El SDK remoto entrega DataFrames; los Parquet raw conservan esos DataFrames antes de normalización. El SDK no expone aquí el cuerpo gRPC original."
    report_path = options_processed / f"{prefix}_connection_check_metadata.json"
    report_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")

    summary = pd.DataFrame(log)
    selected = pd.DataFrame(
        [{"spot_from_initial_stock_quote_mid": spot, "expiration": selected_expiration, "dte_calendar": (selected_expiration - TRADE_DATE).days if selected_expiration else None, "strike": selected_strike, "right_requested": "both"}]
    )
    return {"summary": summary, "selected": selected, "stock_ohlc": stock_ohlc, "stock_quotes": stock_quotes, "expirations": expirations, "strikes": strikes, "option_quotes": option_quotes, "greeks": greeks, "metadata": metadata}


if __name__ == "__main__":
    result = run_connection_check(Path(__file__).resolve().parents[1])
    print(result["summary"].to_string(index=False))
