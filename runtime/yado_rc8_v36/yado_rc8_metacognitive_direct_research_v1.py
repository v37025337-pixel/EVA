from __future__ import annotations
import asyncio,json,os
from pathlib import Path
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
URLS=[
 'https://arxiv.org/abs/2605.17292',
 'https://arxiv.org/abs/2601.15703',
 'https://arxiv.org/abs/2603.07670',
 'https://arxiv.org/abs/2603.14799',
]
MARKERS={
 'metacognition':['metacogn','self-assess','capability profile'],
 'uncertainty':['uncertainty','confidence','calibration'],
 'memory':['memory','retrieval','consolidat'],
 'routing':['routing','framework','delegat'],
 'feedback':['feedback','update','continual'],
}
def markers(text:str):
 low=text.lower();return {k:sum(low.count(w) for w in ws) for k,ws in MARKERS.items()}
async def main(out_path='yado_rc8_metacognitive_internet_receipt.json'):
 os.environ['YADO_ALLOWED_DOMAINS']='arxiv.org'
 k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=':memory:')
 try:
  rows=[]
  for url in URLS:
   e=await k.fetch_evidence(url,max_bytes=2_000_000,max_redirects=2)
   rows.append({'url':e['url'],'title':e['title'],'sha256':e['sha256'],'text_chars':len(e['text']),'redirect_hops':e['redirect_hops'],'markers':markers(e['text'])})
  receipt={'schema':'yado.rc8.metacognitive.internet.receipt.v1','status':'PASS_BOUNDED_DIRECT_METACOGNITIVE_RESEARCH','runtime_kind':'GITHUB_ACTIONS_EVENT_DRIVEN_PYTHON','direct_fetch_count':len(rows),'allowlisted_domains':['arxiv.org'],'sources':rows,'training_research':'yado_rc8_metacognitive_training_research_v1.json','semantic_boundary':'DIRECT_EVIDENCE_FETCH_PLUS_BOUNDED_NATIVE_REDERIVATION_NOT_FOUNDATION_WEIGHT_TRAINING','foundation_weights_modified':False,'background_daemon':False}
  Path(out_path).write_text(json.dumps(receipt,indent=2,sort_keys=True,ensure_ascii=False)+'\n')
  print(json.dumps(receipt,indent=2,ensure_ascii=False))
 finally:k.close()
if __name__=='__main__':asyncio.run(main())
