from __future__ import annotations
from pathlib import Path
import hashlib,json,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_g2_openapi_contract_capability_v1 import G2OpenAPIContractCapabilityV1
from yado_g2_openapi_readonly_executor_v1 import G2OpenAPIReadOnlyExecutorV1

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()

state={
 'policy_tree':{'label':'ALLOW'},
 'contract_registry':{
   'GET_REPO':{'source_id':'GITHUB_PUBLIC_API','source_sha':'fresh-live-v1','method':'GET','path':'/repos/v37025337-pixel/EVA','required':[],'redirect_semantic':False},
   'POST_REPO':{'source_id':'GITHUB_PUBLIC_API','source_sha':'negative-v1','method':'POST','path':'/repos/v37025337-pixel/EVA/issues','required':[],'redirect_semantic':False},
 }
}
cap=G2OpenAPIContractCapabilityV1(state)
get_plan=cap.compile_plan('GET_REPO')
post_plan=cap.compile_plan('POST_REPO')
executor=G2OpenAPIReadOnlyExecutorV1(['api.github.com'],max_bytes=512*1024,timeout=10)
live=executor.execute(get_plan,'https://api.github.com')
body=json.loads(live.get('body_text','{}'))

def rejected(fn):
    try:fn();return False
    except Exception:return True

checks={
 'planner_get_allowed':get_plan.get('action')=='ALLOW' and get_plan.get('read_only_candidate') is True and get_plan.get('network_execute') is False,
 'live_network_executed':live.get('network_executed') is True and live.get('status')==200,
 'live_repo_identity':body.get('full_name')=='v37025337-pixel/EVA',
 'live_response_bounded':0<live.get('response_bytes',0)<=512*1024,
 'live_no_credentials':live.get('credentials_used') is False,
 'live_no_redirects':live.get('redirects_followed') is False,
 'post_rejected':rejected(lambda:executor.execute(post_plan,'https://api.github.com')),
 'host_not_allowlisted_rejected':rejected(lambda:executor.execute(get_plan,'https://example.com')),
 'http_rejected':rejected(lambda:executor.execute(get_plan,'http://api.github.com')),
 'credential_header_rejected':rejected(lambda:executor.execute(get_plan,'https://api.github.com',headers={'Authorization':'Bearer forbidden'})),
 'undeclared_query_rejected':rejected(lambda:executor.execute(get_plan,'https://api.github.com',query={'x':'1'})),
 'private_ip_rejected':rejected(lambda:G2OpenAPIReadOnlyExecutorV1(['127.0.0.1']).execute({'action':'ALLOW','read_only_candidate':True,'network_execute':False,'method':'GET','path':'/','required_slots':{'query':[]},'contract_id':'PRIVATE'},'https://127.0.0.1')),
}
status='PASS_SHADOW_G2_OPENAPI_READONLY_EXECUTOR_V1' if all(checks.values()) else 'WITHHOLD_G2_OPENAPI_READONLY_EXECUTOR_V1'
report={
 'schema':'yado.g2.openapi_readonly_executor.fresh_gate.v1','status':status,
 'checks':checks,'component':G2OpenAPIReadOnlyExecutorV1.component(),
 'live_evidence':{k:v for k,v in live.items() if k!='body_text'},
 'live_body_projection':{'full_name':body.get('full_name'),'private':body.get('private'),'archived':body.get('archived'),'default_branch':body.get('default_branch')},
 'network_target':'api.github.com','credential_source':'NONE','canonical_mutation':False,
 'architecture_mutation':False,'generation_transition':False,'g3_genesis_performed':False,
 'semantic_boundary':'FRESH LIVE SHADOW GATE. REAL NETWORK I/O IS LIMITED TO PUBLIC HTTPS GET/HEAD ON AN EXPLICIT HOST ALLOWLIST, WITH NO CREDENTIALS AND NO REDIRECTS.'
}
report['receipt_sha256']=digest(report)
out=REPO/'candidates/kernel-self-generated/g2-openapi-readonly-executor-v1.json'
out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({'status':status,'checks':checks,'live_evidence':report['live_evidence'],'receipt_sha256':report['receipt_sha256']},indent=2,sort_keys=True,default=str))
if not all(checks.values()):raise SystemExit(2)
