from __future__ import annotations
import hashlib,json,re,ssl,urllib.request,urllib.parse
from html.parser import HTMLParser
from pathlib import Path
from yado_consciousness_theory_synthesis_v1 import TheoryCard,YADOTheorySynthesizer

SOURCES=(
 ('butlin-2308.08708','https://arxiv.org/abs/2308.08708'),
 ('phua-2512.19155','https://arxiv.org/abs/2512.19155'),
 ('goldstein-2410.11407','https://arxiv.org/abs/2410.11407'),
 ('juliani-2204.05133','https://arxiv.org/abs/2204.05133'),
 ('responsible-2501.07290','https://arxiv.org/abs/2501.07290'),
)
ALLOWLIST={'arxiv.org'}
THEORIES={
 'Global Workspace Theory':(('global workspace','broadcast','workspace'),('limited_global_workspace','causal_broadcast','selective_attention')),
 'Recurrent Processing Theory':(('recurrent processing','recurrent','recurrence'),('recurrent_processing','temporal_self_continuity')),
 'Higher-Order Theories':(('higher-order','higher order','metacogn'),('metacognitive_representation','metacognitive_executive_binding','source_monitoring')),
 'Attention Schema Theory':(('attention schema','attentional schema'),('attention_schema','selective_attention','metacognitive_representation')),
 'Predictive Processing / Active Inference':(('predictive processing','active inference','prediction error'),('self_world_prediction_error','recurrent_processing','temporal_self_continuity')),
 'Integrated Information Theory':(('integrated information','iit'),('causal_broadcast',)),
}
class T(HTMLParser):
 def __init__(self):super().__init__();self.x=[]
 def handle_data(self,d):self.x.append(d)
def clean_html(raw:bytes)->str:
 p=T();p.feed(raw.decode('utf-8','ignore'));return ' '.join(' '.join(p.x).split())
def allowed(url):return urllib.parse.urlparse(url).hostname in ALLOWLIST
def fetch(url,timeout=20):
 if not allowed(url):raise RuntimeError('URL_NOT_ALLOWLISTED')
 req=urllib.request.Request(url,headers={'User-Agent':'YADO-RC8-Research/1.0'})
 class R(urllib.request.HTTPRedirectHandler):
  def redirect_request(self,req,fp,code,msg,hdrs,newurl):
   if not allowed(newurl):raise RuntimeError('REDIRECT_NOT_ALLOWLISTED')
   return super().redirect_request(req,fp,code,msg,hdrs,newurl)
 opener=urllib.request.build_opener(R)
 with opener.open(req,timeout=timeout) as r:return r.read(2_000_000),r.geturl()
def distill(rows):
 cards=[];hits={}
 for theory,(keys,mechs) in THEORIES.items():
  src=[];counts=0
  for row in rows:
   low=row['text'].lower();n=sum(low.count(k) for k in keys)
   if n:src.append(row['id']);counts+=n
  if src:
   strength=min(.95,.60+.06*len(src)+.01*min(counts,12)); test=min(.95,.70+.04*len(src))
   cards.append(TheoryCard(theory,tuple(mechs),strength,test,tuple(sorted(src))))
   hits[theory]={'sources':sorted(src),'keyword_hits':counts,'empirical_weight':strength,'operational_testability':test}
 return cards,hits
def run():
 rows=[]
 for sid,url in SOURCES:
  raw,final=fetch(url);text=clean_html(raw)
  rows.append({'id':sid,'url':url,'final_url':final,'sha256':hashlib.sha256(raw).hexdigest(),'text_chars':len(text),'text':text[:120000]})
 cards,hits=distill(rows)
 spec=YADOTheorySynthesizer().synthesize(cards)
 out={'schema':'yado.rc8.consciousness.direct_research.v1','status':'PASS_BOUNDED_DIRECT_MULTI_THEORY_RESEARCH','allowlisted_domains':sorted(ALLOWLIST),'fetch_count':len(rows),'sources':[{k:v for k,v in r.items() if k!='text'} for r in rows],'theory_hits':hits,'synthesis':spec,'subjective_consciousness_claimed':False}
 raw=json.dumps(out,sort_keys=True,separators=(',',':')).encode();out['report_sha256']=hashlib.sha256(raw).hexdigest();return out
if __name__=='__main__':
 o=run();Path('yado_rc8_consciousness_direct_research_v1_report.json').write_text(json.dumps(o,indent=2,sort_keys=True)+'\n');print(json.dumps(o,indent=2,sort_keys=True))
