from __future__ import annotations
import html,json,re,statistics,urllib.parse,urllib.request
from datetime import datetime,timezone
from html.parser import HTMLParser
UA='Mozilla/5.0 GoldEquilibriumPrice/3.3'
def get(u,accept='text/html,*/*'):
 r=urllib.request.Request(u,headers={'User-Agent':UA,'Accept':accept})
 with urllib.request.urlopen(r,timeout=45) as x:return x.read().decode('utf-8',errors='replace')
class Tables(HTMLParser):
 def __init__(self):super().__init__(convert_charrefs=True);self.tables=[];self.t=None;self.r=None;self.cell=False;self.parts=[]
 def handle_starttag(self,tag,attrs):
  tag=tag.lower()
  if tag=='table':self.t=[]
  elif tag=='tr' and self.t is not None:self.r=[]
  elif tag in ('td','th') and self.r is not None:self.cell=True;self.parts=[]
 def handle_data(self,data):
  if self.cell:self.parts.append(data)
 def handle_endtag(self,tag):
  tag=tag.lower()
  if tag in ('td','th') and self.cell:
   s=re.sub(r'\s+',' ',html.unescape(' '.join(self.parts)).replace('\u00a0',' ')).strip();self.r.append(s);self.cell=False
  elif tag=='tr' and self.r is not None:
   if self.r:self.t.append(self.r)
   self.r=None
  elif tag=='table' and self.t is not None:
   if self.t:self.tables.append(self.t)
   self.t=None
def norm(s):return re.sub(r'[^a-z0-9]+',' ',html.unescape(s or '').lower()).strip()
def num(s):
 m=re.search(r'-?\d[\d,]*(?:\.\d+)?',(s or '').replace('−','-').replace('–','-'))
 return float(m.group().replace(',','')) if m else None
def parse_tables(u):p=Tables();p.feed(get(u));return p.tables
def target_col(table,y,q):
 yy=str(y)[-2:];marks=[norm(f'Q{q} {y}'),norm(f'Q{q}\'{yy}')]
 for row in table[:7]:
  for j,c in enumerate(row):
   nc=norm(c)
   if any(m==nc or m in nc for m in marks):return j
 return None
def row_value(tables,y,q,*labels,required=True):
 labs=[norm(x) for x in labels]
 for table in tables:
  j=target_col(table,y,q)
  if j is None:continue
  for row in table:
   if not row:continue
   r0=norm(row[0])
   if any(l==r0 or l in r0 for l in labs):
    if j<len(row):
     v=num(row[j])
     if v is not None:return v
 if required:raise RuntimeError('missing '+labels[0])
 return 0.0
def wgc_quarter(y,q):
 b=f'https://www.gold.org/goldhub/research/gold-demand-trends/gold-demand-trends-q{q}-{y}'
 supply=parse_tables(b+'/supply');invest=parse_tables(b+'/investment')
 try:central=parse_tables(b+'/central-banks')
 except Exception:central=parse_tables(b+'/central-banks-and-other-institutions')
 return {'total_supply_t':row_value(supply,y,q,'Total Supply'),'recycled_gold_t':row_value(supply,y,q,'Recycled Gold','Recycling'),'producer_hedging_t':row_value(supply,y,q,'Net Producer Hedging','Producer Hedging',required=False),'bar_coin_t':row_value(invest,y,q,'Total Bar and Coin Demand','Total Bar & Coin Demand','Bar and Coin'),'etf_t':row_value(invest,y,q,'ETFs & Similar Products','ETFs and Similar Products','Gold-backed ETFs','ETFs'),'central_banks_t':row_value(central,y,q,'Central Banks & Others','Central Banks and Other Institutions','Central Banks')}
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
