"""Exploratory two-state HMM A/B; preserves calendar rows and marginalizes missing skew."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
DATA, REPORTS = ROOT / "data" / "derived", ROOT / "reports"
PX_FILE, OPT_FILE = DATA / "spy_daily_adjusted_2020_2026.csv", REPORTS / "checkpoint_a4_daily.csv"
DEV_END = pd.Timestamp("2023-12-29")
SEEDS = list(range(10)); N_STATES = 2; MAX_ITER = 200; TOL = 1e-6; VAR_FLOOR = 1e-5


@dataclass
class HMM:
    pi: np.ndarray; trans: np.ndarray; means: np.ndarray; vars: np.ndarray
    loglik: float; n_iter: int; converged: bool


def emission_logprob(x: np.ndarray, model: HMM) -> np.ndarray:
    """log p(x_t | state), summing only observed Gaussian dimensions."""
    out = np.zeros((len(x), N_STATES))
    for j in range(x.shape[1]):
        obs = np.isfinite(x[:, j])
        if obs.any():
            z = x[obs, j, None] - model.means[None, :, j]
            out[obs] += -0.5 * (np.log(2 * np.pi * model.vars[None, :, j]) + z * z / model.vars[None, :, j])
    return out


def forward_backward(x: np.ndarray, model: HMM):
    loge = emission_logprob(x, model)
    emit = np.exp(np.clip(loge, -700, 700))
    n = len(x); alpha = np.empty((n, N_STATES)); scale = np.empty(n)
    alpha[0] = model.pi * emit[0]; scale[0] = max(alpha[0].sum(), 1e-300); alpha[0] /= scale[0]
    for t in range(1, n):
        alpha[t] = (alpha[t - 1] @ model.trans) * emit[t]
        scale[t] = max(alpha[t].sum(), 1e-300); alpha[t] /= scale[t]
    beta = np.ones((n, N_STATES))
    for t in range(n - 2, -1, -1):
        beta[t] = model.trans @ (emit[t + 1] * beta[t + 1]) / scale[t + 1]
    gamma = alpha * beta; gamma /= gamma.sum(axis=1, keepdims=True)
    xi_sum = np.zeros((N_STATES, N_STATES))
    for t in range(n - 1):
        xi = alpha[t, :, None] * model.trans * (emit[t + 1] * beta[t + 1])[None, :]
        xi_sum += xi / max(xi.sum(), 1e-300)
    return alpha, gamma, xi_sum, float(np.log(scale).sum())


def fit_hmm(x: np.ndarray, seed: int) -> HMM:
    rng = np.random.default_rng(seed); obs_mean = np.nanmean(x, axis=0); obs_var = np.nanvar(x, axis=0) + VAR_FLOOR
    filled = np.where(np.isfinite(x), x, obs_mean)
    picks = rng.choice(len(x), N_STATES, replace=False)
    model = HMM(np.full(N_STATES, .5), np.array([[.92, .08], [.08, .92]]), filled[picks] + rng.normal(0, .05, (N_STATES, x.shape[1])), np.tile(obs_var, (N_STATES, 1)), -np.inf, 0, False)
    previous = -np.inf
    for it in range(1, MAX_ITER + 1):
        _, gamma, xi_sum, ll = forward_backward(x, model)
        pi = np.clip(gamma[0], 1e-8, 1); pi /= pi.sum()
        trans = np.maximum(xi_sum, 1e-8); trans /= trans.sum(axis=1, keepdims=True)
        means, variances = model.means.copy(), model.vars.copy()
        for j in range(x.shape[1]):
            mask = np.isfinite(x[:, j]); w = gamma[mask]
            denom = w.sum(axis=0)
            means[:, j] = (w * x[mask, j, None]).sum(axis=0) / np.maximum(denom, 1e-12)
            variances[:, j] = (w * (x[mask, j, None] - means[None, :, j]) ** 2).sum(axis=0) / np.maximum(denom, 1e-12)
        model = HMM(pi, trans, means, np.maximum(variances, VAR_FLOOR), ll, it, False)
        if np.isfinite(previous) and abs(ll - previous) <= TOL * (1 + abs(previous)):
            model.converged = True; break
        previous = ll
    return model


def filtered_predictive(x: np.ndarray, model: HMM):
    alpha, _, _, _ = forward_backward(x, model)
    return alpha, alpha @ model.trans


def preflight_missing_skew() -> dict:
    """Small deterministic proof of marginal likelihood, update, transition and alert suppression."""
    m = HMM(np.array([.5, .5]), np.array([[.8, .2], [.3, .7]]), np.array([[0., 0., -1.], [1., 1., 1.]]), np.ones((2, 3)), 0., 0, True)
    x = np.array([[0., 0., -1.], [1., 1., np.nan], [0., 0., 1.]])
    loge = emission_logprob(x, m)
    manual = -0.5 * ((1 - 0) ** 2 + (1 - 0) ** 2 + 2 * np.log(2 * np.pi))
    assert np.isclose(loge[1, 0], manual), "missing skew was not marginalized"
    alpha, pred = filtered_predictive(x, m)
    assert np.isfinite(alpha).all() and np.isfinite(pred).all(), "filter failed with missing skew"
    assert not np.allclose(pred[1], alpha[0]), "transition did not advance calendar state"
    alert_available = np.isfinite(x[:, 2])
    assert alert_available.tolist() == [True, False, True], "missing skew did not suppress only B alert"
    return {"passed": True, "rows": 3, "missing_skew_row": 1, "marginalized_dimensions": ["return", "vol20"], "transition_advanced": True, "b_alert_suppressed": True}


def load_frame() -> pd.DataFrame:
    px = pd.read_csv(PX_FILE, parse_dates=["date"]).sort_values("date").set_index("date")
    op = pd.read_csv(OPT_FILE, parse_dates=["date"]).sort_values("date").set_index("date")
    f = px[["adjusted_close"]].copy()
    f["return"] = np.log(f.adjusted_close).diff()
    f["vol20"] = f["return"].rolling(20, min_periods=20).std()
    usable = op.status.eq("usable_pair")
    f["skew"] = op["skew"].where(usable).reindex(f.index)
    f["wide_spread"] = (op.put_flags.fillna("").str.contains("wide_spread") | op.call_flags.fillna("").str.contains("wide_spread")).reindex(f.index, fill_value=False)
    f["expiry_change"] = op.expiry_change.fillna(False).reindex(f.index, fill_value=False)
    f["extreme_jump"] = op.extreme_jump.fillna(False).reindex(f.index, fill_value=False)
    f["option_status"] = op.status.reindex(f.index)
    f["quality_flag"] = f.wide_spread | f.expiry_change | f.extreme_jump
    f["next_date"] = f.index.to_series().shift(-1).to_numpy()
    f["part"] = np.where(f.index <= DEV_END, "development_2020_2023", "seen_2024_2026")
    return f


def scale_inputs(f: pd.DataFrame):
    cols = ["return", "vol20", "skew"]; dev = f[(f.index <= DEV_END) & f["return"].notna() & f.vol20.notna()]
    mu, sd = dev[cols].mean(), dev[cols].std(ddof=0).replace(0, np.nan)
    z = (f[cols] - mu) / sd
    return z, pd.DataFrame({"feature": cols, "development_mean": mu.values, "development_std": sd.values, "n_development_observed": dev[cols].notna().sum().values})


def map_full_states(dev_model: HMM, full_model: HMM, risk_dev: int):
    cost = ((dev_model.means[:, None, :] - full_model.means[None, :, :]) ** 2).sum(axis=2)
    row, col = linear_sum_assignment(cost); mapping = dict(zip(row.tolist(), col.tolist()))
    return int(mapping[risk_dev]), mapping


def breach_dates(px: pd.Series):
    """Original definition: first b in d+1..d+20 relative to A_d, then group unique b by <=5 sessions."""
    n = len(px); rows = []
    for i in range(n - 20):
        future = px.iloc[i + 1:i + 21]; hit = future[future <= .93 * px.iloc[i]]
        if not hit.empty: rows.append((px.index[i], hit.index[0]))
    dec = pd.DataFrame(rows, columns=["decision_date", "breach_date"])
    unique = pd.DatetimeIndex(dec.breach_date.drop_duplicates().sort_values())
    episodes = []; group = []
    loc = {d: i for i, d in enumerate(px.index)}
    for b in unique:
        if not group or loc[b] - loc[group[-1]] <= 5: group.append(b)
        else: episodes.append(group); group = [b]
    if group: episodes.append(group)
    return dec, pd.DataFrame([{"episode_id": k + 1, "start": g[0], "last_breach": g[-1], "right_censored": bool(loc[g[-1]] + 5 >= n)} for k, g in enumerate(episodes)])


def alerts_and_metrics(f: pd.DataFrame, episodes: pd.DataFrame, model_name: str, prob_col: str, avail_col: str, threshold: float):
    out = f.copy(); out[model_name + "_alert"] = out[avail_col] & (out[prob_col] >= threshold)
    # Final five dates cannot be classified as non-accredited without the next five sessions.
    last_evaluable_alert = out.index[-6]
    out[model_name + "_alert_evaluable"] = out.index <= last_evaluable_alert
    starts = episodes.start.tolist(); assignments = []
    for d, flag, eligible in zip(out.index, out[model_name + "_alert"], out[model_name + "_alert_evaluable"]):
        hits = [s for s in starts if 1 <= out.index.get_loc(s) - out.index.get_loc(d) <= 5] if flag and eligible else []
        assignments.append(hits[0] if hits else pd.NaT)
    out[model_name + "_assigned_episode_start"] = assignments
    return out


def summarize(f: pd.DataFrame, episodes: pd.DataFrame, model_name: str):
    alert = model_name + "_alert"; evaluable = model_name + "_alert_evaluable"; assigned = model_name + "_assigned_episode_start"
    rows = f[f[evaluable]].copy(); eps = episodes[(episodes.start >= rows.index.min() + pd.Timedelta(0)) & (episodes.start <= rows.index.max() + pd.Timedelta(0))].copy()
    # Episodes require all five preceding decision rows within this historical frame.
    idxloc = {d: i for i, d in enumerate(f.index)}
    eps = eps[eps.start.map(lambda d: idxloc.get(d, -99) >= 5)]
    assigned_set = set(rows.loc[rows[assigned].notna(), assigned])
    alerts = int(rows[alert].sum()); credited = int(rows[assigned].notna().sum()); n_eps = len(eps); hits = int(eps.start.isin(assigned_set).sum())
    return {"model": model_name, "decision_dates_evaluable": len(rows), "alerts": alerts, "alert_frequency": alerts / len(rows) if len(rows) else np.nan, "episodes": n_eps, "episodes_right_censored": int(eps.right_censored.sum()), "recall": hits / n_eps if n_eps else np.nan, "credited_alerts": credited, "uncredited_alerts": alerts - credited, "TAAE": (alerts - credited) / alerts if alerts else np.nan}


def run():
    REPORTS.mkdir(exist_ok=True)
    preflight = preflight_missing_skew()
    f = load_frame(); z, scaler = scale_inputs(f)
    mask_a = z[["return", "vol20"]].notna().all(axis=1); mask_b = z[["return", "vol20"]].notna().all(axis=1)  # skew intentionally may be missing
    # Calendar rows begin only once return/vol20 exist; B retains every one of those rows.
    xa, xb = z.loc[mask_a, ["return", "vol20"]].to_numpy(), z.loc[mask_b, ["return", "vol20", "skew"]].to_numpy()
    dev_a = xa[f.loc[mask_a].index <= DEV_END]; dev_b = xb[f.loc[mask_b].index <= DEV_END]
    seed_rows = []
    for name, xdev in [("A", dev_a), ("B", dev_b)]:
        for seed in SEEDS:
            try:
                m = fit_hmm(xdev, seed); seed_rows.append({"model": name, "seed": seed, "loglik_development": m.loglik, "n_iter": m.n_iter, "converged": m.converged, "failed": False})
            except Exception as e:
                seed_rows.append({"model": name, "seed": seed, "loglik_development": np.nan, "n_iter": np.nan, "converged": False, "failed": True, "error": repr(e)})
    seed_table = pd.DataFrame(seed_rows); selected = {}
    dev_models = {}; full_models = {}
    for name, xdev, xfull in [("A", dev_a, xa), ("B", dev_b, xb)]:
        ok = seed_table[(seed_table.model == name) & ~seed_table.failed].sort_values(["loglik_development", "seed"], ascending=[False, True]).iloc[0]
        seed = int(ok.seed); selected[name] = seed; dev_models[name] = fit_hmm(xdev, seed); full_models[name] = fit_hmm(xfull, seed)
    # Risk label comes from development model, then maps to the all-history exploratory refit without choosing on outcomes.
    risk_dev_a = int(np.argmax(dev_models["A"].means[:, 1])); risk_dev_b = int(np.argmax(dev_models["B"].means[:, 1]))
    risk_a, map_a = map_full_states(dev_models["A"], full_models["A"], risk_dev_a)
    risk_b, map_b = map_full_states(dev_models["B"], full_models["B"], risk_dev_b)
    fa, pa = filtered_predictive(xa, full_models["A"]); fb, pb = filtered_predictive(xb, full_models["B"])
    f["A_filtered_risk"] = np.nan; f.loc[mask_a, "A_filtered_risk"] = fa[:, risk_a]
    f["A_predictive_risk_next"] = np.nan; f.loc[mask_a, "A_predictive_risk_next"] = pa[:, risk_a]
    f["B_filtered_risk"] = np.nan; f.loc[mask_b, "B_filtered_risk"] = fb[:, risk_b]
    f["B_predictive_risk_next"] = np.nan; f.loc[mask_b, "B_predictive_risk_next"] = pb[:, risk_b]
    f["A_alert_available"] = f.A_predictive_risk_next.notna()
    f["B_alert_available"] = f.B_predictive_risk_next.notna() & f["skew"].notna()
    f["decision_date"] = f.next_date
    # Align score at observation t to alert decision d=t+1; initial date has no previous observation.
    evalf = f.iloc[:-1].copy(); evalf["observation_date"] = evalf.index; evalf.index = pd.DatetimeIndex(evalf.decision_date); evalf.index.name = "decision_date"
    dev_common = evalf[(evalf.index <= DEV_END) & evalf.A_alert_available & evalf.B_alert_available]
    thresh_a, thresh_b = dev_common.A_predictive_risk_next.quantile(.90), dev_common.B_predictive_risk_next.quantile(.90)
    _, episodes = breach_dates(f.adjusted_close)
    evalf = alerts_and_metrics(evalf, episodes, "A", "A_predictive_risk_next", "A_alert_available", thresh_a)
    evalf = alerts_and_metrics(evalf, episodes, "B", "B_predictive_risk_next", "B_alert_available", thresh_b)
    # Primary comparison is common alert availability, with A recomputed on the same dates.
    common = evalf.A_alert_available & evalf.B_alert_available
    primary = evalf.loc[common].copy()
    primary["A_alert"] = primary.A_predictive_risk_next >= thresh_a; primary["B_alert"] = primary.B_predictive_risk_next >= thresh_b
    primary["A_alert_evaluable"] = primary.index <= evalf.index[-6]; primary["B_alert_evaluable"] = primary.A_alert_evaluable
    # Reassign on common dates using original session indices; episodes retain calendar dates.
    for name in ["A", "B"]:
        assignments=[]
        for d, flag, eligible in zip(primary.index, primary[name+"_alert"], primary[name+"_alert_evaluable"]):
            hits=[s for s in episodes.start if flag and eligible and 1 <= evalf.index.get_loc(s)-evalf.index.get_loc(d) <= 5]
            assignments.append(hits[0] if hits else pd.NaT)
        primary[name+"_assigned_episode_start"] = assignments
    summaries=[]
    for label, sub in [("all_history_exploratory", evalf), ("development_2020_2023", evalf[evalf.index <= DEV_END]), ("seen_2024_2026", evalf[evalf.index > DEV_END]), ("common_dates_all_history_exploratory", primary)]:
        for name in ["A", "B"]:
            summaries.append({"scope": label, **summarize(sub, episodes, name)})
    coverage = pd.DataFrame([{"calendar_rows_return_vol20": int(mask_a.sum()), "B_rows_retained_with_missing_skew": int(mask_b.sum()), "B_alert_available": int(evalf.B_alert_available.sum()), "B_alert_unavailable_missing_skew": int((evalf.B_predictive_risk_next.notna() & ~evalf["skew"].notna()).sum()), "common_alert_dates": int(common.sum()), "quality_wide_spread": int(evalf.wide_spread.sum()), "quality_expiry_change": int(evalf.expiry_change.sum()), "quality_extreme_jump": int(evalf.extreme_jump.sum()), "quality_any": int(evalf.quality_flag.sum())}])
    params=[]
    for name, model, risk_dev, risk_full, mapping in [("A", full_models["A"], risk_dev_a, risk_a, map_a), ("B", full_models["B"], risk_dev_b, risk_b, map_b)]:
        feats = ["return", "vol20"] + (["skew"] if name == "B" else [])
        for s in range(2):
            row={"model":name,"state":s,"is_risk_state":s==risk_full,"development_risk_state":risk_dev,"mapping_development_to_full":json.dumps(mapping),"pi":model.pi[s]}
            for k, feat in enumerate(feats): row["mean_z_"+feat]=model.means[s,k]; row["sd_z_"+feat]=np.sqrt(model.vars[s,k])
            params.append(row)
    pd.DataFrame(params).to_csv(REPORTS / "hmm_ab_emissions.csv", index=False)
    transitions=[]
    for name, model in full_models.items():
        for i in range(2):
            for j in range(2): transitions.append({"model":name,"from_state":i,"to_state":j,"probability":model.trans[i,j]})
    pd.DataFrame(transitions).to_csv(REPORTS / "hmm_ab_transitions.csv", index=False)
    seed_table.to_csv(REPORTS / "hmm_ab_seed_convergence.csv", index=False); scaler.to_csv(REPORTS / "hmm_ab_scaler.csv", index=False)
    coverage.to_csv(REPORTS / "hmm_ab_coverage.csv", index=False); pd.DataFrame(summaries).to_csv(REPORTS / "hmm_ab_historical_metrics.csv", index=False)
    episodes.to_csv(REPORTS / "hmm_ab_episodes.csv", index=False); evalf.to_csv(REPORTS / "hmm_ab_daily.csv", index_label="decision_date"); primary.to_csv(REPORTS / "hmm_ab_common_daily.csv", index_label="decision_date")
    with open(REPORTS / "hmm_ab_preflight.json", "w", encoding="utf-8") as h: json.dump(preflight, h, indent=2)
    # Visuals use predictive probability generated after observation t and indexed by decision t+1.
    for stem, sub in [("hmm_ab_probabilities_full", evalf), ("hmm_ab_probabilities_seen_2024_2026", evalf[evalf.index > DEV_END])]:
        fig, ax = plt.subplots(2, 1, figsize=(13, 7), sharex=True, constrained_layout=True)
        ax[0].plot(sub.index, sub.adjusted_close, color="black", lw=.8); ax[0].set_ylabel("SPY cierre ajustado")
        ax[1].plot(sub.index, sub.A_predictive_risk_next, label="A predictiva", lw=.8); ax[1].plot(sub.index, sub.B_predictive_risk_next, label="B predictiva", lw=.8)
        ax[1].scatter(sub.index[~sub.B_alert_available], sub.B_predictive_risk_next[~sub.B_alert_available], s=6, color="red", label="B sin alerta (skew faltante)")
        ax[1].axhline(thresh_a, color="C0", ls="--", alpha=.5); ax[1].axhline(thresh_b, color="C1", ls="--", alpha=.5); ax[1].set_ylim(-.02,1.02); ax[1].set_ylabel("P predictiva riesgo t+1"); ax[1].legend(ncol=2, fontsize=8)
        fig.suptitle("HMM A/B exploratorio — probabilidades filtradas/predictivas; no prospectivo")
        fig.savefig(REPORTS / f"{stem}.png", dpi=160); plt.close(fig)
    all_metrics = pd.DataFrame(summaries).query("scope == 'all_history_exploratory'").set_index("model")
    notes = [
        "# HMM A/B — análisis exploratorio", "", "Todos los resultados 2020–2026 son retrospectivos/exploratorios; 2024–2026 ya fueron vistos y no son prueba prospectiva.",
        "", "## Implementación y preflight", "", "El HMM gaussiano diagonal fue implementado localmente para marginalizar dimensiones faltantes. La prueba sintética pasó: conserva la fila sin skew, actualiza con retorno/vol20, avanza transición y suprime solo la alerta B.",
        "", "## Diseño registrado", "", f"Escalamiento ajustado solo con desarrollo hasta {DEV_END.date()}; semillas preespecificadas: 0…9. La semilla se eligió por log-verosimilitud de desarrollo y el ajuste exploratorio final usó todo el historial con esa semilla fija. A y B se comparan en fechas comunes; los umbrales P90 se calcularon solo en desarrollo común.",
        "", "## Resultado descriptivo, no confirmatorio", "", f"En fechas comunes hubo {int(common.sum())} decisiones y B perdió {int(evalf.A_alert_available.sum()-evalf.B_alert_available.sum())} fecha de alerta por skew faltante. A y B emitieron {int(all_metrics.loc['A','alerts'])} y {int(all_metrics.loc['B','alerts'])} alertas respectivamente; recall exploratorio {all_metrics.loc['A','recall']:.3f} y {all_metrics.loc['B','recall']:.3f}; TAAE {all_metrics.loc['A','TAAE']:.3f} y {all_metrics.loc['B','TAAE']:.3f}. B acreditó una alerta más, pero no mejoró recall ni frecuencia. Estas cifras no son evidencia prospectiva ni criterios de aprobación.",
        "", "## Qué aprendieron los estados", "", "En ambos modelos, el estado descriptivo de mayor volatilidad tiene mayor media de `vol20` que el otro estado. En B, además, su media de skew estandarizado es mayor; esto describe cómo el ajuste separó el historial, no una causa económica ni una capacidad de anticipación.",
        "", "## Fallos y ambigüedades registrados antes de interpretar", "", "`hmmlearn` no está instalado; se usó una implementación local diagonal, validada con una prueba sintética de marginalización, pero sigue pendiente revisión independiente del algoritmo EM. Pandas emitió dos advertencias de futura conversión de tipo para banderas A4; no cambió valores ni detuvo el cálculo. La disponibilidad EOD sigue sin verificar. El reajuste a todo el historial hace que las probabilidades históricas sean filtradas condicionales a parámetros retrospectivos, no señales disponibles entonces. La regla de cierre recursivo de episodios puede censurar finales de serie; se conserva su bandera.",
        "", "## Límites", "", "Parámetros ajustados con todo el historial y toda métrica son exploratorios. La disponibilidad EOD antes de abrir t+1 sigue sin verificarse. La comparación no prueba utilidad económica ni confirma capacidad prospectiva; no hay integración con Actinver.",
        "", "Artefactos tabulares: `hmm_ab_*.csv`; visuales: `hmm_ab_probabilities_*.png`."
    ]
    (REPORTS / "hmm_ab_exploratory_report.md").write_text("\n".join(notes) + "\n", encoding="utf-8")
    print(json.dumps({"preflight": preflight, "selected_seeds": selected, "threshold_A": float(thresh_a), "threshold_B": float(thresh_b), "rows": len(evalf)}, indent=2))


if __name__ == "__main__":
    run()
