from __future__ import annotations
import html,json,re,statistics,urllib.parse,urllib.request
from datetime import datetime,timezone
UA='Mozilla/5.0 GoldEquilibriumPrice/3.2'
def get(u,accept='text/html,*/*'):
 r=urllib.request.Request(u,headers={'User-Agent':UA,'Accept':accept})
 with urllib.request.urlopen(r,timeout=45) as x:return x.read().decode('utf-8',errors='replace')
def flat(u):return re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',html.unescape(get(u))).replace('\u00a0',' '))
def value(t,*labels,required=True):
 for label in labels:
  m=re.search(re.escape(label)+r"\s*\|?\s*([\-\d,.]+)\s*\|?\s*([\-\d,.]+)\s*\|?\s*([\-\d,.]+)\s*\|?\s*([\-\d,.]+)\s*\|?\s*([\-\d,.]+)",t,re.I)
  if m:return float(m.group(5).replace(',',''))
 if required:raise RuntimeError('missing '+labels[0])
 return 0.0
def wgc_quarter(y,q):
 b=f'https://www.gold.org/goldhub/research/gold-demand-trends/gold-demand-trends-q{q}-{y}'
 s=flat(b+'/supply');i=flat(b+'/investment')
 try:c=flat(b+'/central-banks')
 except Exception:c=flat(b+'/central-banks-and-other-institutions')
 return {'total_supply_t':value(s,'Total Supply'),'recycled_gold_t':value(s,'Recycled Gold','Recycling'),'producer_hedging_t':value(s,'Net Producer Hedging','Producer Hedging',required=False),'bar_coin_t':value(i,'Total Bar and Coin','Total Bar & Coin Demand','Bar and Coin'),'etf_t':value(i,'ETFs & Similar Products','Gold ETFs','ETFs'),'central_banks_t':value(c,'Central Banks & Other inst.','Central Banks & Others','Central Banks')}
def gold_quarters():
 now=int(datetime.now(timezone.utc).timestamp())+86400;start=int(datetime(2016,1,1,tzinfo=timezone.utc).timestamp());q=urllib.parse.quote('GC=F',safe='');u=f'https://query1.finance.yahoo.com/v8/finance/chart/{q}?period1={start}&period2={now}&interval=1wk&events=history&includeAdjustedClose=true';j=json.loads(get(u,'application/json'));z=((j.get('chart') or {}).get('result') or [None])[0]
 if not z:raise RuntimeError('Yahoo history unavailable')
 box={}
 for ts,v in zip(z.get('timestamp') or [],(((z.get('indicators') or {}).get('quote') or [{}])[0].get('close') or [])):
  if v is None:continue
  d=datetime.fromtimestamp(ts,tz=timezone.utc);box.setdefault((d.year,(d.month-1)//3+1),[]).append(float(v))
 return {k:statistics.fmean(v) for k,v in box.items() if len(v)>=8},u
def feature(w):
 s=max(w['total_supply_t'],1.0);return [(w['bar_coin_t']+w['etf_t']+w['central_banks_t'])/s,w['recycled_gold_t']/s,(w.get('producer_hedging_t') or 0.0)/s]
def next_q(y,q):return (y+1,1) if q==4 else (y,q+1)
