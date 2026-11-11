"""Ingesta diaria ajustada de un instrumento desde Alpha Vantage."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import polars as pl
import requests
from dotenv import dotenv_values, load_dotenv


API_URL = "https://www.alphavantage.co/query"
API_FUNCTION = "TIME_SERIES_DAILY_ADJUSTED"
START_DATE = date(2018, 1, 1)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / ".env"
ASSET_CLASS_DIRECTORIES = {
    "equity": PROJECT_ROOT / "data_daily" / "equity",
    "etf": PROJECT_ROOT / "data_daily" / "etf",
}
PARQUET_SCHEMA: dict[str, pl.DataType] = {
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
PRICE_COLUMNS = (
    "open",
    "high",
    "low",
    "close",
    "adjusted_close",
)
REQUIRED_DAILY_FIELDS = {
    "1. open": "open",
    "2. high": "high",
    "3. low": "low",
    "4. close": "close",
    "5. adjusted close": "adjusted_close",
    "6. volume": "volume",
    "7. dividend amount": "dividend_amount",
    "8. split coefficient": "split_coefficient",
}


class AlphaVantageDailyError(RuntimeError):
    """Error de validación o transporte sin incluir credenciales."""


def normalize_symbol(symbol: str) -> str:
    """Normaliza y valida el símbolo para usarlo como nombre de archivo."""
    normalized = symbol.strip().upper()
    if not normalized or not re.fullmatch(r"[A-Z0-9._-]+", normalized):
        raise ValueError("El símbolo contiene caracteres no permitidos.")
    return normalized


def output_path(symbol: str, asset_class: str) -> Path:
    """Devuelve la ruta Parquet para la clase de activo indicada."""
    try:
        directory = ASSET_CLASS_DIRECTORIES[asset_class]
    except KeyError as exc:
        raise ValueError("asset_class debe ser equity o etf.") from exc
    return directory / f"{normalize_symbol(symbol)}.parquet"


def get_api_key(env_file: Path = ENV_FILE, export_to_process: bool = True) -> str:
    """Carga la credencial desde el .env del proyecto sin imprimirla."""
    if export_to_process:
        load_dotenv(dotenv_path=env_file, override=False)
        api_key = os.getenv("ALPHAVANTAGE_API_KEY")
    else:
        api_key = dotenv_values(env_file).get("ALPHAVANTAGE_API_KEY")
    if not api_key:
        raise AlphaVantageDailyError("Falta la variable de entorno requerida.")
    return api_key


def request_daily_adjusted(symbol: str, outputsize: str) -> dict[str, Any]:
    """Solicita una respuesta diaria ajustada y rechaza respuestas de error."""
    response = requests.get(
        API_URL,
        params={
            "function": API_FUNCTION,
            "symbol": normalize_symbol(symbol),
            "outputsize": outputsize,
            "apikey": get_api_key(),
        },
        timeout=30,
    )
    response.raise_for_status()
    try:
        payload = response.json()
    except ValueError as exc:
        raise AlphaVantageDailyError("La respuesta del proveedor no es JSON válido.") from exc

    if not isinstance(payload, dict):
        raise AlphaVantageDailyError("La respuesta del proveedor tiene una estructura inválida.")
    if any(field in payload for field in ("Error Message", "Information", "Note")):
        raise AlphaVantageDailyError("El proveedor devolvió una respuesta no utilizable.")
    return payload


def request_daily_adjusted_raw(symbol: str, outputsize: str, env_file: Path = ENV_FILE, export_to_process: bool = True) -> tuple[int, bytes, dict[str, Any]]:
    """Request one response while retaining its original bytes for an isolated cut."""
    response = requests.get(API_URL, params={"function": API_FUNCTION, "symbol": normalize_symbol(symbol), "outputsize": outputsize, "apikey": get_api_key(env_file, export_to_process)}, timeout=30)
    status = response.status_code
    response.raise_for_status()
    raw = response.content
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AlphaVantageDailyError("La respuesta del proveedor no es JSON válido.") from exc
    if not isinstance(payload, dict) or any(field in payload for field in ("Error Message", "Information", "Note")):
        raise AlphaVantageDailyError("El proveedor devolvió una respuesta no utilizable.")
    return status, raw, payload


def update_isolated_daily(symbol: str, asset_class: str, destination_root: Path, target_date: date) -> dict[str, object]:
    """Write raw and Parquet only below an explicit research-owned destination."""
    normalized = normalize_symbol(symbol)
    raw_dir = destination_root / "raw"
    raw_path = raw_dir / f"{normalized}_{target_date.isoformat()}.json"
    reused_raw = raw_path.exists()
    if reused_raw:
        raw = raw_path.read_bytes()
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise AlphaVantageDailyError("El raw existente no es JSON válido.") from exc
        status: int | None = None
    else:
        status, raw, payload = request_daily_adjusted_raw(normalized, "full", ENV_FILE, False)
    frame = parse_daily_payload(payload, normalized)
    validate_daily_frame(frame)
    latest = frame.get_column("session_date").max()
    completeness = "COMPLETE" if latest == target_date else "STALE"
    raw_dir.mkdir(parents=True, exist_ok=True)
    if not reused_raw:
        raw_path.write_bytes(raw)
    destination = destination_root / "parquet" / asset_class / f"{normalized}.parquet"
    if destination.exists():
        final_frame = combine_daily_frames(load_existing_daily(destination), frame)
    else:
        final_frame = frame
    write_daily_atomically(final_frame, destination)
    return {"http_status": status, "symbol": normalized, "effective_date": latest.isoformat(), "status": completeness, "raw_path": str(raw_path), "raw_sha256": hashlib.sha256(raw).hexdigest(), "validation": "PASS", "parquet_path": str(destination), "raw_reused": reused_raw}


def _required_value(values: dict[str, Any], provider_key: str, session_date: str) -> str:
    value = values.get(provider_key)
    if value is None or value == "":
        raise AlphaVantageDailyError(
            f"Falta un campo diario requerido para la sesión {session_date}."
        )
    return str(value)


def parse_daily_payload(payload: dict[str, Any], symbol: str) -> pl.DataFrame:
    """Convierte la respuesta del proveedor al esquema canónico diario."""
    metadata = payload.get("Meta Data")
    series = payload.get("Time Series (Daily)")
    if not isinstance(metadata, dict):
        raise AlphaVantageDailyError("La respuesta no contiene Meta Data.")
    if not isinstance(series, dict):
        raise AlphaVantageDailyError("La respuesta no contiene Time Series (Daily).")

    requested_symbol = normalize_symbol(symbol)
    returned_symbol = str(metadata.get("2. Symbol", "")).strip().upper()
    if returned_symbol != requested_symbol:
        raise AlphaVantageDailyError("El símbolo devuelto no coincide con el solicitado.")

    provider_timezone = str(metadata.get("5. Time Zone", ""))
    provider_last_refreshed = str(metadata.get("3. Last Refreshed", ""))
    ingested_at_utc = datetime.now(timezone.utc)
    rows: list[dict[str, Any]] = []

    for session_date_text, values in series.items():
        if not isinstance(values, dict):
            raise AlphaVantageDailyError("Una observación diaria tiene una estructura inválida.")
        try:
            session_date = datetime.strptime(session_date_text, "%Y-%m-%d").date()
            row = {
                "symbol_requested": requested_symbol,
                "session_date": session_date,
                "open": float(_required_value(values, "1. open", session_date_text)),
                "high": float(_required_value(values, "2. high", session_date_text)),
                "low": float(_required_value(values, "3. low", session_date_text)),
                "close": float(_required_value(values, "4. close", session_date_text)),
                "adjusted_close": float(
                    _required_value(values, "5. adjusted close", session_date_text)
                ),
                "volume": int(_required_value(values, "6. volume", session_date_text)),
                "dividend_amount": float(
                    _required_value(values, "7. dividend amount", session_date_text)
                ),
                "split_coefficient": float(
                    _required_value(values, "8. split coefficient", session_date_text)
                ),
                "provider_timezone": provider_timezone,
                "source": "ALPHA_VANTAGE",
                "provider_last_refreshed": provider_last_refreshed,
                "ingested_at_utc": ingested_at_utc,
            }
        except (TypeError, ValueError) as exc:
            raise AlphaVantageDailyError(
                f"Una observación diaria no puede convertirse para la sesión {session_date_text}."
            ) from exc
        rows.append(row)

    frame = pl.DataFrame(rows, schema=PARQUET_SCHEMA, strict=True)
    return (
        frame.filter(pl.col("session_date") >= pl.lit(START_DATE))
        .sort("session_date")
    )


def validate_daily_frame(frame: pl.DataFrame) -> None:
    """Comprueba claves, tipos y restricciones económicas mínimas."""
    if frame.is_empty():
        raise AlphaVantageDailyError(
            f"No quedaron observaciones desde {START_DATE.isoformat()}."
        )
    if frame.columns != list(PARQUET_SCHEMA):
        raise AlphaVantageDailyError("El esquema de columnas no coincide con el contrato diario.")
    if frame.schema != pl.Schema(PARQUET_SCHEMA):
        raise AlphaVantageDailyError("Los tipos del esquema diario no coinciden con el contrato.")

    required_non_null = (
        "symbol_requested",
        "session_date",
        *PRICE_COLUMNS,
        "dividend_amount",
        "split_coefficient",
        "provider_timezone",
        "source",
        "provider_last_refreshed",
        "ingested_at_utc",
    )
    for column in required_non_null:
        if frame.get_column(column).null_count() != 0:
            raise AlphaVantageDailyError(f"El campo {column} contiene valores nulos.")

    if frame.get_column("session_date").n_unique() != frame.height:
        raise AlphaVantageDailyError("Existen claves duplicadas por session_date.")
    for column in PRICE_COLUMNS:
        if frame.select((pl.col(column) <= 0).any()).item():
            raise AlphaVantageDailyError(f"El campo {column} debe ser positivo.")
    if frame.select((pl.col("volume") < 0).fill_null(False).any()).item():
        raise AlphaVantageDailyError("volume no puede ser negativo.")
    if frame.select((pl.col("dividend_amount") < 0).any()).item():
        raise AlphaVantageDailyError("dividend_amount no puede ser negativo.")
    if frame.select((pl.col("split_coefficient") <= 0).any()).item():
        raise AlphaVantageDailyError("split_coefficient debe ser positivo.")

    invalid_high = (
        (pl.col("high") < pl.col("open"))
        | (pl.col("high") < pl.col("close"))
        | (pl.col("high") < pl.col("low"))
    )
    invalid_low = (
        (pl.col("low") > pl.col("open"))
        | (pl.col("low") > pl.col("close"))
        | (pl.col("low") > pl.col("high"))
    )
    if frame.select((invalid_high | invalid_low).any()).item():
        raise AlphaVantageDailyError("Los rangos OHLC no son consistentes.")


def load_existing_daily(path: Path) -> pl.DataFrame:
    """Lee y valida el histórico existente antes de intentar actualizarlo."""
    existing = pl.read_parquet(path)
    validate_daily_frame(existing)
    return existing


def combine_daily_frames(existing: pl.DataFrame, downloaded: pl.DataFrame) -> pl.DataFrame:
    """Une conservando la descarga más reciente cuando una fecha se repite."""
    combined = (
        pl.concat([existing, downloaded], how="vertical")
        .unique(subset=["session_date"], keep="last", maintain_order=True)
        .sort("session_date")
    )
    validate_daily_frame(combined)
    return combined


def write_daily_atomically(frame: pl.DataFrame, destination: Path) -> None:
    """Escribe, relee y reemplaza el destino solo después de validar el temporal."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = destination.with_name(
        f"{destination.name}.{uuid.uuid4().hex}.tmp.parquet"
    )
    try:
        temporary_path.touch(exist_ok=False)
        frame.write_parquet(temporary_path)
        temporary_frame = pl.read_parquet(temporary_path)
        validate_daily_frame(temporary_frame)
        if temporary_frame.height != frame.height or not temporary_frame.equals(frame):
            raise AlphaVantageDailyError(
                "El Parquet temporal no coincide con el DataFrame validado."
            )
        os.replace(temporary_path, destination)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def update_daily_history(symbol: str, asset_class: str) -> Path:
    """Descarga y actualiza el histórico diario ajustado de un único instrumento."""
    normalized_symbol = normalize_symbol(symbol)
    destination = output_path(normalized_symbol, asset_class)
    exists = destination.exists()
    payload = request_daily_adjusted(
        normalized_symbol,
        outputsize="compact" if exists else "full",
    )
    downloaded = parse_daily_payload(payload, normalized_symbol)
    validate_daily_frame(downloaded)

    if exists:
        final_frame = combine_daily_frames(load_existing_daily(destination), downloaded)
    else:
        final_frame = downloaded.sort("session_date")
        validate_daily_frame(final_frame)

    write_daily_atomically(final_frame, destination)
    return destination


def parse_args() -> argparse.Namespace:
    """Define la interfaz CLI de un símbolo y una clase de activo."""
    parser = argparse.ArgumentParser(
        description="Actualiza el histórico diario ajustado de un instrumento Alpha Vantage."
    )
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--asset-class", required=True, choices=("equity", "etf"))
    parser.add_argument("--destination-root", type=Path)
    parser.add_argument("--target-date", type=date.fromisoformat)
    return parser.parse_args()


def main() -> None:
    """Ejecuta la actualización solicitada por CLI."""
    args = parse_args()
    if bool(args.destination_root) != bool(args.target_date):
        raise AlphaVantageDailyError("--destination-root y --target-date deben indicarse juntos.")
    if args.destination_root:
        print(json.dumps(update_isolated_daily(args.symbol, args.asset_class, args.destination_root, args.target_date), sort_keys=True))
    else:
        print(update_daily_history(args.symbol, args.asset_class))


if __name__ == "__main__":
    main()
