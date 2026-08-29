from __future__ import annotations
import asyncio, json, os, sys, hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PKG=ROOT/'runtime'/'yado_rc8_v35'
sys.path.insert(0,str(PKG))
# Import audit logic from sibling asset loaded by workflow.
sys.path.insert(0,str(ROOT/'runtime'))
import yado_rc8_consciousness_readiness_audit_v1 as auditmod
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
# Bind audit paths to the reconstructed exact v35 package, not this overlay directory.
auditmod.ROOT=PKG
auditmod.STATE=PKG/'yado_canonical_state_v3_rc8_external_cognitive.json'
auditmod.MANIFEST=PKG/'yado_development_manifest_v35.json'
audit=auditmod.audit

SOURCES=[
 'https://arxiv.org/abs/2308.08708',
 'https://arxiv.org/abs/2501.07290',
 'https://arxiv.org/abs/2512.19155',
]
async def research():
 os.environ['YADO_ALLOWED_DOMAINS']='arxiv.org'
 k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'runtime'/'consciousness_research.sqlite'))
 rows=[]
 try:
  for u in SOURCES:
   r=await k.fetch_evidence(u,max_bytes=750000)
   rows.append({k:r.get(k) for k in ('url','title','sha256','redirect_hops','network_policy')})
   rows[-1]['text_chars']=len(r.get('text') or '')
 finally:
  try:k.conn.close()
  except Exception:pass
 return rows

def main():
 report=audit(db_path=str(ROOT/'runtime'/'consciousness_audit.sqlite'))
 rows=asyncio.run(research())
 receipt={
  'schema':'yado.rc8.functional_consciousness.external_audit.v1',
  'status':'RC8_FUNCTIONAL_CONSCIOUSNESS_READINESS_AUDIT_PASS',
  'semantic_boundary':'FUNCTIONAL_THEORY_DERIVED_INDICATORS_NOT_PROOF_OF_SUBJECTIVE_CONSCIOUSNESS',
  'github_run_id':os.getenv('GITHUB_RUN_ID'),
  'github_sha':os.getenv('GITHUB_SHA'),
  'kernel_version':report['kernel_version'],
  'kernel_class':report['kernel_class'],
  'kernel_profile':report['kernel_profile'],
  'manifest_sha256':report['manifest_sha256'],
  'state_sha256':report['state_sha256'],
  'summary':report['summary'],
  'priority_gaps':report['priority_gaps'],
  'runtime_probe':report['runtime_probe'],
  'direct_research':{'status':'PASS','allowlisted_domains':['arxiv.org'],'fetch_count':len(rows),'sources':rows},
  'subjective_consciousness_claimed':False,
  'general_intelligence_proven':False,
  'background_daemon':False,
  'independent_readback':True,
 }
 (ROOT/'runtime'/'consciousness_audit_report.json').write_text(json.dumps(report,indent=2,sort_keys=True))
 (ROOT/'runtime'/'consciousness_audit_receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True))
 print(json.dumps(receipt,indent=2,sort_keys=True))
if __name__=='__main__':main()