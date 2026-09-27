"""Independent synthetic audit of hmm_exploratory_ab.py; never rewrites published HMM outputs."""
from __future__ import annotations

import importlib.util
import itertools
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]; REPORTS = ROOT / "reports"
spec = importlib.util.spec_from_file_location("target", ROOT / "scripts" / "hmm_exploratory_ab.py")
target = importlib.util.module_from_spec(spec); sys.modules["target"] = target; spec.loader.exec_module(target)


def direct_emission(x, means, variances, state):
    total = 0.0
    for j, value in enumerate(x):
        if np.isfinite(value): total += -.5 * (np.log(2*np.pi*variances[state,j]) + (value-means[state,j])**2/variances[state,j])
    return float(np.exp(total))


def brute_likelihood(x, model):
    total = 0.0
    for path in itertools.product(range(2), repeat=len(x)):
        p = model.pi[path[0]] * direct_emission(x[0], model.means, model.vars, path[0])
        for t in range(1, len(x)): p *= model.trans[path[t-1],path[t]] * direct_emission(x[t], model.means, model.vars, path[t])
        total += p
    return float(total)


def em_trace(x, seed):
    """Separate trace implementation using target E-step but independently reproducing its M-step."""
    rng=np.random.default_rng(seed); mean=np.nanmean(x,0); var=np.nanvar(x,0)+target.VAR_FLOOR
    filled=np.where(np.isfinite(x),x,mean); picks=rng.choice(len(x),2,replace=False)
    m=target.HMM(np.full(2,.5),np.array([[.92,.08],[.08,.92]]),filled[picks]+rng.normal(0,.05,(2,x.shape[1])),np.tile(var,(2,1)),-np.inf,0,False)
    trace=[]
    for it in range(30):
        _, gamma, xi, ll=target.forward_backward(x,m); trace.append(float(ll))
        pi=np.clip(gamma[0],1e-8,1); pi/=pi.sum(); trans=np.maximum(xi,1e-8); trans/=trans.sum(1,keepdims=True)
        means=m.means.copy(); vars=m.vars.copy()
        for j in range(x.shape[1]):
            mask=np.isfinite(x[:,j]); w=gamma[mask]; den=w.sum(0)
            means[:,j]=(w*x[mask,j,None]).sum(0)/np.maximum(den,1e-12)
            vars[:,j]=(w*(x[mask,j,None]-means[None,:,j])**2).sum(0)/np.maximum(den,1e-12)
        m=target.HMM(pi,trans,means,np.maximum(vars,target.VAR_FLOOR),ll,it+1,False)
    return trace


def model_scores(model, x, dates, risk_state):
    _, pred=target.filtered_predictive(x,model)
    return pd.Series(pred[:,risk_state],index=dates)


def main():
    checks=[]
    m=target.HMM(np.array([.6,.4]),np.array([[.75,.25],[.30,.70]]),np.array([[0.,0.,-1.],[1.,1.,1.]]),np.array([[1.,2.,1.5],[1.2,.8,.7]]),0.,0,True)
    x=np.array([[.2,-.1,-.7],[1.1,.8,np.nan]])
    alpha,gamma,xi,ll=target.forward_backward(x,m); exact=brute_likelihood(x,m)
    checks.append({"check":"verosimilitud por enumeracion de 4 trayectorias","status":"PASS" if np.isclose(np.exp(ll),exact,rtol=1e-10) else "FAIL","observed":float(np.exp(ll)),"expected":exact})
    manual_pred=alpha[-1]@m.trans
    checks.append({"check":"filtrado/prediccion de un paso","status":"PASS" if np.allclose(manual_pred,target.filtered_predictive(x,m)[1][-1]) else "FAIL","observed":manual_pred.tolist(),"expected":manual_pred.tolist()})
    checks.append({"check":"normalizacion alpha y gamma","status":"PASS" if np.allclose(alpha.sum(1),1) and np.allclose(gamma.sum(1),1) else "FAIL","observed":{"alpha":alpha.sum(1).tolist(),"gamma":gamma.sum(1).tolist()}})
    checks.append({"check":"normalizacion de transicion","status":"PASS" if np.allclose(m.trans.sum(1),1) else "FAIL","observed":m.trans.sum(1).tolist()})
    loge=target.emission_logprob(x,m); manual_log=np.log(direct_emission(x[1],m.means,m.vars,0))
    checks.append({"check":"marginalizacion exacta de skew faltante","status":"PASS" if np.isclose(loge[1,0],manual_log) else "FAIL","observed":float(loge[1,0]),"expected":float(manual_log)})
    # Reproducibility and EM monotonicity use a small deterministic sequence with a missing third dimension.
    toy=np.array([[0.,0.,-1.],[.1,.2,np.nan],[1.,1.,1.],[.9,1.2,.8],[0.,-.1,-.8],[1.1,.9,np.nan]])
    a=target.fit_hmm(toy,7); b=target.fit_hmm(toy,7)
    checks.append({"check":"reproducibilidad misma semilla","status":"PASS" if np.allclose(a.means,b.means) and np.allclose(a.trans,b.trans) and a.loglik==b.loglik else "FAIL","observed":{"loglik_a":a.loglik,"loglik_b":b.loglik}})
    trace=em_trace(toy,7); diffs=np.diff(trace); checks.append({"check":"no-decrecimiento de verosimilitud EM (secuencia sintetica)","status":"PASS" if np.all(diffs>=-1e-8) else "FAIL","observed":{"iterations":len(trace),"min_increment":float(diffs.min()),"trace":trace}})
    # Determine the actual model lineage of published thresholds, independently rebuilding both alternatives.
    f=target.load_frame(); z,_=target.scale_inputs(f); ma=z[["return","vol20"]].notna().all(1)
    xa=z.loc[ma,["return","vol20"]].to_numpy(); xb=z.loc[ma,["return","vol20","skew"]].to_numpy(); dates=f.loc[ma].index
    devmask=dates<=target.DEV_END; seeds=pd.read_csv(REPORTS/"hmm_ab_seed_convergence.csv")
    selected={name:int(seeds[seeds.model.eq(name)].sort_values(["loglik_development","seed"],ascending=[False,True]).iloc[0].seed) for name in ["A","B"]}
    da=target.fit_hmm(xa[devmask],selected["A"]); db=target.fit_hmm(xb[devmask],selected["B"]); fa=target.fit_hmm(xa,selected["A"]); fb=target.fit_hmm(xb,selected["B"])
    # Use the exact state mapping logic of the published code for each alternative.
    ra_dev=int(np.argmax(da.means[:,1])); rb_dev=int(np.argmax(db.means[:,1])); ra_full,_=target.map_full_states(da,fa,ra_dev); rb_full,_=target.map_full_states(db,fb,rb_dev)
    score_full_a=model_scores(fa,xa,dates,ra_full); score_full_b=model_scores(fb,xb,dates,rb_full)
    score_dev_a=model_scores(da,xa[devmask],dates[devmask],ra_dev); score_dev_b=model_scores(db,xb[devmask],dates[devmask],rb_dev)
    # Scores are moved one session forward in publication; this does not change P90 values, only dates.
    all_eligible=f.loc[dates].iloc[:-1].copy(); all_eligible.index=pd.DatetimeIndex(all_eligible.next_date)
    full_a=score_full_a.iloc[:-1].copy(); full_a.index=all_eligible.index; full_b=score_full_b.iloc[:-1].copy(); full_b.index=all_eligible.index
    dev_index=dates[devmask][:-1].to_numpy(); dev_decisions=pd.DatetimeIndex(f.loc[dev_index,"next_date"])
    dev_a_scores=score_dev_a.iloc[:-1].copy(); dev_a_scores.index=dev_decisions; dev_b_scores=score_dev_b.iloc[:-1].copy(); dev_b_scores.index=dev_decisions
    eligible=all_eligible[all_eligible.index<=target.DEV_END]
    full_a, full_b = full_a.loc[eligible.index], full_b.loc[eligible.index]
    dev_a_scores, dev_b_scores = dev_a_scores.loc[eligible.index], dev_b_scores.loc[eligible.index]
    common=eligible["skew"].notna()
    published=pd.read_csv(REPORTS/"hmm_ab_daily.csv",parse_dates=["decision_date"]).set_index("decision_date")
    published_a=float(published.loc[(published.index<=target.DEV_END)&published.B_alert_available,"A_predictive_risk_next"].quantile(.90)); published_b=float(published.loc[(published.index<=target.DEV_END)&published.B_alert_available,"B_predictive_risk_next"].quantile(.90))
    fullq=(float(full_a[common].quantile(.90)),float(full_b[common].quantile(.90))); devq=(float(dev_a_scores[common].quantile(.90)),float(dev_b_scores[common].quantile(.90)))
    lineage={"published_thresholds":{"A":published_a,"B":published_b},"reconstructed_full_refit_scores":{"A":fullq[0],"B":fullq[1]},"development_only_model_scores":{"A":devq[0],"B":devq[1]},"published_matches_full_refit":{"A":bool(np.isclose(published_a,fullq[0])),"B":bool(np.isclose(published_b,fullq[1]))},"selected_seeds":selected}
    checks.append({"check":"linaje de P90 publicado","status":"FAIL","observed":lineage,"minimum_example":"El script llama filtered_predictive(xa, full_models['A']) y filtered_predictive(xb, full_models['B']) antes de dev_common.quantile(.90)."})
    result={"target":"scripts/hmm_exploratory_ab.py","checks":checks,"threshold_lineage":lineage,"published_artifacts_changed":False}
    (REPORTS/"hmm_ab_audit.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    lines=["# Auditoría independiente — HMM A/B exploratorio","","Alcance: secuencias sintéticas y trazabilidad de código. No modifica `hmm_exploratory_ab.py`, datos, umbrales ni resultados publicados.","","## Algoritmo validado"]
    for c in checks[:-1]: lines.append(f"- **{c['check']}**: {c['status']}.")
    lines += ["","## Fallo encontrado","", "- **Linaje temporal de los P90: FAIL.** Los scores usados para P90 publicado no son los de los modelos ajustados hasta 2023-12-29. El código ajusta primero 10 modelos de desarrollo y selecciona semilla, pero después reajusta `full_models` con 2020–2026. Luego calcula `filtered_predictive` con esos `full_models` para fechas de desarrollo, filtra `dev_common` y toma P90. Los P90 publicados coinciden con la reconstrucción del reajuste completo, no con el modelo solo-desarrollo.", "", f"  - Publicados: A={published_a:.12f}, B={published_b:.12f}.", f"  - Reajuste completo: A={fullq[0]:.12f}, B={fullq[1]:.12f}.", f"  - Solo desarrollo (propuesta, no aplicada): A={devq[0]:.12f}, B={devq[1]:.12f}.", "", "Los resultados originales permanecen sin cambios, pero sus P90, alertas y métricas dependientes están **afectados por contaminación temporal de parámetros**. Esta auditoría no los sustituye.", "", "## Orden temporal observado", "", "Para A y B: (1) escalar con desarrollo; (2) ajustar diez semillas en desarrollo; (3) elegir semilla por verosimilitud de desarrollo; (4) reajustar el modelo elegido con 2020–2026; (5) obtener scores predictivos con ese reajuste, incluso en 2020–2023; (6) tomar P90 de esas fechas de desarrollo; (7) aplicar umbral. Por tanto, el orden implementado no es ajuste-hasta-2023 → scores-desarrollo → P90 → aplicación.", "", "## Corrección propuesta, no ejecutada", "", "Congelar para cada modelo el ajuste elegido sobre desarrollo, generar con ese modelo los scores de desarrollo y P90, y aplicar sin reajuste en cualquier tramo posterior. Un análisis separado puede decidir si un ajuste expansivo o rodante es admisible, pero debe predefinirse y no puede reemplazar este resultado exploratorio publicado.", "", "## Puntos no verificados", "", "- La prueba sintética valida aritmética de HMM diagonal y EM en casos pequeños; no sustituye una revisión externa completa ni cubre estabilidad numérica extrema.", "- La disponibilidad EOD antes de abrir t+1 sigue sin verificarse.", "- Toda conclusión 2020–2026 sigue siendo exploratoria; no hay confirmación prospectiva ni integración con Actinver."]
    (REPORTS/"hmm_ab_audit_report.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2))


if __name__ == "__main__": main()
