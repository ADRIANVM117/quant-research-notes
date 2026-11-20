"""XLE Systematic Momentum 126d: paper-trading preparation only.

This program has no IBKR order-submission implementation.  It can only probe
the local paper ports and write an explicitly blocked dry-run proposal.
"""

from __future__ import annotations

import json
import socket
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import polars as pl

SYMBOLS = ("SPY", "XLE", "IWM", "IWD", "IWF")
RESEARCH_START = date(2018, 1, 2)
OLS_WINDOW = 252
MOMENTUM_HORIZON = 126
MAX_BUDGET_USD = 10_000.0
PAPER_PORTS = (7497, 4002)  # TWS paper, IB Gateway paper defaults.
ORDER_TRANSMISSION_ENABLED = False  # This must remain false in this utility.


def project_root(start: Path) -> Path:
    for candidate in (start.resolve(), *start.resolve().parents):
        if (candidate / "data" / "gold" / "daily_series" / "etf").is_dir():
            return candidate
        project = candidate / "Momentum_systematic_strategies"
        if (project / "data" / "gold" / "daily_series" / "etf").is_dir():
            return project
    raise FileNotFoundError("No se encontró data/gold/daily_series/etf.")


def frozen_signal(root: Path) -> dict[str, object]:
    gold = root / "data" / "gold" / "daily_series" / "etf"
    frames = {
        symbol: pl.read_parquet(gold / f"{symbol}.parquet")
        .with_columns(pl.col("session_date").cast(pl.Date))
        .filter(pl.col("session_date") >= RESEARCH_START)
        .sort("session_date")
        for symbol in SYMBOLS
    }
    prices = frames["SPY"].select(pl.col("session_date").alias("date"), pl.col("adjusted_close").alias("SPY"))
    for symbol in SYMBOLS[1:]:
        prices = prices.join(
            frames[symbol].select(pl.col("session_date").alias("date"), pl.col("adjusted_close").alias(symbol)),
            on="date", how="inner",
        )
    returns = prices.with_columns([pl.col(symbol).log().diff().alias(f"{symbol}_ret") for symbol in SYMBOLS]).drop_nulls()
    model = returns.select("date", "XLE_ret", "SPY_ret", "IWM_ret", "IWF_ret", "IWD_ret").with_columns(
        pl.col("SPY_ret").alias("market"),
        (pl.col("IWM_ret") - pl.col("SPY_ret")).alias("size"),
        (pl.col("IWF_ret") - pl.col("IWD_ret")).alias("growth_value"),
    )
    factors = model.select("market", "size", "growth_value").to_numpy()
    actual = model.get_column("XLE_ret").to_numpy()
    systematic = []
    for index in range(OLS_WINDOW, len(actual)):
        design = np.column_stack((np.ones(OLS_WINDOW), factors[index - OLS_WINDOW:index]))
        beta = np.linalg.lstsq(design, actual[index - OLS_WINDOW:index], rcond=None)[0]
        systematic.append(beta[0] + factors[index] @ beta[1:])
    attribution = model.slice(OLS_WINDOW).with_columns(pl.Series("systematic_return", systematic))
    window = attribution.tail(MOMENTUM_HORIZON)
    signal_date = window.get_column("date")[-1]
    systematic_momentum = float(window.get_column("systematic_return").sum())
    return {
        "signal_date": signal_date.isoformat(),
        "systematic_momentum_126": systematic_momentum,
        "target": "LONG" if systematic_momentum > 0 else "CASH",
        "gold_last_session": signal_date.isoformat(),
    }


def probe_paper_ports() -> dict[str, bool]:
    result = {}
    for port in PAPER_PORTS:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                result[str(port)] = True
        except OSError:
            result[str(port)] = False
    return result


def append_blocked_proposal(folder: Path, signal: dict[str, object], ports: dict[str, bool]) -> Path:
    ledger_dir = folder / "ledger"
    ledger_dir.mkdir(parents=True, exist_ok=True)
    ledger = ledger_dir / "dry_run_proposals.jsonl"
    manual_stop = (folder / "MANUAL_STOP").exists()
    proposal = {
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "strategy": "XLE Systematic Momentum 126d",
        "symbol": "XLE",
        "contract_to_verify": {"secType": "STK", "exchange": "SMART", "currency": "USD", "primaryExchange": "ARCA"},
        "signal": signal,
        "max_budget_usd": MAX_BUDGET_USD,
        "cash_nonnegative": True,
        "leverage": False,
        "order_transmission_enabled": ORDER_TRANSMISSION_ENABLED,
        "manual_stop_active": manual_stop,
        "paper_port_probe": ports,
        "proposal_status": "BLOCKED_DRY_RUN_ONLY",
        "blockers": [
            "No hay conexión paper autenticada ni contrato validado.",
            "El último Gold puede no corresponder al cierre más reciente.",
            "No se conoce cash/posición/órdenes abiertas de la cuenta paper.",
            "La utilidad no contiene código de transmisión de órdenes.",
        ],
    }
    identity = (proposal["signal"]["signal_date"], proposal["signal"]["target"])
    if ledger.exists():
        for line in ledger.read_text(encoding="utf-8").splitlines():
            recorded = json.loads(line)
            prior = (recorded["signal"]["signal_date"], recorded["signal"]["target"])
            if prior == identity:
                print(f"Duplicate proposal suppressed for {identity[0]} / {identity[1]}.")
                return ledger
    with ledger.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(proposal, ensure_ascii=False) + "\n")
    return ledger


if __name__ == "__main__":
    candidate_dir = Path(__file__).resolve().parent
    root = project_root(candidate_dir)
    signal = frozen_signal(root)
    ports = probe_paper_ports()
    ledger = append_blocked_proposal(candidate_dir, signal, ports)
    print(json.dumps({"signal": signal, "paper_port_probe": ports, "ledger": str(ledger), "orders_sent": 0}, ensure_ascii=False, indent=2))
