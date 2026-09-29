"""Independent construction audit for the historical-baseline OLS slope.

No model is fitted here. The script verifies lineage and recomputes documented
windows independently, then returns descriptive development-sample summaries.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
HMM_ROOT = PROJECT_ROOT.parents[1] / "HMM_regime_options"
ORIGINAL_TERMINAL_PATH = PROJECT_ROOT / "data" / "derived" / "spy_atm30_straddle_terminal_move_rel_2020-01-02_2026-08-31.csv"
BASELINE_PATH = PROJECT_ROOT / "data" / "derived" / "spy_atm30_straddle_with_historical_move_baseline_2020-01-02_2026-08-31.csv"
PRICE_PATH = HMM_ROOT / "data" / "derived" / "spy_daily_adjusted_2020_2026.csv"
REPORT_PATH = PROJECT_ROOT / "reports" / "historical_baseline_negative_slope_audit.md"
DEVELOPMENT_TERMINAL_CUTOFF = pd.Timestamp("2023-12-29")
WINDOW_COUNT = 252


def _equal_with_na(left: pd.Series, right: pd.Series) -> pd.Series:
    return (left == right) | (left.isna() & right.isna())


def audit_baseline_lineage() -> dict[str, Any]:
    """Verify the frozen baseline implementation without refitting any model."""

    date_columns = ["observation_date", "expiration"]
    original = pd.read_csv(ORIGINAL_TERMINAL_PATH, parse_dates=date_columns).sort_values("series_row_index")
    baseline = pd.read_csv(BASELINE_PATH, parse_dates=date_columns).sort_values("series_row_index")
    prices = pd.read_csv(PRICE_PATH, parse_dates=["date"]).sort_values("date").reset_index(drop=True)
    sessions = prices["date"].to_numpy(dtype="datetime64[ns]")
    closes = prices["close"].to_numpy(float)
    split_coefficients = prices["split_coefficient"].to_numpy(float)
    index_by_date = {pd.Timestamp(session): idx for idx, session in enumerate(sessions)}

    lineage_columns = [
        "series_row_index", "observation_date", "pair_available", "call_contractID", "put_contractID",
        "expiration", "dte", "strike", "spy_close_t", "straddle_mid_rel_t", "terminal_move_rel",
        "terminal_followup_complete",
    ]
    original_indexed = original.set_index("series_row_index")
    baseline_indexed = baseline.set_index("series_row_index")
    missing_ids = sorted(set(original_indexed.index).symmetric_difference(baseline_indexed.index))
    lineage_mismatches: dict[str, int] = {}
    if not missing_ids:
        for column in lineage_columns[1:]:
            lineage_mismatches[column] = int(
                (~_equal_with_na(original_indexed[column], baseline_indexed[column])).sum()
            )
    else:
        lineage_mismatches = {column: -1 for column in lineage_columns[1:]}

    development = baseline.loc[
        baseline["straddle_mid_rel_t"].notna()
        & baseline["historical_move_baseline_t"].notna()
        & baseline["terminal_move_rel"].notna()
        & baseline["terminal_followup_complete"].astype(bool)
        & (baseline["expiration"] <= DEVELOPMENT_TERMINAL_CUTOFF)
    ].copy().sort_values("observation_date").reset_index(drop=True)

    all_row_checks: list[dict[str, Any]] = []
    for row in development.to_dict("records"):
        t = pd.Timestamp(row["observation_date"])
        T = pd.Timestamp(row["expiration"])
        t_index, T_index = index_by_date[t], index_by_date[T]
        H = T_index - t_index
        ends = np.arange(H, t_index + 1, dtype=int)[-WINDOW_COUNT:]
        split_counts = [int(np.count_nonzero(~np.isclose(split_coefficients[end - H:end + 1], 1.0))) for end in ends]
        k = float(row["strike"]) / float(row["spy_close_t"])
        recomputed = float(np.mean(np.abs(closes[ends] / closes[ends - H] - k)))
        all_row_checks.append({
            "series_row_index": int(row["series_row_index"]),
            "h_matches": H == int(row["h_sessions"]),
            "k_matches": np.isclose(k, float(row["k_strike_over_spot_t"]), atol=1e-14),
            "window_count_matches": len(ends) == int(row["historical_window_count"]) == WINDOW_COUNT,
            "last_window_ends_at_or_before_t": int(ends[-1]) <= t_index,
            "first_start_matches": pd.Timestamp(sessions[ends[0] - H]) == pd.Timestamp(row["historical_first_window_start"]),
            "first_end_matches": pd.Timestamp(sessions[ends[0]]) == pd.Timestamp(row["historical_first_window_end"]),
            "last_start_matches": pd.Timestamp(sessions[ends[-1] - H]) == pd.Timestamp(row["historical_last_window_start"]),
            "last_end_matches": pd.Timestamp(sessions[ends[-1]]) == pd.Timestamp(row["historical_last_window_end"]),
            "split_count_matches": sum(count > 0 for count in split_counts) == int(row["historical_split_affected_window_count"]),
            "baseline_matches": np.isclose(recomputed, float(row["historical_move_baseline_t"]), atol=1e-14),
        })
    checks = pd.DataFrame(all_row_checks)

    examples = []
    for label, row_number in zip(("inicio", "mitad", "final"), (0, (len(development) - 1) // 2, len(development) - 1)):
        row = development.iloc[row_number]
        t, T = pd.Timestamp(row["observation_date"]), pd.Timestamp(row["expiration"])
        t_index, T_index = index_by_date[t], index_by_date[T]
        H = T_index - t_index
        ends = np.arange(H, t_index + 1, dtype=int)[-WINDOW_COUNT:]
        k = float(row["strike"]) / float(row["spy_close_t"])
        recomputed = float(np.mean(np.abs(closes[ends] / closes[ends - H] - k)))
        examples.append({
            "example": label,
            "series_row_index": int(row["series_row_index"]),
            "observation_date": t,
            "expiration": T,
            "observation_session_index": t_index,
            "expiration_session_index": T_index,
            "h_sessions_recomputed": H,
            "h_sessions_stored": int(row["h_sessions"]),
            "strike": float(row["strike"]),
            "spy_close_t": float(row["spy_close_t"]),
            "k_recomputed": k,
            "k_stored": float(row["k_strike_over_spot_t"]),
            "first_window_start": pd.Timestamp(sessions[ends[0] - H]),
            "first_window_end": pd.Timestamp(sessions[ends[0]]),
            "last_window_start": pd.Timestamp(sessions[ends[-1] - H]),
            "last_window_end": pd.Timestamp(sessions[ends[-1]]),
            "last_window_end_le_t": pd.Timestamp(sessions[ends[-1]]) <= t,
            "windows_with_split": int(sum(np.count_nonzero(~np.isclose(split_coefficients[end - H:end + 1], 1.0)) > 0 for end in ends)),
            "baseline_recomputed": recomputed,
            "baseline_stored": float(row["historical_move_baseline_t"]),
            "absolute_difference": abs(recomputed - float(row["historical_move_baseline_t"])),
            "terminal_move_rel": float(row["terminal_move_rel"]),
        })
    examples_frame = pd.DataFrame(examples)

    development["year"] = development["observation_date"].dt.year
    descriptive_by_year = development.groupby("year").agg(
        rows=("series_row_index", "size"),
        baseline_mean=("historical_move_baseline_t", "mean"),
        baseline_median=("historical_move_baseline_t", "median"),
        baseline_q25=("historical_move_baseline_t", lambda values: values.quantile(0.25)),
        baseline_q75=("historical_move_baseline_t", lambda values: values.quantile(0.75)),
        terminal_mean=("terminal_move_rel", "mean"),
        terminal_median=("terminal_move_rel", "median"),
        terminal_q25=("terminal_move_rel", lambda values: values.quantile(0.25)),
        terminal_q75=("terminal_move_rel", lambda values: values.quantile(0.75)),
    ).reset_index()

    verification = {
        "development_rows": len(development),
        "lineage_row_id_mismatch_count": len(missing_ids),
        "lineage_field_mismatch_counts": lineage_mismatches,
        "all_h_match": bool(checks["h_matches"].all()),
        "all_k_match": bool(checks["k_matches"].all()),
        "all_252_window_counts_match": bool(checks["window_count_matches"].all()),
        "all_window_dates_match": bool(checks[["first_start_matches", "first_end_matches", "last_start_matches", "last_end_matches"]].all(axis=None)),
        "all_windows_end_by_t": bool(checks["last_window_ends_at_or_before_t"].all()),
        "all_split_counts_match": bool(checks["split_count_matches"].all()),
        "all_baselines_match": bool(checks["baseline_matches"].all()),
        "stored_slope_under_audit": -0.15284988,
    }
    return {
        "development": development,
        "examples": examples_frame,
        "descriptive_by_year": descriptive_by_year,
        "verification": verification,
        "row_checks": checks,
    }


def write_audit_report(result: dict[str, Any], path: Path = REPORT_PATH) -> Path:
    """Persist a concise audit conclusion without altering existing results."""

    verification = result["verification"]
    lineage_ok = verification["lineage_row_id_mismatch_count"] == 0 and all(
        value == 0 for value in verification["lineage_field_mismatch_counts"].values()
    )
    construction_ok = all(verification[key] for key in (
        "all_h_match", "all_k_match", "all_252_window_counts_match", "all_window_dates_match",
        "all_windows_end_by_t", "all_split_counts_match", "all_baselines_match",
    ))
    conclusion = (
        "No se encontró error de construcción bajo la definición documentada; la pendiente negativa publicada es compatible con la relación empírica descriptiva de esta muestra de desarrollo."
        if lineage_ok and construction_ok else
        "Se encontró una discrepancia de linaje o construcción; el resultado publicado queda afectado y requiere revisión separada."
    )
    lines = [
        "# Auditoría de la pendiente negativa del benchmark histórico",
        "",
        f"Filas de desarrollo auditadas: {verification['development_rows']}.",
        f"Pendiente OLS publicada bajo revisión: {verification['stored_slope_under_audit']:.8f}.",
        "",
        "## Verificación de construcción",
        "",
        f"- Linaje de filas: {'correcto' if lineage_ok else 'con discrepancias'}.",
        f"- H, k, 252 ventanas, fechas de ventanas, límites `≤ t`, splits y promedio: {'correctos' if construction_ok else 'con discrepancias'}.",
        f"- {conclusion}",
        "",
        "## Alcance",
        "",
        "No se ajustaron modelos ni se recalculó la evaluación 2024–2026. La dispersión y los resúmenes anuales son diagnósticos descriptivos, no una nueva estimación causal. El supuesto EOD y las limitaciones de opciones americanas permanecen sin cambios.",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
