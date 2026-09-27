"""Generate post-development HMM A/B probabilities with parameters frozen at 2023-12-29.

This script deliberately creates new artifacts only.  It does not calculate thresholds,
alerts, episodes, labels, or performance metrics.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
TARGET_PATH = ROOT / "scripts" / "hmm_exploratory_ab.py"
CUTOFF = pd.Timestamp("2023-12-29")


def load_target():
    spec = importlib.util.spec_from_file_location("hmm_ab_source", TARGET_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules["hmm_ab_source"] = module
    spec.loader.exec_module(module)
    return module


def fit_development_only(source, x_dev: np.ndarray, name: str):
    rows, models = [], {}
    for seed in source.SEEDS:
        model = source.fit_hmm(x_dev, seed)
        rows.append({"model": name, "seed": seed, "loglik_development": model.loglik,
                     "n_iter": model.n_iter, "converged": model.converged})
        models[seed] = model
    table = pd.DataFrame(rows)
    chosen = table.sort_values(["loglik_development", "seed"], ascending=[False, True]).iloc[0]
    return models[int(chosen.seed)], table, int(chosen.seed)


def main():
    source = load_target()
    if source.DEV_END != CUTOFF:
        raise RuntimeError(f"Cutoff mismatch: source={source.DEV_END.date()} requested={CUTOFF.date()}")
    frame = source.load_frame()
    # `scale_inputs` explicitly limits its fit sample to `index <= DEV_END`.
    z, scaler = source.scale_inputs(frame)
    feature_rows = z[["return", "vol20"]].notna().all(axis=1)
    all_dates = frame.index[feature_rows]
    development_mask = all_dates <= CUTOFF
    x_a = z.loc[feature_rows, ["return", "vol20"]].to_numpy()
    x_b = z.loc[feature_rows, ["return", "vol20", "skew"]].to_numpy()
    x_a_dev, x_b_dev = x_a[development_mask], x_b[development_mask]

    model_a, seeds_a, seed_a = fit_development_only(source, x_a_dev, "A")
    model_b, seeds_b, seed_b = fit_development_only(source, x_b_dev, "B")
    risk_a = int(np.argmax(model_a.means[:, 1]))
    risk_b = int(np.argmax(model_b.means[:, 1]))

    # Filter chronological rows from the beginning.  `filtered_predictive` returns
    # alpha[t] and alpha[t] @ transition; B's emission marginalizes missing skew.
    alpha_a, pred_a = source.filtered_predictive(x_a, model_a)
    alpha_b, pred_b = source.filtered_predictive(x_b, model_b)
    work = frame.loc[feature_rows].copy()
    work["A_filtered_risk"] = alpha_a[:, risk_a]
    work["A_predictive_risk_next"] = pred_a[:, risk_a]
    work["B_filtered_risk"] = alpha_b[:, risk_b]
    work["B_predictive_risk_next"] = pred_b[:, risk_b]
    work["B_skew_available"] = work["skew"].notna()
    work["observation_date"] = work.index
    work["decision_date"] = work["next_date"]
    # A score at observation t is usable at decision t+1. The final observation has
    # no known next decision date and is intentionally not exported.
    out = work[work.decision_date.notna()].copy()
    out = out.set_index("decision_date", drop=False)
    out = out[out.index > CUTOFF]
    columns = ["decision_date", "observation_date", "A_filtered_risk", "A_predictive_risk_next",
               "B_filtered_risk", "B_predictive_risk_next", "B_skew_available", "skew",
               "option_status", "quality_flag"]
    out = out[columns]
    if out.B_predictive_risk_next.isna().any():
        raise RuntimeError("B probability missing: marginalization did not preserve a calendar row")

    audit = {
        "artifact": "hmm_ab_development_frozen_scores_2024_2026.csv",
        "purpose": "historical, already-seen 2024-2026 scores; not an intact prospective test",
        "parameter_cutoff": str(CUTOFF.date()),
        "scaler_fit_dates": {"min": str(frame.index[(frame.index <= CUTOFF) & frame["return"].notna() & frame.vol20.notna()].min().date()),
                             "max": str(frame.index[(frame.index <= CUTOFF) & frame["return"].notna() & frame.vol20.notna()].max().date())},
        "model_fit_dates": {"A": {"min": str(all_dates[development_mask].min().date()), "max": str(all_dates[development_mask].max().date())},
                            "B": {"min": str(all_dates[development_mask].min().date()), "max": str(all_dates[development_mask].max().date())}},
        "seed_selection_dates": {"A": {"min": str(all_dates[development_mask].min().date()), "max": str(all_dates[development_mask].max().date())},
                                 "B": {"min": str(all_dates[development_mask].min().date()), "max": str(all_dates[development_mask].max().date())}},
        "selected_seeds": {"A": seed_a, "B": seed_b},
        "risk_state_identified_on_development": {"A": risk_a, "B": risk_b},
        "post_cutoff_input_used_only_for_filtering": {"min_observation_date": str(out.observation_date.min().date()), "max_observation_date": str(out.observation_date.max().date())},
        "output_dates": {"min_decision_date": str(out.decision_date.min().date()), "max_decision_date": str(out.decision_date.max().date()), "rows": int(len(out))},
        "invariants": {"all_scaler_dates_at_or_before_cutoff": True, "all_model_fit_dates_at_or_before_cutoff": True,
                       "all_seed_selection_dates_at_or_before_cutoff": True, "state_identification_at_or_before_cutoff": True,
                       "all_B_probabilities_present": bool(out.B_predictive_risk_next.notna().all())}
    }
    coverage = pd.DataFrame([{
        "decision_date_start": out.decision_date.min().date(), "decision_date_end": out.decision_date.max().date(),
        "rows": len(out), "A_probability_available": int(out.A_predictive_risk_next.notna().sum()),
        "B_probability_available": int(out.B_predictive_risk_next.notna().sum()),
        "B_skew_available": int(out.B_skew_available.sum()), "B_skew_missing": int((~out.B_skew_available).sum()),
        "quality_flagged": int(out.quality_flag.sum())
    }])
    out.to_csv(REPORTS / "hmm_ab_development_frozen_scores_2024_2026.csv", index=False)
    pd.concat([seeds_a, seeds_b]).to_csv(REPORTS / "hmm_ab_development_frozen_seed_convergence.csv", index=False)
    scaler.to_csv(REPORTS / "hmm_ab_development_frozen_scaler.csv", index=False)
    coverage.to_csv(REPORTS / "hmm_ab_development_frozen_coverage.csv", index=False)
    (REPORTS / "hmm_ab_development_frozen_fit_audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    report = f"""# HMM A/B — scores congelados a desarrollo

Archivo nuevo: `hmm_ab_development_frozen_scores_2024_2026.csv`. No es `hmm_ab_daily.csv`: este último conserva scores del reajuste completo exploratorio.

Parámetros, escalamiento, selección de semilla e identificación del estado se limitaron a observaciones hasta {CUTOFF.date()}. Los datos posteriores se usaron únicamente para filtrar con parámetros fijos.

Cobertura de decisión: {out.decision_date.min().date()} a {out.decision_date.max().date()}, {len(out)} filas. B conserva probabilidad cuando skew falta; la disponibilidad se reporta en `B_skew_available`.

No se calcularon P90, alertas, episodios, etiquetas, métricas ni resultado a diez sesiones. 2024–2026 es evaluación histórica ya vista, no prueba prospectiva intacta.

La comprobación fechada está en `hmm_ab_development_frozen_fit_audit.json`.
"""
    (REPORTS / "hmm_ab_development_frozen_report.md").write_text(report, encoding="utf-8")
    print(json.dumps({"output": str(REPORTS / "hmm_ab_development_frozen_scores_2024_2026.csv"), "coverage": coverage.iloc[0].to_dict(), "audit": audit}, indent=2, default=str))


if __name__ == "__main__":
    main()
