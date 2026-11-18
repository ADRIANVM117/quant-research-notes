"""Data Sanity v1 para los Parquet diarios Silver de Reto Actinver."""
from __future__ import annotations

import argparse
import csv
import os
import shutil
import tempfile
import uuid
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import polars as pl

ROOT = Path(__file__).resolve().parents[1]
SILVER = ROOT / "data" / "parquet"
GOLD = ROOT / "data" / "gold" / "daily_series"
QUALITY = ROOT / "data" / "quality"
EXPECTED = {
    "symbol_requested": pl.String, "session_date": pl.Date, "open": pl.Float64,
    "high": pl.Float64, "low": pl.Float64, "close": pl.Float64,
    "adjusted_close": pl.Float64, "volume": pl.Int64, "dividend_amount": pl.Float64,
    "split_coefficient": pl.Float64, "provider_timezone": pl.String,
    "source": pl.String, "provider_last_refreshed": pl.String,
    "ingested_at_utc": pl.Datetime(time_zone="UTC"),
}
PRICE = ("open", "high", "low", "close", "adjusted_close")
STATUS_COLUMNS = ["run_timestamp_utc", "asset_class", "symbol_requested", "silver_path", "status", "row_count", "min_session_date", "max_session_date", "rejection_count", "warning_count", "missing_session_count", "identical_bar_run_count", "positive_dividend_sessions", "non_unit_split_sessions", "gold_path", "approval_method", "manual_decision", "manual_decision_reason", "pending_action"]
ISSUE_COLUMNS = ["run_timestamp_utc", "asset_class", "symbol_requested", "severity", "rule_id", "rule_name", "session_date", "period_start", "period_end", "observed_value", "expected_condition", "details", "silver_path"]

def issue(now, asset, symbol, silver, severity, rule, name, **values):
    return {"run_timestamp_utc": now, "asset_class": asset, "symbol_requested": symbol,
            "severity": severity, "rule_id": rule, "rule_name": name,
            "session_date": "", "period_start": "", "period_end": "", "observed_value": "",
            "expected_condition": "", "details": "", "silver_path": str(silver), **values}

def atomic_csv(path: Path, columns: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); tmp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp.csv")
    try:
        with tmp.open("x", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=columns); writer.writeheader(); writer.writerows(rows)
        with tmp.open(encoding="utf-8", newline="") as f:
            if csv.DictReader(f).fieldnames != columns: raise RuntimeError("CSV temporal inválido.")
        os.replace(tmp, path)
    finally:
        if tmp.exists(): tmp.unlink()

def load_manual(path=QUALITY/'manual_quality_decisions.csv'):
    fields=['symbol_requested','asset_class','manual_decision','approved_warning_rule_ids','decision_reason','evidence_file','reviewed_at_utc','reviewer','pending_action']
    if not path.exists():
        return {}
    with path.open(encoding='utf-8',newline='') as f: rows=list(csv.DictReader(f))
    if not rows or list(rows[0])!=fields: raise ValueError('Esquema de decisiones manuales inválido.')
    out={}
    for r in rows:
        key=(r['asset_class'],r['symbol_requested'])
        if key in out: raise ValueError('Decisión manual duplicada.')
        if r['manual_decision'] not in ('APPROVE_FOR_GOLD','KEEP_IN_SUBGOLD'): raise ValueError('Decisión manual no permitida.')
        out[key]=r
    return out

def validate_frame(frame: pl.DataFrame, now_date: date, now: str, asset: str, symbol: str, silver: Path):
    issues=[]
    if frame.columns != list(EXPECTED) or frame.schema != pl.Schema(EXPECTED):
        issues.append(issue(now,asset,symbol,silver,"REJECTION","R1","Esquema válido",expected_condition="14 columnas y tipos exactos",observed_value=str(frame.schema)))
        return issues
    if frame.height == 0:
        return [issue(now,asset,symbol,silver,"REJECTION","R1","Esquema válido",expected_condition="al menos una fila",observed_value="0")]
    dup=frame.group_by(["symbol_requested","session_date"]).len().filter(pl.col("len")>1)
    for r in dup.to_dicts(): issues.append(issue(now,asset,symbol,silver,"REJECTION","R2","Unicidad temporal",session_date=str(r["session_date"]),observed_value=str(r["len"]),expected_condition="una fila por símbolo y fecha"))
    dates=frame.get_column("session_date").to_list()
    if dates != sorted(dates): issues.append(issue(now,asset,symbol,silver,"REJECTION","R3","Orden temporal",expected_condition="session_date ascendente"))
    for d in dates:
        if d > now_date: issues.append(issue(now,asset,symbol,silver,"REJECTION","R3","Fecha futura",session_date=str(d),expected_condition="no posterior a fecha local CDMX"))
    for c in PRICE:
        bad=frame.filter(pl.col(c).is_null() | (pl.col(c)<=0))
        for r in bad.select("session_date",c).to_dicts(): issues.append(issue(now,asset,symbol,silver,"REJECTION","R4","Precios válidos",session_date=str(r["session_date"]),observed_value=str(r[c]),expected_condition=f"{c} no nulo y > 0"))
    bad_high=frame.filter((pl.col("high")<pl.max_horizontal("open","close","low")))
    bad_low=frame.filter((pl.col("low")>pl.min_horizontal("open","close","high")))
    for r in bad_high.select("session_date").to_dicts(): issues.append(issue(now,asset,symbol,silver,"REJECTION","R5","OHLC coherente",session_date=str(r["session_date"]),expected_condition="high >= max(open, close, low)"))
    for r in bad_low.select("session_date").to_dicts(): issues.append(issue(now,asset,symbol,silver,"REJECTION","R5","OHLC coherente",session_date=str(r["session_date"]),expected_condition="low <= min(open, close, high)"))
    for c, cond in (("volume",pl.col("volume").is_null() | (pl.col("volume")<0)),("dividend_amount",pl.col("dividend_amount").is_null() | (pl.col("dividend_amount")<0)),("split_coefficient",pl.col("split_coefficient").is_null() | (pl.col("split_coefficient")<=0))):
        for r in frame.filter(cond).select("session_date",c).to_dicts(): issues.append(issue(now,asset,symbol,silver,"REJECTION","R6","Campos de mercado válidos",session_date=str(r["session_date"]),observed_value=str(r[c]),expected_condition=f"{c} válido"))
    return issues

def identical_warnings(frame, now, asset, symbol, silver):
    warnings=[]; runs=[]; start=0; values=frame.select(["open","high","low","close"]).rows()
    for i in range(1, len(values)+1):
        if i==len(values) or values[i] != values[start]:
            if i-start >= 3: runs.append((start,i-1))
            start=i
    for a,b in runs:
        block=frame.slice(a,b-a+1); row=block.row(0,named=True)
        warnings.append(issue(now,asset,symbol,silver,"WARNING","R8","Barras idénticas consecutivas",period_start=str(row["session_date"]),period_end=str(block.row(-1,named=True)["session_date"]),observed_value=str({c:row[c] for c in ("open","high","low","close")}),expected_condition="menos de tres sesiones OHLC idénticas",details=f"sesiones={block.height}; volumes={block.get_column('volume').to_list()}"))
    return warnings

def info_issues(frame, now, asset, symbol, silver):
    info=[]
    returns=frame.with_columns(pl.col("adjusted_close").pct_change().alias("r")).filter(pl.col("r").is_not_null()).with_columns(pl.col("r").abs().alias("abs_r")).sort("abs_r",descending=True).head(5)
    for r in returns.select("session_date","r").to_dicts(): info.append(issue(now,asset,symbol,silver,"INFORMATION","I1","Retorno extremo informativo",session_date=str(r["session_date"]),observed_value=str(r["r"]),details="top 5 por retorno absoluto; sin umbral de rechazo"))
    for col, predicate, rule in (("dividend_amount",pl.col("dividend_amount")>0,"I2"),("split_coefficient",pl.col("split_coefficient")!=1,"I3")):
        for r in frame.filter(predicate).select("session_date",col).to_dicts(): info.append(issue(now,asset,symbol,silver,"INFORMATION",rule,"Corporate action informativa",session_date=str(r["session_date"]),observed_value=str(r[col]),details=col))
    return info

def copy_gold(source: Path, destination: Path, fail=False):
    destination.parent.mkdir(parents=True,exist_ok=True); tmp=destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.tmp.parquet")
    try:
        shutil.copyfile(source,tmp); candidate=pl.read_parquet(tmp); original=pl.read_parquet(source)
        if candidate.schema != original.schema or not candidate.equals(original): raise RuntimeError("Gold temporal no coincide con Silver.")
        if fail: raise RuntimeError("Falla simulada antes de os.replace.")
        os.replace(tmp,destination)
    finally:
        if tmp.exists(): tmp.unlink()

def run_self_test():
    test_root = ROOT / "data" / ".tmp"
    test_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=test_root) as d:
        p=Path(d); now=date.today(); base=pl.DataFrame({"symbol_requested":["X"]*3,"session_date":[date(2024,1,2),date(2024,1,3),date(2024,1,4)],"open":[1.0]*3,"high":[1.0]*3,"low":[1.0]*3,"close":[1.0]*3,"adjusted_close":[1.0]*3,"volume":[0]*3,"dividend_amount":[0.0]*3,"split_coefficient":[1.0]*3,"provider_timezone":["US/Eastern"]*3,"source":["X"]*3,"provider_last_refreshed":["x"]*3,"ingested_at_utc":[datetime.now(timezone.utc)]*3},schema=EXPECTED)
        def rejected(f): return bool(validate_frame(f,now,"t","equity","X",p))
        assert not rejected(base); assert len(identical_warnings(base,"t","equity","X",p))==1
        assert len(identical_warnings(base.head(2),"t","equity","X",p))==0
        assert not rejected(base.head(2)) and not identical_warnings(base.head(2),"t","equity","X",p)  # GOLD_APPROVED
        assert not rejected(base) and identical_warnings(base,"t","equity","X",p)  # SUBGOLD_REVIEW
        assert rejected(base.drop("open")); assert rejected(base.with_columns(pl.col("volume").cast(pl.Float64)))
        assert rejected(pl.concat([base, base.head(1)]))  # fecha duplicada / REJECTED
        assert rejected(base.with_columns(pl.col("session_date").reverse())); assert rejected(base.with_columns(pl.when(pl.int_range(0,pl.len())==1).then(date.today().replace(year=date.today().year+1)).otherwise(pl.col("session_date")).alias("session_date")))
        for col,val in (("open",None),("close",0.0),("high",0.5),("low",2.0),("volume",None),("volume",-1),("dividend_amount",-1.0),("split_coefficient",0.0)):
            assert rejected(base.with_columns(pl.when(pl.int_range(0,pl.len())==0).then(pl.lit(val,dtype=base.schema[col])).otherwise(pl.col(col)).alias(col)))
        silver=p/"silver.parquet"; gold=p/"gold.parquet"; base.head(2).write_parquet(silver); copy_gold(silver,gold); assert pl.read_parquet(gold).equals(base.head(2)); old=gold.read_bytes()
        try: copy_gold(silver,gold,True)
        except RuntimeError: pass
        else: raise AssertionError("No falló la copia simulada")
        assert gold.read_bytes()==old

def main():
    parser=argparse.ArgumentParser(description="Data Sanity v1 de Parquet diarios Silver."); parser.add_argument("--self-test",action="store_true"); parser.add_argument("--asset-class",choices=("equity","etf")); parser.add_argument("--symbol"); args=parser.parse_args()
    if args.self_test: run_self_test(); print("OFFLINE_TESTS=PASS"); return
    if args.symbol and not args.asset_class: parser.error("--symbol requiere --asset-class")
    now=datetime.now(timezone.utc).isoformat(); today=datetime.now(ZoneInfo("America/Mexico_City")).date(); decisions=load_manual(); audited=[]; frames={}; issues=[]
    asset_classes=(args.asset_class,) if args.asset_class else ("equity","etf")
    for asset in asset_classes:
        for silver in sorted((SILVER/asset).glob("*.parquet")):
            symbol=silver.stem
            if args.symbol and symbol != args.symbol.strip().upper(): continue
            try: frame=pl.read_parquet(silver); rejects=validate_frame(frame,today,now,asset,symbol,silver)
            except Exception as exc: frame=None; rejects=[issue(now,asset,symbol,silver,"REJECTION","R1","Esquema válido",details=f"lectura: {exc}")]
            frames[(asset,symbol)]=frame; audited.append((asset,symbol,silver,frame,rejects))
    valid=[(a,s,f) for a,s,_,f,r in audited if not r and f is not None]
    session_counts=Counter(); active={}
    for a,s,f in valid:
        ds=f.get_column("session_date").to_list(); active[(a,s)]=(min(ds),max(ds),set(ds))
    all_dates=sorted(set().union(*(x[2] for x in active.values()))) if active else []
    reference={d for d in all_dates if sum(lo<=d<=hi for lo,hi,_ in active.values()) and sum(d in ss for lo,hi,ss in active.values()) >= .9*sum(lo<=d<=hi for lo,hi,_ in active.values())}
    status_rows=[]
    known={(a,s) for a,s,_,_,_ in audited}
    if not set(decisions).issubset(known): raise ValueError('Símbolo desconocido en decisiones manuales.')
    for asset,symbol,silver,frame,rejects in audited:
        warnings=[]; infos=[]
        if not rejects and frame is not None:
            lo,hi,seen=active[(asset,symbol)]
            for d in sorted(x for x in reference if lo<=x<=hi and x not in seen): warnings.append(issue(now,asset,symbol,silver,"WARNING","R7","Sesión de consenso faltante",session_date=str(d),expected_condition="CONSENSUS_US_SESSION_CALENDAR_V1"))
            warnings += identical_warnings(frame,now,asset,symbol,silver); infos=info_issues(frame,now,asset,symbol,silver)
        issues += rejects+warnings+infos; status="REJECTED" if rejects else "SUBGOLD_REVIEW" if warnings else "GOLD_APPROVED"; gold_path=""; decision=decisions.get((asset,symbol)); method='AUTOMATIC'
        if decision:
            if decision['manual_decision']=='KEEP_IN_SUBGOLD': status='SUBGOLD_REVIEW'; method='PENDING_REVIEW'
            elif not rejects and {x['rule_id'] for x in warnings}.issubset(set(filter(None,decision['approved_warning_rule_ids'].split(',')))): status='GOLD_APPROVED'; method='MANUAL'
        if status=="GOLD_APPROVED":
            target=GOLD/asset/silver.name; copy_gold(silver,target); gold_path=str(target)
        positive=frame.filter(pl.col("dividend_amount")>0).height if frame is not None and not rejects else 0; splits=frame.filter(pl.col("split_coefficient")!=1).height if frame is not None and not rejects else 0
        status_rows.append({"run_timestamp_utc":now,"asset_class":asset,"symbol_requested":symbol,"silver_path":str(silver),"status":status,"row_count":frame.height if frame is not None else 0,"min_session_date":str(frame.get_column("session_date").min()) if frame is not None and not rejects else "","max_session_date":str(frame.get_column("session_date").max()) if frame is not None and not rejects else "","rejection_count":len(rejects),"warning_count":len(warnings),"missing_session_count":sum(x["rule_id"]=="R7" for x in warnings),"identical_bar_run_count":sum(x["rule_id"]=="R8" for x in warnings),"positive_dividend_sessions":positive,"non_unit_split_sessions":splits,"gold_path":gold_path,"approval_method":method,"manual_decision":decision['manual_decision'] if decision else '',"manual_decision_reason":decision['decision_reason'] if decision else '',"pending_action":decision['pending_action'] if decision else ''})
    atomic_csv(QUALITY/"series_status.csv",STATUS_COLUMNS,status_rows); atomic_csv(QUALITY/"quality_issues.csv",ISSUE_COLUMNS,issues)
    groups={k:[r["symbol_requested"] for r in status_rows if r["status"]==k] for k in ("GOLD_APPROVED","SUBGOLD_REVIEW","REJECTED")}; reasons=Counter(x["rule_id"] for x in issues)
    (QUALITY/"daily_quality_summary.md").write_text("# Data Sanity v1\n\n"+f"- Timestamp: {now}\n- Series auditadas: {len(status_rows)}\n- GOLD_APPROVED: {len(groups['GOLD_APPROVED'])}\n- SUBGOLD_REVIEW: {len(groups['SUBGOLD_REVIEW'])}\n- REJECTED: {len(groups['REJECTED'])}\n- Sesiones de consenso faltantes: {reasons['R7']}\n- Corridas de barras idénticas: {reasons['R8']}\n- Silver no fue modificado.\n- Calendario: `CONSENSUS_US_SESSION_CALENDAR_V1` es provisional y no sustituye un calendario bursátil oficial.\n\n"+"## Instrumentos por estado\n\n"+"\n".join(f"- {k}: {', '.join(v) or 'ninguno'}" for k,v in groups.items())+"\n\n## Motivos por regla\n\n"+"\n".join(f"- {k}: {v}" for k,v in sorted(reasons.items()))+"\n\n## Gold promovidos\n\n"+"\n".join(f"- {r['asset_class']}/{r['symbol_requested']}" for r in status_rows if r['gold_path']),encoding="utf-8")
    print(f"AUDITED={len(status_rows)} GOLD_APPROVED={len(groups['GOLD_APPROVED'])} SUBGOLD_REVIEW={len(groups['SUBGOLD_REVIEW'])} REJECTED={len(groups['REJECTED'])}")
if __name__=="__main__": main()
