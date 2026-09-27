"""One pre-registered exploratory Spearman/block-bootstrap evaluation; no HMM training."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
INPUT = REPORTS / "hmm_ab_development_frozen_scores_future_vol10_2024_2026.csv"
SEED, REPLICATIONS, BLOCK = 20260927, 5000, 20
PREDICTORS = ["vol20_t", "A_predictive_risk_next", "B_predictive_risk_next"]
OUT_PREFIX = REPORTS / "hmm_ab_future_vol10_spearman_exploratory"


def rho(y: np.ndarray, x: np.ndarray) -> float:
    return float(spearmanr(y, x).statistic)


def moving_block_indices(n: int, block: int, rng: np.random.Generator) -> np.ndarray:
    if n < block:
        raise ValueError(f"n={n} is smaller than fixed block length={block}")
    starts = rng.integers(0, n - block + 1, size=int(np.ceil(n / block)))
    return np.concatenate([np.arange(s, s + block) for s in starts])[:n]


def main():
    raw = pd.read_csv(INPUT, parse_dates=["decision_date", "observation_date"])
    required = ["future_vol10_eligible", "future_vol10", *PREDICTORS]
    missing = [c for c in required if c not in raw]
    if missing:
        raise RuntimeError(f"Missing required columns: {missing}")
    selected = raw.loc[raw.future_vol10_eligible.astype(bool), ["decision_date", "observation_date", "future_vol10", *PREDICTORS]].dropna().sort_values("decision_date").reset_index(drop=True)
    if selected.decision_date.duplicated().any():
        raise RuntimeError("Decision dates must be unique")
    n = len(selected)
    y = selected.future_vol10.to_numpy(float)
    x = {name: selected[name].to_numpy(float) for name in PREDICTORS}
    observed = {name: rho(y, x[name]) for name in PREDICTORS}
    observed_diffs = {"A_minus_vol20": observed["A_predictive_risk_next"] - observed["vol20_t"],
                      "B_minus_A": observed["B_predictive_risk_next"] - observed["A_predictive_risk_next"]}

    rng = np.random.default_rng(SEED)
    draws = np.empty((REPLICATIONS, 2))
    for r in range(REPLICATIONS):
        idx = moving_block_indices(n, BLOCK, rng)
        rb = {name: rho(y[idx], x[name][idx]) for name in PREDICTORS}
        draws[r] = [rb["A_predictive_risk_next"] - rb["vol20_t"], rb["B_predictive_risk_next"] - rb["A_predictive_risk_next"]]
    names = ["A_minus_vol20", "B_minus_A"]
    intervals = {name: {"ci95_low": float(np.quantile(draws[:, i], .025)), "ci95_high": float(np.quantile(draws[:, i], .975))} for i, name in enumerate(names)}
    for name in names:
        intervals[name]["includes_zero"] = bool(intervals[name]["ci95_low"] <= 0 <= intervals[name]["ci95_high"])
        intervals[name]["interpretation"] = "INCONCLUSO respecto a mejora" if intervals[name]["includes_zero"] else "intervalo no incluye cero (exploratorio; no implica utilidad económica)"

    summary_rows = [{"statistic": f"rho_{name}", "value": value} for name, value in observed.items()]
    summary_rows += [{"statistic": name, "value": observed_diffs[name], **intervals[name]} for name in names]
    pd.DataFrame(summary_rows).to_csv(str(OUT_PREFIX) + "_summary.csv", index=False)
    pd.DataFrame({"A_minus_vol20": draws[:, 0], "B_minus_A": draws[:, 1]}).to_csv(str(OUT_PREFIX) + "_bootstrap_draws.csv", index=False)
    metadata = {"input": INPUT.name, "rows_input": int(len(raw)), "rows_selected_common": n,
                "decision_date_start": str(selected.decision_date.min().date()), "decision_date_end": str(selected.decision_date.max().date()),
                "predictors": PREDICTORS, "outcome": "future_vol10", "method": "Spearman; moving block bootstrap without circular wrap",
                "block_length_decisions": BLOCK, "seed": SEED, "replications": REPLICATIONS,
                "correlations": observed, "differences": observed_diffs, "intervals": intervals,
                "historical_status": "exploratory; 2024-2026 already seen; not an intact prospective test"}
    (Path(str(OUT_PREFIX) + "_metadata.json")).write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    report = ["# Evaluación exploratoria — Spearman y volatilidad futura a 10 sesiones", "",
              "Ejercicio histórico exploratorio: 2024–2026 ya fue visto; no es prueba prospectiva intacta.", "",
              f"Muestra común: {n} filas elegibles, {selected.decision_date.min().date()} a {selected.decision_date.max().date()}.",
              f"Bootstrap móvil: bloques de {BLOCK} decisiones, {REPLICATIONS} réplicas, semilla {SEED}.", "",
              "## Correlaciones de Spearman", ""]
    report += [f"- `future_vol10` con `{name}`: {value:.6f}." for name, value in observed.items()]
    report += ["", "## Comparaciones principales", ""]
    report += [f"- `{name}`: {observed_diffs[name]:.6f}; IC exploratorio 95% [{intervals[name]['ci95_low']:.6f}, {intervals[name]['ci95_high']:.6f}]; {intervals[name]['interpretation']}." for name in names]
    report += ["", "No se entrenaron modelos ni se calcularon umbrales, alertas, episodios, rankings o métricas de utilidad económica. Una diferencia de correlación no se interpreta como utilidad económica."]
    (Path(str(OUT_PREFIX) + "_report.md")).write_text("\n".join(report) + "\n", encoding="utf-8")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
