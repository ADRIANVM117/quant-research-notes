"""Genera los recursos visuales de XLE desde el ledger auditado de ejecución.

La fuente es la simulación congelada de ``01_execution_feasibility.ipynb``.
Este script ejecuta sus celdas analíticas hasta ``execution-summary`` y extrae,
sin reconstruir la simulación, los NAV diarios del escenario IBKR Pro Fixed
modelado con 5 bps de slippage adverso.

Uso, desde la raíz del repositorio::

    .\\Momentum_systematic_strategies\\.venv\\Scripts\\python.exe \\
        Momentum_systematic_strategies/02_factor_momentum/scripts/generate_xle_execution_animation.py
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.ticker import FuncFormatter
import numpy as np
from PIL import Image


FACTOR_ROOT = Path(__file__).resolve().parents[1]
MOMENTUM_ROOT = FACTOR_ROOT.parent
EXECUTION_NOTEBOOK = (
    FACTOR_ROOT
    / "strategy_candidates"
    / "xle_systematic_momentum"
    / "notebooks"
    / "01_execution_feasibility.ipynb"
)
ASSETS = FACTOR_ROOT / "assets"
PNG_PATH = ASSETS / "xle_systematic_vs_buyhold_fixed_5bps.png"
GIF_PATH = ASSETS / "xle_systematic_vs_buyhold_fixed_5bps.gif"
SCENARIO = "IBKR Pro Fixed + 5 bps"
SYSTEMATIC = "Systematic momentum"
BUY_AND_HOLD = "Buy & Hold"
EXPECTED_SESSIONS = 1_853
INITIAL_CAPITAL = 10_000.0
FPS = 12
ACTIVE_FRAMES = 108
HOLD_FRAMES = 24


def execute_frozen_simulation() -> dict:
    """Ejecuta sólo el tramo de la notebook que construye su ledger original."""
    notebook = json.loads(EXECUTION_NOTEBOOK.read_text(encoding="utf-8"))
    namespace = {"__name__": "__execution_source__", "IN_COLAB": False}
    skipped = {"colab-bootstrap-execution", "p1-bootstrap-execution"}

    previous_directory = Path.cwd()
    try:
        # La notebook encuentra Gold a partir de este directorio, igual que en
        # su ejecución local habitual.
        os.chdir(MOMENTUM_ROOT)
        for cell in notebook["cells"]:
            if cell["cell_type"] != "code" or cell.get("id") in skipped:
                continue
            source = "".join(cell["source"])
            exec(compile(source, str(EXECUTION_NOTEBOOK), "exec"), namespace)
            if cell.get("id") == "execution-summary":
                return namespace
    finally:
        os.chdir(previous_directory)

    raise RuntimeError("No se encontró la celda execution-summary en la notebook de ejecución.")


def canonical_hash(dates: np.ndarray, nav: np.ndarray) -> str:
    """Hash de la trayectoria fecha/NAV usada literalmente por la gráfica."""
    payload = "\n".join(f"{date}|{value:.10f}" for date, value in zip(dates, nav))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_series(namespace: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, str]:
    """Extrae y valida las dos curvas a partir del ledger ya calculado."""
    pl = namespace["pl"]
    ledger = namespace["ledger"]
    summary = namespace["execution_summary"]

    series = {}
    for strategy in (SYSTEMATIC, BUY_AND_HOLD):
        history = ledger.filter(
            (pl.col("scenario") == SCENARIO) & (pl.col("strategy") == strategy)
        ).sort("date")
        if history.height != EXPECTED_SESSIONS:
            raise AssertionError(f"{strategy}: {history.height} sesiones; se esperaban {EXPECTED_SESSIONS}.")
        if history.get_column("date").null_count() or history.get_column("nav").null_count():
            raise AssertionError(f"{strategy}: el ledger tiene fechas o NAV nulos.")
        series[strategy] = history

    systematic = series[SYSTEMATIC]
    buy_hold = series[BUY_AND_HOLD]
    if systematic.get_column("date").to_list() != buy_hold.get_column("date").to_list():
        raise AssertionError("Las dos curvas no comparten las mismas fechas de ejecución.")

    dates = np.asarray(systematic.get_column("date").to_list())
    systematic_nav = systematic.get_column("nav").to_numpy()
    buy_hold_nav = buy_hold.get_column("nav").to_numpy()
    initial_date = systematic.get_column("signal_date")[0]
    if not initial_date < dates[0]:
        raise AssertionError("El punto inicial debe preceder a la primera sesión ejecutada.")

    # El punto inicial es una referencia contable, no una sesión o dato
    # interpolado. Los 1,853 NAV posteriores proceden directamente del ledger.
    plot_dates = np.r_[np.datetime64(initial_date), dates]
    plot_systematic = np.r_[INITIAL_CAPITAL, systematic_nav]
    plot_buy_hold = np.r_[INITIAL_CAPITAL, buy_hold_nav]

    if not np.array_equal(plot_dates[1:], dates):
        raise AssertionError("La gráfica alteró las fechas del ledger.")
    if not np.array_equal(plot_systematic[1:], systematic_nav) or not np.array_equal(plot_buy_hold[1:], buy_hold_nav):
        raise AssertionError("La gráfica alteró algún NAV del ledger.")

    def metric(strategy: str, column: str) -> float:
        return float(
            summary.filter((pl.col("scenario") == SCENARIO) & (pl.col("strategy") == strategy))
            .get_column(column)[0]
        )

    checks = {
        "Systematic capital final": (systematic_nav[-1], 28_028.02, 0.01),
        "Buy & Hold capital final": (buy_hold_nav[-1], 23_494.51, 0.01),
        "Systematic CAGR": (metric(SYSTEMATIC, "cagr_pct"), 15.046, 0.001),
        "Buy & Hold CAGR": (metric(BUY_AND_HOLD, "cagr_pct"), 12.318, 0.001),
        "Systematic max drawdown": (metric(SYSTEMATIC, "max_drawdown_pct"), -27.805, 0.001),
        "Buy & Hold max drawdown": (metric(BUY_AND_HOLD, "max_drawdown_pct"), -57.981, 0.001),
    }
    for label, (observed, expected, tolerance) in checks.items():
        if abs(observed - expected) > tolerance:
            raise AssertionError(f"{label}: {observed} no coincide con {expected}.")

    return plot_dates, plot_systematic, plot_buy_hold, dates, canonical_hash(dates, systematic_nav)


def build_figure(dates: np.ndarray, systematic: np.ndarray, buy_hold: np.ndarray):
    """Crea el lienzo común con escalas fijas para PNG y GIF."""
    figure, axis = plt.subplots(figsize=(9.6, 5.4), dpi=100)
    figure.patch.set_facecolor("#fbfcfe")
    axis.set_facecolor("#fbfcfe")
    axis.spines[["top", "right"]].set_visible(False)
    axis.spines[["left", "bottom"]].set_color("#cbd5e1")
    axis.grid(axis="y", color="#e2e8f0", linewidth=0.8)
    axis.set_xlim(dates[0], dates[-1])
    lower = max(0, (np.floor(min(systematic.min(), buy_hold.min()) / 1_000) - 1) * 1_000)
    upper = (np.ceil(max(systematic.max(), buy_hold.max()) / 1_000) + 1) * 1_000
    axis.set_ylim(lower, upper)
    axis.xaxis.set_major_locator(mdates.YearLocator())
    axis.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    axis.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f"${value / 1_000:.0f}k"))
    axis.tick_params(colors="#475569", labelsize=9)
    axis.set_title("XLE — evolución histórica simulada del capital", loc="left", pad=17, weight="bold", color="#0f172a")
    axis.text(0, 1.02, "IBKR Pro Fixed modelado + 5 bps de slippage adverso · USD 10,000 iniciales", transform=axis.transAxes, fontsize=9, color="#475569")
    axis.text(0, -0.17, "Simulación histórica · selección retrospectiva de XLE · no constituye validación prospectiva", transform=axis.transAxes, fontsize=8, color="#64748b")
    systematic_line, = axis.plot([], [], color="#0f766e", linewidth=2.4, label="Systematic Momentum 126d")
    buy_hold_line, = axis.plot([], [], color="#64748b", linewidth=1.9, label="XLE Buy & Hold")
    axis.legend(frameon=False, loc="upper left", fontsize=9)
    systematic_label = axis.annotate("", xy=(dates[-1], systematic[-1]), xytext=(-8, 10), textcoords="offset points", ha="right", color="#0f766e", fontsize=9, weight="bold")
    buy_hold_label = axis.annotate("", xy=(dates[-1], buy_hold[-1]), xytext=(-8, -15), textcoords="offset points", ha="right", color="#475569", fontsize=9, weight="bold")
    date_label = axis.text(1, 1.02, "", transform=axis.transAxes, ha="right", fontsize=9, color="#475569")
    figure.subplots_adjust(left=0.09, right=0.97, top=0.86, bottom=0.20)
    return figure, systematic_line, buy_hold_line, systematic_label, buy_hold_label, date_label


def save_static_png(dates: np.ndarray, systematic: np.ndarray, buy_hold: np.ndarray) -> None:
    figure, systematic_line, buy_hold_line, systematic_label, buy_hold_label, date_label = build_figure(dates, systematic, buy_hold)
    systematic_line.set_data(dates, systematic)
    buy_hold_line.set_data(dates, buy_hold)
    systematic_label.set_text(f"${systematic[-1]:,.2f}")
    buy_hold_label.set_text(f"${buy_hold[-1]:,.2f}")
    date_label.set_text(str(dates[-1])[:10])
    figure.savefig(PNG_PATH, dpi=180, facecolor=figure.get_facecolor())
    plt.close(figure)


def save_animation(dates: np.ndarray, systematic: np.ndarray, buy_hold: np.ndarray) -> None:
    frame_indices = np.unique(np.linspace(0, len(dates) - 1, ACTIVE_FRAMES, dtype=int))
    frame_indices = np.r_[frame_indices, np.repeat(len(dates) - 1, HOLD_FRAMES)]
    figure, systematic_line, buy_hold_line, systematic_label, buy_hold_label, date_label = build_figure(dates, systematic, buy_hold)

    def update(frame: int):
        index = frame_indices[frame]
        systematic_line.set_data(dates[: index + 1], systematic[: index + 1])
        buy_hold_line.set_data(dates[: index + 1], buy_hold[: index + 1])
        date_label.set_text(str(dates[index])[:10])
        if index == len(dates) - 1:
            systematic_label.set_text(f"${systematic[-1]:,.2f}")
            buy_hold_label.set_text(f"${buy_hold[-1]:,.2f}")
        else:
            systematic_label.set_text("")
            buy_hold_label.set_text("")
        return systematic_line, buy_hold_line, systematic_label, buy_hold_label, date_label

    temporary = GIF_PATH.with_suffix(".unoptimized.gif")
    animation = FuncAnimation(figure, update, frames=len(frame_indices), interval=1_000 / FPS, blit=False)
    animation.save(temporary, writer=PillowWriter(fps=FPS))
    plt.close(figure)

    # Reduce el tamaño para GitHub sin modificar observaciones de las curvas.
    with Image.open(temporary) as image:
        frames, durations = [], []
        try:
            while True:
                frames.append(image.convert("P", palette=Image.Palette.ADAPTIVE))
                durations.append(image.info.get("duration", int(1_000 / FPS)))
                image.seek(image.tell() + 1)
        except EOFError:
            pass
    frames[0].save(GIF_PATH, save_all=True, append_images=frames[1:], duration=durations, loop=0, disposal=2, optimize=True)
    temporary.unlink()


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    namespace = execute_frozen_simulation()
    dates, systematic, buy_hold, source_dates, systematic_hash = load_series(namespace)
    save_static_png(dates, systematic, buy_hold)
    save_animation(dates, systematic, buy_hold)
    print(f"Sesiones del ledger: {len(source_dates)}")
    print(f"Rango de ejecución: {source_dates[0]} a {source_dates[-1]}")
    print(f"SHA-256 trayectoria Systematic (fecha|NAV): {systematic_hash}")
    print(f"PNG: {PNG_PATH} ({PNG_PATH.stat().st_size:,} bytes)")
    print(f"GIF: {GIF_PATH} ({GIF_PATH.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
