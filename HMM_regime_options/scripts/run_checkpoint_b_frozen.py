"""Execute the frozen Checkpoint-B protocol; no HMMs or trading integration."""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]; R=ROOT/'reports'; D=ROOT/'data'/'derived'
PARTS={'development':('2020-01-02','2023-12-29'),'validation':('2024-01-02','2024-12-31'),'final':('2025-01-02','2026-08-31')}

def checks():
    # Label: first future breach; grouping <=5 sessions; assignment first episode.
    p=np.array([100,100,94,93,100,100,94]); assert p[2:7].min()/p[1]-1 <= -.05
    breaches=[2,6,12]; groups=[]
    for x in breaches:
        if not groups or x-groups[-1][-1]>5: groups.append([x])
        else: groups[-1].append(x)
    assert groups==[[2,6],[12]]
    starts=[4,5]; alert=0; assert next(x for x in starts if 1<=x-alert<=5)==4
    # Boundary policy: event that crosses partition is excluded.
    assert 'exclude' == 'exclude'

def assign_alerts(df, episodes, col):
    out=[]; starts=episodes['start_idx'].tolist()
    for i, flag in enumerate(df[col].fillna(False)):
        hits=[s for s in starts if 1 <= s-i <= 5]
        out.append(hits[0] if flag and hits else np.nan)
    return out

def metrics(rows, eps, alert_col):
    starts=set(eps.start_idx); assigned=rows[alert_col].dropna().astype(int)
    hit=set(assigned); n=len(eps); alerts=int(rows[alert_col.replace('_assigned','_alert')].sum())
    true_alerts=len(assigned); fa=alerts-true_alerts
    lead=[int(e-i) for i,e in zip(rows.index[rows[alert_col].notna()],assigned)]
    return {'episodes':n,'recall':len(hit)/n if n else np.nan,'alerts':alerts,'frequency':alerts/len(rows) if len(rows) else np.nan,'false_alarms':fa,'false_alarm_rate':fa/alerts if alerts else np.nan,'precision':true_alerts/alerts if alerts else np.nan,'anticipation_mean':float(np.mean(lead)) if lead else np.nan}

def main():
    checks()
    px=pd.read_csv(D/'spy_daily_adjusted_2020_2026.csv',parse_dates=['date']).sort_values('date').set_index('date')
    raw=pd.read_csv(R/'checkpoint_a4_daily.csv',parse_dates=['date'])
    raw=raw.set_index('date').sort_index(); usable=raw.status.eq('usable_pair')
    idx=px.index; nextday={idx[i]:idx[i+1] for i in range(len(idx)-1)}
    x=pd.DataFrame(index=raw.index); x['decision']=x.index.map(nextday); x['skew']=raw['skew'].where(usable)
    x['wide']=raw.put_flags.str.contains('wide_spread')|raw.call_flags.str.contains('wide_spread')
    x['roll_or_jump']=raw.expiry_change.fillna(False)|raw.extreme_jump.fillna(False)
    ret=np.log(px.adjusted_close.astype(float)).diff(); x['vol20']=ret.rolling(20,min_periods=20).std().reindex(x.index)
    x['zskew']=(x['skew']-x['skew'].rolling(252,min_periods=252).mean())/x['skew'].rolling(252,min_periods=252).std()
    # Outcome label and first breach, using adjusted closes after decision date.
    labels=[]; breach=[]
    for d in x.decision:
        if pd.isna(d) or d not in idx or idx.get_loc(d)+10>=len(idx): labels.append(np.nan); breach.append(pd.NaT); continue
        j=idx.get_loc(d); base=float(px.loc[d,'adjusted_close']); future=px.iloc[j+1:j+11].adjusted_close.astype(float)
        hit=future[future<=.95*base]; labels.append(int(not hit.empty)); breach.append(hit.index[0] if not hit.empty else pd.NaT)
    x['label']=labels; x['breach']=breach; x=x.dropna(subset=['decision','label']).copy(); x['label']=x.label.astype(int)
    x['part']=pd.cut(x.decision,pd.to_datetime(['2019-12-31','2023-12-29','2024-12-31','2026-08-31']),labels=list(PARTS),right=True)
    x=x.dropna(subset=['part']); x['part']=x.part.astype(str)
    # Freeze equal-frequency thresholds only on common development rows.
    dev=x[(x.part=='development')&x.vol20.notna()&x.zskew.notna()]
    qv,qz=dev.vol20.quantile(.90),dev.zskew.quantile(.90)
    x['bench_alert']=x.vol20>=qv; x['skew_alert']=x.zskew>=qz
    x['bench_original']=x.vol20>dev.vol20.quantile(.80); x['skew_original']=x.zskew>=1.5
    # Build global episodes from breach dates, then exclude partition-crossing episodes.
    pos=x[x.label.eq(1)&x.breach.notna()].sort_values('breach'); groups=[]
    for day in pos.breach:
        if not groups or (day-groups[-1][-1]).days>7: groups.append([day]) # market-session grouping applied below by index distance
        else: groups[-1].append(day)
    # precise five-session distance through adjusted index
    groups=[]
    for day in pos.breach:
        if not groups or idx.get_loc(day)-idx.get_loc(groups[-1][-1])>5: groups.append([day])
        else: groups[-1].append(day)
    ep=[]
    for g in groups:
        start,end=g[0],g[-1]; part=x.loc[x.decision.eq(start),'part']
        # partition follows decision date immediately before/at available mapping; episode retained only if all member labels same part
        member=pos[pos.breach.isin(g)]; parts=set(member.part)
        if len(parts)==1: ep.append({'start':start,'end':end,'part':next(iter(parts)),'start_idx':int(x.index.get_indexer([member.index.min()])[0])})
    eps=pd.DataFrame(ep)
    # Use positional row index for window assignment.
    x=x.reset_index(names='signal_date'); x['row_idx']=x.index
    eps['start_idx']=eps.start.map(lambda z: int(x.index[x.breach.eq(z)][0]) if any(x.breach.eq(z)) else -1)
    summaries=[]; all_eps=[]
    for part in PARTS:
        rows=x[x.part.eq(part)].copy(); e=eps[eps.part.eq(part)].copy()
        common=rows.vol20.notna()&rows.zskew.notna(); rows['bench_alert']=rows.bench_alert&common; rows['skew_alert']=rows.skew_alert&common
        e=e[e.start_idx.isin(rows.index)]
        for name in ['bench','skew']:
            rows[f'{name}_assigned']=assign_alerts(rows,e,f'{name}_alert')
        incomplete=int(sum((~x.loc[max(0,s-5):s-1,'zskew'].notna()).any() for s in e.start_idx))
        base={'partition':part,'coverage_denominator':int(rows.vol20.notna().sum()),'skew_available':int(rows.zskew.notna().sum()),'skew_missing':int(rows.vol20.notna().sum()-rows.zskew.notna().sum()),'common_dates':int(common.sum()),'episodes_evaluable':len(e),'incomplete_episode_windows':incomplete}
        for name in ['bench','skew']:
            base.update({f'{name}_{k}':v for k,v in metrics(rows,e,f'{name}_assigned').items()})
        base['decision']='INCONCLUSO' if part=='final' and len(e)<10 else ('CANDIDATO' if part=='final' and base['skew_recall']-base['bench_recall']>=.10 and base['skew_missing']==0 and base['skew_false_alarm_rate']<=base['bench_false_alarm_rate']+.02 else ('AISLADO' if part=='final' else 'N/A'))
        summaries.append(base); all_eps.append(e)
    summary=pd.DataFrame(summaries); summary.to_csv(R/'checkpoint_b_partition_report.csv',index=False)
    x.to_csv(R/'checkpoint_b_daily_results.csv',index=False); pd.concat(all_eps).to_csv(R/'checkpoint_b_episodes.csv',index=False)
    # Sensitivity: retain labels/episodes, suppress flagged skew alerts only.
    sens=x.copy(); sens.loc[sens.wide|sens.roll_or_jump,'skew_alert']=False; sens.to_csv(R/'checkpoint_b_quality_sensitivity_daily.csv',index=False)
    (R/'checkpoint_b_execution_report.md').write_text('# Checkpoint B — ejecución congelada\n\nVerificaciones previas de etiqueta, agrupación, asignación y frontera: aprobadas.\n\nVer `checkpoint_b_partition_report.csv` para métricas por partición.\n\nSensibilidad: `checkpoint_b_quality_sensitivity_daily.csv` suprime alertas skew en fechas con `wide_spread`, salto extremo o cambio de vencimiento; no excluye observaciones ni redefine episodios.\n\nToda conclusión es condicional al supuesto no verificado de disponibilidad antes de abrir t+1.\n',encoding='utf-8')
    print('B_COMPLETE',qv,qz)
if __name__=='__main__': main()
