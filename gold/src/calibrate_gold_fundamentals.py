#!/usr/bin/env python3
from __future__ import annotations
import json, math, statistics
from datetime import datetime, timezone
from pathlib import Path
from wgc_history import wgc_quarter, gold_quarters, feature, next_q

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'docs/gold/data/fundamentals_calibration.json'
START = 2017
MIN_TRAIN = 12
MIN_OOS = 20
RIDGE = 1.5
MIN_MSE_SKILL = 2.0
MIN_REL_MAPE_IMPROVEMENT = 1.0
MIN_DIRECTION = 52.5


def solve(A, b):
    n = len(b); M = [A[i][:] + [b[i]] for i in range(n)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(M[r][c])); M[c], M[p] = M[p], M[c]; z = M[c][c]
        if abs(z) < 1e-12: raise RuntimeError('singular')
        M[c] = [v / z for v in M[c]]
        for r in range(n):
            if r != c:
                z = M[r][c]; M[r] = [M[r][j] - z * M[c][j] for j in range(n + 1)]
    return [M[i][-1] for i in range(n)]


def design(rows):
    cols = list(zip(*[r['x'] for r in rows])); mu = [statistics.fmean(c) for c in cols]; sd = [statistics.pstdev(c) or 1 for c in cols]
    return [[1.0] + [(v-m)/s for v,m,s in zip(r['x'],mu,sd)] for r in rows], mu, sd


def fit(X, y):
    p = len(X[0]); A = [[0.0]*p for _ in range(p)]; b = [0.0]*p
    for x,t in zip(X,y):
        for i in range(p):
            b[i] += x[i]*t
            for j in range(p): A[i][j] += x[i]*x[j]
    for i in range(1,p): A[i][i] += RIDGE
    return solve(A,b)


def pred(x,b,mu,sd):
    return sum(a*v for a,v in zip(b,[1.0]+[(v-m)/s for v,m,s in zip(x,mu,sd)]))


def write(out):
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(out,ensure_ascii=False,indent=2))


def main():
    now = datetime.now(timezone.utc); lastq = (now.month-1)//3; lasty = now.year
    if lastq == 0: lastq,lasty = 4,lasty-1
    gold,gurl = gold_quarters(); obs=[]; cov=[]; fail=[]
    for y in range(START,lasty+1):
        for q in (1,2,3):
            if (y,q) > (lasty,lastq): continue
            try:
                w = wgc_quarter(y,q); nn = next_q(y,q)
                if (y,q) not in gold or nn not in gold: raise RuntimeError('gold average unavailable')
                obs.append({'period':f'{y}-Q{q}','x':feature(w),'anchor':gold[(y,q)],'next':gold[nn],'ret':math.log(gold[nn]/gold[(y,q)])}); cov.append(f'{y}-Q{q}')
            except Exception as e:
                fail.append({'period':f'{y}-Q{q}','reason':str(e)[:160]})
    if len(obs) < MIN_TRAIN + 1:
        out = {
            'generated_at_utc': now.isoformat(),
            'model':'wgc-quarterly-physical-overlay-ridge-v2-research',
            'frequency':'quarterly',
            'publication_status':'RESEARCH_ONLY',
            'promotion_eligible':False,
            'walk_forward_gate':'FAIL',
            'statistical_research_gate':'NOT_RUN_INSUFFICIENT_EXACT_DATA',
            'physical_price_validation_gate':'NOT_AVAILABLE_POINT_IN_TIME_VINTAGES',
            'metrics':{'wgc_quarters_exact':len(obs),'walk_forward_n':0},
            'coverage':{'first':cov[0] if cov else None,'last':cov[-1] if cov else None,'period_count':len(cov),'required_minimum_for_training':MIN_TRAIN+1,'failed_period_count':len(fail),'failed_periods':fail},
            'promotion_blocker':f'INSUFFICIENT_EXACT_POINT_IN_TIME_DATA: only {len(obs)} exact usable WGC quarters; at least {MIN_TRAIN+1} are required before training. No interpolation or imputation is allowed. Historical release/vintage mapping is also incomplete.',
            'sources':{'fundamentals':'World Gold Council public Gold Demand Trends quarterly report section tables','gold_price':gurl},
            'rules':{'publication_lag':'features from q may predict q+1 only after verified original release date','missing_data':'exact observations only; no interpolation or imputation','min_training_quarters':MIN_TRAIN,'min_oos_quarters':MIN_OOS,'min_mse_skill_pct':MIN_MSE_SKILL,'min_relative_mape_improvement_pct':MIN_REL_MAPE_IMPROVEMENT,'min_direction_accuracy_pct':MIN_DIRECTION,'no_price_clipping':True,'failed_layer_price_weight':0.0}
        }
        write(out)
        return
    pp=[]; aa=[]; nv=[]; dirs=[]; periods=[]
    for i in range(MIN_TRAIN,len(obs)):
        tr=obs[:i]; X,mu,sd=design(tr); b=fit(X,[r['ret'] for r in tr]); r=obs[i]; pr=pred(r['x'],b,mu,sd)
        pp.append(r['anchor']*math.exp(pr)); aa.append(r['next']); nv.append(r['anchor']); dirs.append(int((pr>=0)==(r['ret']>=0))); periods.append(r['period'])
    X,mu,sd=design(obs); b=fit(X,[r['ret'] for r in obs])
    mape=100*statistics.fmean(abs((a-p)/a) for a,p in zip(aa,pp)); naive=100*statistics.fmean(abs((a-p)/a) for a,p in zip(aa,nv))
    mse=statistics.fmean((a-p)**2 for a,p in zip(aa,pp)); nmse=statistics.fmean((a-p)**2 for a,p in zip(aa,nv)); skill=100*(1-mse/nmse) if nmse else 0
    rel_mape=100*(naive-mape)/naive if naive else 0; direction=100*statistics.fmean(dirs)
    ma=statistics.fmean(aa); den=sum((a-ma)**2 for a in aa); r2=1-sum((a-p)**2 for a,p in zip(aa,pp))/den if den else 0
    statistical_checks = {'min_oos_quarters': len(aa) >= MIN_OOS,'min_mse_skill': skill >= MIN_MSE_SKILL,'min_relative_mape_improvement': rel_mape >= MIN_REL_MAPE_IMPROVEMENT,'directional_information': direction >= MIN_DIRECTION,'sanity_mape': mape <= 12.0}
    statistical_pass = all(statistical_checks.values())
    out = {
        'generated_at_utc':now.isoformat(), 'model':'wgc-quarterly-physical-overlay-ridge-v2-research', 'frequency':'quarterly',
        'feature_period':'quarter q fundamentals', 'target':'average COMEX GC=F price in q+1 versus q',
        'features':['strategic_demand_share','recycling_share','producer_hedging_share'], 'beta':b, 'means':mu, 'sds':sd, 'ridge_lambda':RIDGE,
        'metrics':{'wgc_quarters_exact':len(obs),'walk_forward_n':len(aa),'walk_forward_start_feature_period':periods[0] if periods else None,'walk_forward_end_feature_period':periods[-1] if periods else None,'price_r2':round(r2,4),'price_mape_pct':round(mape,3),'naive_mape_pct':round(naive,3),'relative_mape_improvement_pct':round(rel_mape,3),'rmse_usd_oz':round(math.sqrt(mse),2),'skill_vs_naive_mse_pct':round(skill,2),'direction_accuracy_pct':round(direction,2)},
        'statistical_research_gate':'PASS' if statistical_pass else 'FAIL', 'statistical_checks':statistical_checks,
        'physical_price_validation_gate':'NOT_AVAILABLE_POINT_IN_TIME_VINTAGES', 'walk_forward_gate':'FAIL', 'publication_status':'RESEARCH_ONLY', 'promotion_eligible':False,
        'promotion_blocker':'Exact point-in-time WGC release/vintage mapping is incomplete; current public historical pages cannot be treated as information known on each historical forecast date.',
        'coverage':{'first':cov[0] if cov else None,'last':cov[-1] if cov else None,'period_count':len(cov),'q4_policy':'excluded when quarterly table is ambiguous in full-year reports','failed_period_count':len(fail),'failed_periods':fail},
        'sources':{'fundamentals':'World Gold Council public Gold Demand Trends quarterly report section tables','gold_price':gurl},
        'rules':{'publication_lag':'features from q may predict q+1 only after verified original release date','missing_data':'exact observations only; no interpolation or imputation','min_training_quarters':MIN_TRAIN,'min_oos_quarters':MIN_OOS,'min_mse_skill_pct':MIN_MSE_SKILL,'min_relative_mape_improvement_pct':MIN_REL_MAPE_IMPROVEMENT,'min_direction_accuracy_pct':MIN_DIRECTION,'no_price_clipping':True,'failed_layer_price_weight':0.0}
    }
    write(out)

if __name__=='__main__': main()
