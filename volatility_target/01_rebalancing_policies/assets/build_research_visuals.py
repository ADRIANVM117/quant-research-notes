"""Genera los recursos visuales del README a partir de los insumos certificados.

Ejecución desde la raíz del repositorio:
    volatility_target/.venv/Scripts/python.exe \
        volatility_target/01_rebalancing_policies/assets/build_research_visuals.py
"""

from __future__ import annotations

import json
import math
import os
from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import polars as pl
from matplotlib.animation import PillowWriter


ASSET_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = ASSET_DIR.parents[2]
NOTEBOOK_DIR = PROJECT_ROOT / "volatility_target" / "01_rebalancing_policies"
INITIAL_NAV_USD = 10_891.246187363835
POLICIES = [
    "P0 — Daily",
    "P1 — Banda 5 pp",
    "P2 — Banda 10 pp",
    "B1 — Buy & Hold SPY",
    "B2 — Asignación estática 60/40",
]
COLORS = {
    "P0 — Daily": "#1f77b4",
    "P1 — Banda 5 pp": "#ff7f0e",
    "P2 — Banda 10 pp": "#2ca02c",
    "B1 — Buy & Hold SPY": "#9467bd",
    "B2 — Asignación estática 60/40": "#8c564b",
}
EXPECTED_FINAL_NAV = {
    "P0 — Daily": 20_946.398124753934,
    "P1 — Banda 5 pp": 22_024.794436598226,
    "P2 — Banda 10 pp": 21_982.64015029923,
    "B1 — Buy & Hold SPY": 30_797.605472,
    "B2 — Asignación estática 60/40": 22_834.661758,
}


def notebook_cell(notebook_name: str, cell_id: str) -> str:
    """Devuelve el código de una celda por id, sin alterar la notebook."""
    notebook = json.loads((NOTEBOOK_DIR / notebook_name).read_text(encoding="utf-8"))
    for cell in notebook["cells"]:
        if cell.get("id") == cell_id:
            return "".join(cell["source"])
    raise KeyError(f"No existe la celda {cell_id} en {notebook_name}.")


def load_validated_histories() -> tuple[dict[str, pl.DataFrame], pl.DataFrame]:
    """Ejecuta las celdas certificadas que reconstruyen B1 y B2."""
    os.chdir(PROJECT_ROOT)
    namespace: dict[str, object] = {"__name__": "__research_visual_builder__"}
    for notebook_name, cell_id in [
        ("03_economic_statistic_evaluation.ipynb", "load-validated-policy-histories"),
        ("03_economic_statistic_evaluation.ipynb", "build-benchmark-b1"),
        ("03_economic_statistic_evaluation.ipynb", "build-benchmark-b2"),
        ("02_rebalancing_policies.ipynb", "ewma-forecast"),
    ]:
        exec(notebook_cell(notebook_name, cell_id), namespace)

    histories = {
        "P0 — Daily": namespace["policy_p0"],
        "P1 — Banda 5 pp": namespace["policy_p1"],
        "P2 — Banda 10 pp": namespace["policy_p2"],
        "B1 — Buy & Hold SPY": namespace["benchmark_b1"],
        "B2 — Asignación estática 60/40": namespace["benchmark_b2"],
    }
    for policy, history in histories.items():
        if not math.isclose(
            float(history["portfolio_value_close"][-1]),
            EXPECTED_FINAL_NAV[policy],
            rel_tol=0.0,
            abs_tol=1e-6,
        ):
            raise ValueError(f"{policy}: NAV final no coincide con el resultado certificado.")

    reference_dates = histories["P0 — Daily"]["session_date"].to_list()
    if any(history["session_date"].to_list() != reference_dates for history in histories.values()):
        raise ValueError("Los cinco historiales no comparten el calendario certificado.")
    return histories, namespace["ewma"]


def apply_editorial_style(axis: plt.Axes) -> None:
    axis.spines[["top", "right"]].set_visible(False)
    axis.grid(axis="y", color="#d9dce1", linewidth=0.7, alpha=0.8)
    axis.set_facecolor("#fbfcfe")


def build_economic_tradeoff(histories: dict[str, pl.DataFrame]) -> Path:
    """Crea crecimiento normalizado y drawdown con el calendario común."""
    figure, axes = plt.subplots(2, 1, figsize=(12, 8.2), sharex=True)

    for policy in POLICIES:
        history = histories[policy].sort("session_date")
        dates = history["session_date"].to_list()
        nav = history["portfolio_value_close"].to_numpy()
        wealth = nav / INITIAL_NAV_USD
        high_water_mark = np.maximum.accumulate(np.concatenate(([INITIAL_NAV_USD], nav)))[1:]
        drawdown = nav / high_water_mark - 1
        linestyle = "-" if policy.startswith("P") else "--"

        axes[0].plot(dates, wealth, label=policy, color=COLORS[policy], lw=1.7, ls=linestyle)
        axes[1].plot(dates, drawdown, label=policy, color=COLORS[policy], lw=1.7, ls=linestyle)

    axes[0].set_title("Crecimiento de una unidad de capital inicial", loc="left", fontweight="bold")
    axes[0].set_ylabel("Índice de riqueza")
    axes[1].set_title("Drawdown histórico", loc="left", fontweight="bold")
    axes[1].set_ylabel("Drawdown")
    axes[1].set_xlabel("")
    axes[1].yaxis.set_major_formatter(lambda value, _: f"{value:.0%}")
    axes[1].axhline(0, color="#4b5563", lw=0.8)
    axes[1].xaxis.set_major_locator(mdates.YearLocator())
    axes[1].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    for axis in axes:
        apply_editorial_style(axis)

    handles, labels = axes[0].get_legend_handles_labels()
    figure.legend(handles, labels, loc="upper center", ncol=3, frameon=False, bbox_to_anchor=(0.5, 0.99))
    figure.subplots_adjust(left=0.08, right=0.98, top=0.88, bottom=0.09, hspace=0.10)
    output = ASSET_DIR / "economic_tradeoff.png"
    figure.savefig(output, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(figure)
    return output


def build_volatility_to_exposure_gif(
    histories: dict[str, pl.DataFrame], ewma: pl.DataFrame
) -> Path:
    """Anima el episodio COVID sin mover la señal respecto de su ejecución."""
    start, trough, end = date(2020, 2, 20), date(2020, 3, 23), date(2020, 4, 30)
    p0 = histories["P0 — Daily"].filter(
        pl.col("session_date").is_between(start, end, closed="both")
    ).sort("session_date")
    episode_dates = p0["session_date"].to_list()
    target_weight = p0["target_weight"].to_numpy()
    forecast = ewma.filter(
        pl.col("forecast_for_date").is_between(start, end, closed="both")
    ).sort("forecast_for_date")
    if not episode_dates or forecast.is_empty():
        raise ValueError("El episodio de estrés seleccionado no está disponible.")

    weights = {
        policy: histories[policy]
        .filter(pl.col("session_date").is_between(start, end, closed="both"))
        .sort("session_date")
        for policy in POLICIES[:3]
    }
    if any(frame["session_date"].to_list() != episode_dates for frame in weights.values()):
        raise ValueError("Las políticas no están alineadas durante el episodio de estrés.")

    fixed_volatility_max = float(forecast["forecast_vol_annualized"].max()) * 1.12
    frame_ends = list(range(2, len(episode_dates) + 1, 2))
    if frame_ends[-1] != len(episode_dates):
        frame_ends.append(len(episode_dates))

    output = ASSET_DIR / "from_volatility_to_portfolio_exposure.gif"
    writer = PillowWriter(fps=5)
    with writer.saving(plt.figure(figsize=(10.4, 6.5)), str(output), dpi=92) as _:
        figure = plt.gcf()
        for end_index in frame_ends:
            figure.clear()
            top, bottom = figure.subplots(2, 1, sharex=True, gridspec_kw={"height_ratios": [1, 1.25]})
            current_date = episode_dates[end_index - 1]

            visible_forecast = forecast.filter(pl.col("forecast_for_date") <= current_date)
            top.plot(
                visible_forecast["forecast_for_date"].to_list(),
                visible_forecast["forecast_vol_annualized"].to_list(),
                color="#2563eb",
                lw=2,
                label="EWMA: pronóstico para la sesión",
            )
            top.axhline(0.12, color="#6b7280", lw=1, ls="--", label="Objetivo anual: 12%")
            top.set_ylim(0, fixed_volatility_max)
            top.set_ylabel("Volatilidad anualizada")
            top.yaxis.set_major_formatter(lambda value, _: f"{value:.0%}")
            top.set_title(
                f"COVID-19: señal al cierre → posible ejecución en la siguiente apertura  |  {current_date:%d %b %Y}",
                loc="left",
                fontsize=10.5,
                fontweight="bold",
            )

            bottom.plot(
                episode_dates[:end_index],
                target_weight[:end_index],
                color="#111827",
                lw=1.6,
                ls=":",
                label="Peso objetivo",
            )
            for policy in POLICIES[:3]:
                frame = weights[policy]
                visible = frame.head(end_index)
                bottom.plot(
                    visible["session_date"].to_list(),
                    visible["effective_weight_close"].to_list(),
                    color=COLORS[policy],
                    lw=1.8,
                    label=f"{policy}: peso efectivo",
                )
                trades = visible.filter(pl.col("trade_executed"))
                bottom.scatter(
                    trades["session_date"].to_list(),
                    trades["effective_weight_close"].to_list(),
                    color=COLORS[policy],
                    s=22,
                    marker="o",
                    edgecolor="white",
                    linewidth=0.45,
                    zorder=4,
                )

            for axis in (top, bottom):
                axis.axvline(start, color="#9ca3af", lw=0.8, ls="--")
                axis.axvline(trough, color="#9ca3af", lw=0.8, ls="--")
                axis.set_xlim(start, end)
                apply_editorial_style(axis)
            top.text(start, fixed_volatility_max * 0.94, "Inicio del estrés", color="#4b5563", fontsize=8)
            top.text(trough, fixed_volatility_max * 0.84, "Mínimo de SPY", color="#4b5563", fontsize=8)
            bottom.set_ylim(0, 1.05)
            bottom.set_ylabel("Peso en SPY")
            bottom.yaxis.set_major_formatter(lambda value, _: f"{value:.0%}")
            bottom.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
            bottom.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
            bottom.tick_params(axis="x", labelrotation=0)

            handles, labels = top.get_legend_handles_labels()
            weight_handles, weight_labels = bottom.get_legend_handles_labels()
            unique = dict(zip(handles + weight_handles, labels + weight_labels))
            figure.legend(
                unique.keys(),
                unique.values(),
                loc="lower center",
                ncol=3,
                frameon=False,
                fontsize=8,
                bbox_to_anchor=(0.5, -0.01),
            )
            figure.subplots_adjust(left=0.09, right=0.98, top=0.90, bottom=0.18, hspace=0.12)
            writer.grab_frame(facecolor="white")
    return output


def main() -> None:
    histories, ewma = load_validated_histories()
    tradeoff = build_economic_tradeoff(histories)
    animation = build_volatility_to_exposure_gif(histories, ewma)
    print(f"Generado: {tradeoff}")
    print(f"Generado: {animation}")


if __name__ == "__main__":
    main()
