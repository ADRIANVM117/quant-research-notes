"""Align frozen HMM A/B scores with vol20(t) and realized future 10-session volatility.

No HMM fitting, thresholds, alerts, episodes, correlations, rankings, or performance
statistics are calculated here. Existing artifacts are read only.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REPORTS, DERIVED = ROOT / "reports", ROOT / "data" / "derived"
SCORES = REPORTS / "hmm_ab_development_frozen_scores_2024_2026.csv"
PRICES = DERIVED / "spy_daily_adjusted_2020_2026.csv"
OUT = REPORTS / "hmm_ab_development_frozen_scores_future_vol10_2024_2026.csv"


def return_endpoint_dates(index: pd.DatetimeIndex, decision_loc: int) -> list[str]:
    """Eleven close dates: t, d, and the nine sessions after d; hence ten returns."""
    return [str(day.date()) for day in index[decision_loc - 1:decision_loc + 10]]


def main():
    scores = pd.read_csv(SCORES, parse_dates=["decision_date", "observation_date"])
    prices = pd.read_csv(PRICES, parse_dates=["date"]).sort_values("date").set_index("date")
    close = prices["adjusted_close"].astype(float)
    log_returns = np.log(close).diff()
    # Exact existing definition: sample standard deviation of 20 returns through t.
    vol20 = log_returns.rolling(20, min_periods=20).std(ddof=1)
    calendar = prices.index
    loc = {date: i for i, date in enumerate(calendar)}

    future_vol, eligible, examples = [], [], {}
    for row_number, row in scores.iterrows():
        t, d = row.observation_date, row.decision_date
        if t not in loc or d not in loc:
            raise RuntimeError(f"Score row {row_number} has a date missing from the price calendar")
        d_loc = loc[d]
        if d_loc == 0 or calendar[d_loc - 1] != t:
            raise RuntimeError(f"Score row {row_number} is not consecutive: t={t.date()} d={d.date()}")
        complete = d_loc + 9 < len(calendar)
        eligible.append(complete)
        if complete:
            endpoints = close.iloc[d_loc - 1:d_loc + 10].to_numpy()
            returns = np.diff(np.log(endpoints))
            if len(returns) != 10:
                raise RuntimeError("Expected exactly ten future return observations")
            future_vol.append(float(np.std(returns, ddof=1)))
            if not examples:
                examples["first_eligible"] = {"row": int(row_number), "observation_date": str(t.date()), "decision_date": str(d.date()), "close_endpoint_dates": return_endpoint_dates(calendar, d_loc), "return_endpoint_dates": [str(day.date()) for day in calendar[d_loc:d_loc + 10]], "return_count": 10}
            examples["last_eligible"] = {"row": int(row_number), "observation_date": str(t.date()), "decision_date": str(d.date()), "close_endpoint_dates": return_endpoint_dates(calendar, d_loc), "return_endpoint_dates": [str(day.date()) for day in calendar[d_loc:d_loc + 10]], "return_count": 10}
        else:
            future_vol.append(np.nan)

    out = scores.copy()
    out["vol20_t"] = out["observation_date"].map(vol20)
    out["future_vol10"] = future_vol
    out["future_vol10_eligible"] = eligible
    # Preserve all original 668 rows and their columns, adding alignment fields only.
    if len(out) != len(scores) or not out.iloc[:, :len(scores.columns)].equals(scores):
        raise RuntimeError("Original score rows or columns changed during alignment")
    out.to_csv(OUT, index=False)

    complete = out[out.future_vol10_eligible]
    audit = {
        "input_score_rows": int(len(scores)), "output_rows": int(len(out)),
        "future_vol10_complete": int(len(complete)), "future_vol10_missing": int(out.future_vol10.isna().sum()),
        "last_eligible_decision_date": str(complete.decision_date.max().date()),
        "vol20_definition": "sample standard deviation (ddof=1) of 20 log adjusted-close returns through observation_date t",
        "future_vol10_definition": "sample standard deviation (ddof=1), not annualized, of 10 log adjusted-close returns from t->d through d+8->d+9",
        "examples": examples
    }
    (REPORTS / "hmm_ab_development_frozen_scores_future_vol10_audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    report = f"""# Alineación de scores HMM congelados con volatilidad realizada

Entrada: `{SCORES.name}`. Salida nueva: `{OUT.name}`. Se preservan las {len(out)} filas originales y se añaden `vol20_t`, `future_vol10` y `future_vol10_eligible`.

Seguimiento completo: {len(complete)} fechas; `future_vol10` faltante: {int(out.future_vol10.isna().sum())}; última decisión elegible: {complete.decision_date.max().date()}.

Para cada decisión `d`, los diez retornos son `log(A_d/A_t)`, seguido de los nueve retornos entre sesiones consecutivas desde `d` hasta `d+9`. `future_vol10` usa `ddof=1` y no se anualiza. `vol20_t` usa exactamente la ventana de 20 retornos conocida hasta `t`.

Los índices concretos de la primera y última fila elegibles están en `hmm_ab_development_frozen_scores_future_vol10_audit.json`. No se calcularon correlaciones, rankings, umbrales, alertas, episodios, métricas ni conclusiones sobre A, B o `vol20`.
"""
    (REPORTS / "hmm_ab_development_frozen_scores_future_vol10_report.md").write_text(report, encoding="utf-8")
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
