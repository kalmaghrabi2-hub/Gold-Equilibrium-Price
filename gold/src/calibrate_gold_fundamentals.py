#!/usr/bin/env python3
from __future__ import annotations
import json,math,statistics
from datetime import datetime,timezone
from pathlib import Path
from wgc_history import wgc_quarter,gold_quarters,feature,next_q
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'docs/gold/data/fundamentals_calibration.json';START=2017;MIN_TRAIN=12;MIN_OOS=12;RIDGE=1.5
def solve(A,b):
 n=len(b);M=[A[i][:]+[b[i]] for i in range(n)]
 for c in range(n):
  p=max(range(c,n),key=lambda r:abs(M[r][c]));M[c],M[p]=M[p],M[c];z=M[c][c]
  if abs(z)<1e-12:raise RuntimeError('singular')
  M[c]=[v/z for v in M[c]]
  for r in range(n):
   if r!=c:
    z=M[r][c];M[r]=[M[r][j]-z*M[c][j] for j in range(n+1)]
 return [M[i][-1] for i in range(n)]
def design(rows):
 cols=list(zip(*[r['x'] for r in rows]));mu=[statistics.fmean(c) for c in cols];sd=[statistics.pstdev(c) or 1 for c in cols];return [[1.0]+[(v-m)/s for v,m,s in zip(r['x'],mu,sd)] for r in rows],mu,sd
def fit(X,y):
 p=len(X[0]);A=[[0.0]*p for _ in range(p)];b=[0.0]*p
 for x,t in zip(X,y):
  for i in range(p):
   b[i]+=x[i]*t
   for j in range(p):A[i][j]+=x[i]*x[j]
 for i in range(1,p):A[i][i]+=RIDGE
 return solve(A,b)
def pred(x,b,mu,sd):return sum(a*v for a,v in zip(b,[1.0]+[(v-m)/s for v,m,s in zip(x,mu,sd)]))
def main():
 now=datetime.now(timezone.utc);lastq=(now.month-1)//3;lasty=now.year
 if lastq==0:lastq,lasty=4,lasty-1
 gold,gurl=gold_quarters();obs=[];cov=[];fail=[]
 for y in range(START,lasty+1):
  for q in (1,2,3):
   if (y,q)>(lasty,lastq):continue
   try:
    w=wgc_quarter(y,q);nn=next_q(y,q)
    if (y,q) not in gold or nn not in gold:raise RuntimeError('gold average unavailable')
    obs.append({'period':f'{y}-Q{q}','x':feature(w),'anchor':gold[(y,q)],'next':gold[nn],'ret':math.log(gold[nn]/gold[(y,q)])});cov.append(f'{y}-Q{q}')
   except Exception as e:fail.append({'period':f'{y}-Q{q}','reason':str(e)[:160]})
 if len(obs)<MIN_TRAIN+MIN_OOS:raise RuntimeError(f'insufficient exact WGC observations: {len(obs)}')
 pp=[];aa=[];nv=[];dirs=[];periods=[]
 for i in range(MIN_TRAIN,len(obs)):
  tr=obs[:i];X,mu,sd=design(tr);b=fit(X,[r['ret'] for r in tr]);r=obs[i];pr=pred(r['x'],b,mu,sd);pp.append(r['anchor']*math.exp(pr));aa.append(r['next']);nv.append(r['anchor']);dirs.append(int((pr>=0)==(r['ret']>=0)));periods.append(r['period'])
 X,mu,sd=design(obs);b=fit(X,[r['ret'] for r in obs]);mape=100*statistics.fmean(abs((a-p)/a) for a,p in zip(aa,pp));naive=100*statistics.fmean(abs((a-p)/a) for a,p in zip(aa,nv));mse=statistics.fmean((a-p)**2 for a,p in zip(aa,pp));nmse=statistics.fmean((a-p)**2 for a,p in zip(aa,nv));skill=100*(1-mse/nmse) if nmse else 0;direction=100*statistics.fmean(dirs);ma=statistics.fmean(aa);den=sum((a-ma)**2 for a in aa);r2=1-sum((a-p)**2 for a,p in zip(aa,pp))/den if den else 0;passed=len(aa)>=MIN_OOS and mape<=12 and direction>=45 and skill>=-10
 out={'generated_at_utc':now.isoformat(),'model':'wgc-quarterly-physical-overlay-ridge-v1','frequency':'quarterly','feature_period':'quarter q fundamentals','target':'average COMEX GC=F price in q+1 versus q','features':['strategic_demand_share','recycling_share','producer_hedging_share'],'beta':b,'means':mu,'sds':sd,'ridge_lambda':RIDGE,'metrics':{'wgc_quarters_exact':len(obs),'walk_forward_n':len(aa),'walk_forward_start_feature_period':periods[0],'walk_forward_end_feature_period':periods[-1],'price_r2':round(r2,4),'price_mape_pct':round(mape,3),'naive_mape_pct':round(naive,3),'rmse_usd_oz':round(math.sqrt(mse),2),'skill_vs_naive_mse_pct':round(skill,2),'direction_accuracy_pct':round(direction,2)},'walk_forward_gate':'PASS' if passed else 'FAIL','publication_status':'CALIBRATED' if passed else 'PROVISIONAL','coverage':{'first':cov[0],'last':cov[-1],'period_count':len(cov),'q4_policy':'excluded when quarterly table is ambiguous in full-year reports','failed_period_count':len(fail),'failed_periods':fail},'sources':{'fundamentals':'World Gold Council public Gold Demand Trends quarterly report section tables','gold_price':gurl},'rules':{'publication_lag':'features from q predict q+1; no same-quarter WGC look-ahead','missing_data':'exact observations only; no interpolation or imputation','min_training_quarters':MIN_TRAIN,'min_oos_quarters':MIN_OOS,'max_price_mape_pct':12.0,'min_direction_accuracy_pct':45.0,'min_skill_vs_naive_mse_pct':-10.0}}
 OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(out,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
