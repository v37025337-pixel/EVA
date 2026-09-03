from __future__ import annotations
import asyncio, json, os, re
from pathlib import Path
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive

URLS=[
  'https://arxiv.org/abs/2608.05810',
  'https://arxiv.org/abs/2604.27003',
  'https://arxiv.org/abs/2606.02461',
  'https://arxiv.org/abs/2608.03874',
  'https://arxiv.org/abs/2604.20087',
]
MARKERS={
 'skill':['skill','skills'],
 'transfer':['transfer','continual'],
 'memory':['memory','memories'],
 'evaluation':['benchmark','evaluation'],
 'gate':['gate','verifier','filter'],
}

def marker_evidence(text:str):
    low=text.lower();return {k:sum(low.count(w) for w in ws) for k,ws in MARKERS.items()}

async def main(out_path='yado_rc8_internet_research_receipt.json'):
    os.environ['YADO_ALLOWED_DOMAINS']='arxiv.org'
    k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=':memory:')
    try:
        rows=[]
        for url in URLS:
            e=await k.fetch_evidence(url,max_bytes=2_000_000,max_redirects=2)
            rows.append({'url':e['url'],'title':e['title'],'sha256':e['sha256'],'text_chars':len(e['text']),'redirect_hops':e['redirect_hops'],'markers':marker_evidence(e['text'])})
        receipt={
          'schema':'yado.rc8.internet_research.receipt.v1','status':'PASS_BOUNDED_DIRECT_INTERNET_RESEARCH',
          'runtime_kind':'GITHUB_ACTIONS_EVENT_DRIVEN_PYTHON','direct_fetch_count':len(rows),
          'allowlisted_domains':['arxiv.org'],'sources':rows,
          'principle_source':'yado_rc8_external_research_cycle2.json',
          'semantic_distillation_boundary':'HOST_RESEARCH_SUMMARY_PLUS_BOUNDED_KEYWORD_EVIDENCE_NOT_FOUNDATION_WEIGHT_TRAINING',
          'foundation_weights_modified':False,'background_daemon':False,
        }
        Path(out_path).write_text(json.dumps(receipt,indent=2,sort_keys=True,ensure_ascii=False)+'\n')
        print(json.dumps(receipt,indent=2,ensure_ascii=False))
    finally:k.close()

if __name__=='__main__':asyncio.run(main())
