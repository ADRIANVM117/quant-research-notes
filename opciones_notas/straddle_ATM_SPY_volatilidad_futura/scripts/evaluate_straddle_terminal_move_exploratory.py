"""Frozen one-time exploratory evaluation of straddle vs historical baseline.

Definitions and constants reproduce the dated protocol exactly. This module
does not search variants, alter filters, or claim trading profitability.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = PROJECT_ROOT / "data" / "derived" / "spy_atm30_straddle_with_historical_move_baseline_2020-01-02_2026-08-31.csv"
REPORT_PATH = PROJECT_ROOT / "reports" / "straddle_terminal_move_exploratory_evaluation.md"
DEVELOPMENT_TERMINAL_CUTOFF = pd.Timestamp("2023-12-29")
EVALUATION_START = pd.Timestamp("2024-01-02")
BOOTSTRAP_BLOCK_LENGTH = 30
BOOTSTRAP_REPLICATES = 5_000
BOOTSTRAP_SEED = 20260927


def _fit_linear(x: np.ndarray, y: np.ndarray) -> dict[str, float]:
    design = np.column_stack([np.ones(len(x)), x])
    intercept, slope = np.linalg.lstsq(design, y, rcond=None)[0]
    return {"intercept": float(intercept), "slope": float(slope)}


def _metrics(y: np.ndarray, prediction: np.ndarray) -> dict[str, float]:
    errors = y - prediction
    mse = float(np.mean(errors**2))
    return {
        "mse": mse,
        "rmse": float(np.sqrt(mse)),
        "mae": float(np.mean(np.abs(errors))),
    }


def _block_bootstrap_mse_difference(
    baseline_squared_error: np.ndarray,
    straddle_squared_error: np.ndarray,
) -> tuple[float, float]:
    """Moving-block bootstrap specified in the frozen protocol."""

    n = len(baseline_squared_error)
    if n < BOOTSTRAP_BLOCK_LENGTH:
        raise ValueError(f"Evaluation has {n} rows, fewer than block length {BOOTSTRAP_BLOCK_LENGTH}.")
    generator = np.random.default_rng(BOOTSTRAP_SEED)
    starts = np.arange(n - BOOTSTRAP_BLOCK_LENGTH + 1)
    offsets = np.arange(BOOTSTRAP_BLOCK_LENGTH)
    differences = np.empty(BOOTSTRAP_REPLICATES)
    blocks_needed = int(np.ceil(n / BOOTSTRAP_BLOCK_LENGTH))
    for replicate in range(BOOTSTRAP_REPLICATES):
        sampled_starts = generator.choice(starts, size=blocks_needed, replace=True)
        indices = np.concatenate([start + offsets for start in sampled_starts])[:n]
        differences[replicate] = (
            np.mean(baseline_squared_error[indices]) - np.mean(straddle_squared_error[indices])
        )
    lower, upper = np.quantile(differences, [0.025, 0.975])
    return float(lower), float(upper)


def run_frozen_evaluation() -> dict[str, Any]:
    """Apply frozen development/evaluation separation and report fixed metrics."""

    frame = pd.read_csv(INPUT_PATH, parse_dates=["observation_date", "expiration"])
    required = ["straddle_mid_rel_t", "historical_move_baseline_t", "terminal_move_rel"]
    common = frame.dropna(subset=required).copy().sort_values("observation_date").reset_index(drop=True)
    terminal_complete = common["terminal_followup_complete"].astype(bool)
    development = common.loc[
        terminal_complete & (common["expiration"] <= DEVELOPMENT_TERMINAL_CUTOFF)
    ].copy()
    evaluation = common.loc[
        terminal_complete & (common["observation_date"] >= EVALUATION_START)
    ].copy()
    if development.empty or evaluation.empty:
        raise ValueError("Frozen split has an empty development or evaluation partition.")
    if (development["expiration"] > DEVELOPMENT_TERMINAL_CUTOFF).any():
        raise AssertionError("A terminal result after the development cutoff entered calibration.")

    target_dev = development["terminal_move_rel"].to_numpy(float)
    target_eval = evaluation["terminal_move_rel"].to_numpy(float)
    baseline_model = _fit_linear(development["historical_move_baseline_t"].to_numpy(float), target_dev)
    straddle_model = _fit_linear(development["straddle_mid_rel_t"].to_numpy(float), target_dev)

    baseline_prediction = np.maximum(
        0.0,
        baseline_model["intercept"] + baseline_model["slope"] * evaluation["historical_move_baseline_t"].to_numpy(float),
    )
    straddle_prediction = np.maximum(
        0.0,
        straddle_model["intercept"] + straddle_model["slope"] * evaluation["straddle_mid_rel_t"].to_numpy(float),
    )
    baseline_metrics = _metrics(target_eval, baseline_prediction)
    straddle_metrics = _metrics(target_eval, straddle_prediction)
    difference = baseline_metrics["mse"] - straddle_metrics["mse"]
    ci_lower, ci_upper = _block_bootstrap_mse_difference(
        (target_eval - baseline_prediction) ** 2,
        (target_eval - straddle_prediction) ** 2,
    )
    decision = "INCONCLUSA" if ci_lower <= 0 <= ci_upper else "FAVORECE_STRADDLE" if ci_lower > 0 else "FAVORECE_BASELINE"
    return {
        "development": development,
        "evaluation": evaluation,
        "baseline_model": baseline_model,
        "straddle_model": straddle_model,
        "baseline_metrics": baseline_metrics,
        "straddle_metrics": straddle_metrics,
        "mse_difference_baseline_minus_straddle": difference,
        "mse_difference_ci95": (ci_lower, ci_upper),
        "decision": decision,
        "common_rows": len(common),
        "development_size": len(development),
        "evaluation_size": len(evaluation),
        "development_dates": (development["observation_date"].min(), development["observation_date"].max()),
        "development_terminal_dates": (development["expiration"].min(), development["expiration"].max()),
        "evaluation_dates": (evaluation["observation_date"].min(), evaluation["observation_date"].max()),
        "evaluation_terminal_dates": (evaluation["expiration"].min(), evaluation["expiration"].max()),
    }


def write_report(result: dict[str, Any], path: Path = REPORT_PATH) -> Path:
    """Write the concise, reproducible result report after frozen execution."""

    path.parent.mkdir(parents=True, exist_ok=True)
    baseline, straddle = result["baseline_metrics"], result["straddle_metrics"]
    lower, upper = result["mse_difference_ci95"]
    lines = [
        "# Evaluación exploratoria: costo relativo del straddle vs benchmark histórico",
        "",
        "## Protocolo y particiones",
        "",
        f"- Entrada común: {result['common_rows']:,} filas con los tres valores disponibles.",
        f"- Desarrollo: {result['development_size']:,} observaciones t entre {result['development_dates'][0].date()} y {result['development_dates'][1].date()}; vencimientos entre {result['development_terminal_dates'][0].date()} y {result['development_terminal_dates'][1].date()}, todos ≤ 2023-12-29.",
        f"- Evaluación histórica: {result['evaluation_size']:,} observaciones t entre {result['evaluation_dates'][0].date()} y {result['evaluation_dates'][1].date()}; vencimientos entre {result['evaluation_terminal_dates'][0].date()} y {result['evaluation_terminal_dates'][1].date()}.",
        "- Predicciones truncadas en cero con la misma regla para ambos modelos.",
        "",
        "## Coeficientes de desarrollo",
        "",
        "| Modelo | Intercepto | Pendiente |",
        "|---|---:|---:|",
        f"| Baseline histórico | {result['baseline_model']['intercept']:.8f} | {result['baseline_model']['slope']:.8f} |",
        f"| Straddle | {result['straddle_model']['intercept']:.8f} | {result['straddle_model']['slope']:.8f} |",
        "",
        "## Métricas de evaluación histórica",
        "",
        "| Predictor | MSE | RMSE | MAE |",
        "|---|---:|---:|---:|",
        f"| Baseline histórico | {baseline['mse']:.8f} | {baseline['rmse']:.8f} | {baseline['mae']:.8f} |",
        f"| Straddle | {straddle['mse']:.8f} | {straddle['rmse']:.8f} | {straddle['mae']:.8f} |",
        "",
        f"Diferencia principal `MSE_baseline - MSE_straddle`: **{result['mse_difference_baseline_minus_straddle']:.8f}**.",
        f"IC exploratorio 95% por bootstrap de bloques móviles de 30 fechas (5,000 réplicas; semilla 20260927): **[{lower:.8f}, {upper:.8f}]**.",
        f"Decisión del protocolo: **{result['decision']}**.",
        "",
        "## Límites",
        "",
        "Esta es evaluación histórica exploratoria; 2024–2026 ya era un periodo visto y no es prueba prospectiva intacta. No mide rentabilidad de un straddle, pues SPY tiene opciones americanas y las cotizaciones no demuestran ejecución simultánea. La disponibilidad EOD de la cadena continúa como supuesto no verificado.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


if __name__ == "__main__":
    evaluation_result = run_frozen_evaluation()
    print(write_report(evaluation_result))
