from __future__ import annotations
from pathlib import Path
import hashlib,json,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_unified_core_v1 import UnifiedYADOCoreV1

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def rejected(fn):
    try:fn();return False
    except Exception:return True

core=UnifiedYADOCoreV1(REPO)
state={
 'policy_tree':{'label':'ALLOW'},
 'contract_registry':{
   'GET_BRANCH':{'source_id':'GITHUB_PUBLIC_API','source_sha':'post-admission-v1','method':'GET','path':'/repos/v37025337-pixel/EVA/branches/yado-architecture-shadow-search','required':[],'redirect_semantic':False},
   'POST_BLOCK':{'source_id':'GITHUB_PUBLIC_API','source_sha':'post-negative-v1','method':'POST','path':'/repos/v37025337-pixel/EVA/issues','required':[],'redirect_semantic':False},
 }
}
plan=core.compile_openapi_contract_plan(state,'GET_BRANCH')
out=core.execute_openapi_readonly_plan(plan,'https://api.github.com',['api.github.com'],max_bytes=512*1024,timeout=10)
body=json.loads(out.get('body_text','{}'))
post=core.compile_openapi_contract_plan(state,'POST_BLOCK')
checks={
 'core_entrypoint_present':hasattr(core,'execute_openapi_readonly_plan'),
 'branch_get_200':out.get('status')==200 and out.get('network_executed') is True,
 'branch_identity':body.get('name')=='yado-architecture-shadow-search',
 'read_only_enforced':out.get('read_only_enforced') is True and out.get('credentials_used') is False,
 'redirects_zero':out.get('redirects_followed') is False,
 'write_plan_rejected':rejected(lambda:core.execute_openapi_readonly_plan(post,'https://api.github.com',['api.github.com'])),
 'frontier_preserved':core.head.get('current_frontier')=='KERNEL_G2_RAW_REPRESENTATION_V5_CANONICAL_ADMISSION_V1',
 'g3_not_started':core.head.get('g3_genesis_performed') is False,
}
status='PASS_G2_OPENAPI_READONLY_EXECUTOR_POST_ADMISSION_V1' if all(checks.values()) else 'WITHHOLD_G2_OPENAPI_READONLY_EXECUTOR_POST_ADMISSION_V1'
report={
 'schema':'yado.g2.openapi_readonly_executor.post_admission.v1','status':status,
 'checks':checks,'live_evidence':{k:v for k,v in out.items() if k!='body_text'},
 'body_projection':{'name':body.get('name'),'protected':body.get('protected'),'commit_sha':body.get('commit',{}).get('sha')},
 'canonical_mutation':False,'architecture_mutation':False,'generation_transition':False,'g3_genesis_performed':False,
 'semantic_boundary':'POST-ADMISSION LIVE VERIFICATION THROUGH UnifiedYADOCoreV1. GET/HEAD ONLY, NO CREDENTIALS, NO REDIRECTS.'
}
report['receipt_sha256']=digest(report)
outp=REPO/'audits/yado-g2-openapi-readonly-executor-post-admission-v1.json'
outp.parent.mkdir(parents=True,exist_ok=True);outp.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps(report,indent=2,sort_keys=True,default=str))
if not all(checks.values()):raise SystemExit(2)
