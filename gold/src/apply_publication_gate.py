#!/usr/bin/env python3
"""Apply the final benchmark publication gate to the gold P*."""
from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
LATEST=ROOT/'docs/gold/data/latest.json'; CAL=ROOT/'docs/gold/data/weekly_calibration.json'
def main():
    d=json.loads(LATEST.read_text(encoding='utf-8')); c=json.loads(CAL.read_text(encoding='utf-8'))
    m=c.get('metrics') or {}; live=c.get('live') or {}; model=d.get('model')
    if not model: return
    passed=c.get('walk_forward_gate')=='PASS' and c.get('benchmark_gate')=='PASS'
    candidate=float(live.get('fair_value_usd_oz') or model['weekly_fair_value_usd_oz'])
    fallback=float(live.get('anchor_usd_oz') or candidate); active=candidate if passed else fallback
    market=float(d['market']['usd_oz'])
    acc=m.get('accuracy_pct') if passed else m.get('naive_accuracy_pct'); mape=m.get('mape_pct') if passed else m.get('naive_mape_pct'); rmse=m.get('rmse_usd_oz') if passed else m.get('naive_rmse_usd_oz')
    model['weekly_fair_value_usd_oz']=round(active,2); model['macro_fair_value_usd_oz']=round(active,2)
    physical=model.get('physical_overlay') or {}; effective_mult=float(physical.get('effective_multiplier',1.0)) if physical.get('applied_to_pstar') else 1.0
    applied=active*effective_mult; low,high=.55*market,1.55*market; pstar=min(max(applied,low),high)
    model['applied_combined_p_star_usd_oz']=round(applied,2); model['fundamental_p_star_usd_oz']=round(pstar,2); model['market_vs_pstar_pct']=round((market/pstar-1)*100,2)
    model['publication_source']='BENCHMARK_MODEL' if passed else 'PERSISTENCE_FALLBACK'
    model['accuracy']={**(model.get('accuracy') or {}),'oos_accuracy_pct':acc,'mape_pct':mape,'rmse_usd_oz':rmse,'candidate_model_accuracy_pct':m.get('accuracy_pct'),'candidate_model_mape_pct':m.get('mape_pct'),'naive_accuracy_pct':m.get('naive_accuracy_pct'),'naive_mape_pct':m.get('naive_mape_pct'),'definition':'100 - MAPE on the effective published layer over the final OOS window; descriptive, not a probability'}
    d['model_status']='VALID' if passed and d.get('model_status')=='VALID' else 'PROVISIONAL'; model['status']=d['model_status']
    LATEST.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'publication_source':model['publication_source'],'pstar_usd_oz':model['fundamental_p_star_usd_oz'],'effective_accuracy_pct':acc},ensure_ascii=False))
if __name__=='__main__': main()
