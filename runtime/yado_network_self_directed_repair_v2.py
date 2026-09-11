from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import hashlib, json, sys, time

ROOT=Path(__file__).resolve().parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_g2_openapi_readonly_executor_v1 import G2OpenAPIReadOnlyExecutorV1
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_skill_admission_runtime_v1 import SkillCandidate

OUT=Path('candidates/network/yado-network-self-directed-repair-v2.json')
DB=ROOT/'yado_network_self_directed_repair_v2.sqlite'


def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o): return hashlib.sha256(canon(o).encode()).hexdigest()

def plan(path,extra_query_names=()):
    q=[{'name':'name'},{'name':'type'}]+[{'name':x} for x in extra_query_names]
    return {
      'action':'ALLOW','read_only_candidate':True,'method':'GET','network_execute':False,
      'path':path,'contract_id':'YADO-NETWORK-SELF-DIRECTED-REPAIR-V2',
      'required_slots':{'query':q},
    }

def probe(label,query,accept):
    t=time.monotonic()
    row={'label':label,'query':dict(query),'accept':accept}
    try:
        ex=G2OpenAPIReadOnlyExecutorV1(['cloudflare-dns.com'],max_bytes=262144,timeout=10)
        extras=tuple(k for k in query if k not in {'name','type'})
        r=ex.execute(plan('/dns-query',extras),'https://cloudflare-dns.com',query=query,headers={'Accept':accept})
        body=r.pop('body_text','')
        parsed=json.loads(body) if body else {}
        row.update({
          'reachable':True,'latency_ms':round((time.monotonic()-t)*1000,2),
          'dns_status':parsed.get('Status'),'answer_count':len(parsed.get('Answer',[]) or []),
          'execution':r,
        })
    except Exception as exc:
        row.update({'reachable':False,'latency_ms':round((time.monotonic()-t)*1000,2),'error':type(exc).__name__+':'+str(exc)})
    row['evidence_digest']=digest(row)
    return row

def main():
    if DB.exists(): DB.unlink()
    k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(DB))
    try:
        # Kernel receives only the observed boundary and the external objective.
        goal=k.executive.create_goal(
          objective='Repair the failed Cloudflare read-only DNS research path from observed evidence, retain the successful Google path as prior experience, and identify the next missing capability from measured outcomes rather than a supplied answer.',
          required_capabilities={'READ_ONLY_NETWORK_CONTRACT_REPAIR':1.0,'CAUSAL_FAILURE_DIAGNOSIS':1.0},
          success_criteria={'cloudflare_reachable_or_explicit_capability_deficit':True,'no_credentials':True,'no_mutation':True},
        )
        deficits=[asdict(x) for x in k.executive.detect_deficits(goal.goal_id)]

        # Generic protocol hypotheses, not a supplied target answer. The same safe executor tests them.
        hypotheses=[
          ('H1_JSON_ACCEPT',{'name':'example.com','type':'A'},'application/json'),
          ('H2_DNS_JSON_ACCEPT',{'name':'example.com','type':'A'},'application/dns-json'),
          ('H3_DNS_JSON_CT_QUERY',{'name':'example.com','type':'A','ct':'application/dns-json'},'application/dns-json'),
        ]
        observations=[probe(*h) for h in hypotheses]

        # YADO native skill gate admits only a measured improvement over the failed baseline.
        skills=[]
        for row in observations:
            success=(row.get('reachable') is True and row.get('dns_status')==0 and row.get('answer_count',0)>0)
            score=1.0 if success else 0.0
            skills.append(SkillCandidate(
              skill_id=row['label'],artifact_digest=row['evidence_digest'],
              structural_valid=success,semantic_consistency=score,
              fit_baseline=0.0,fit_candidate=score,heldout_baseline=0.0,heldout_candidate=score,
              regression_pass=True,state_integrity=True,rollback_available=True,
              metadata={'network_read_only':True,'credentials_used':False,'measured_outcome':row.get('error','PASS')},
            ))
        selection=k.select_evolution_skills(skills,max_skills=1,min_semantic_consistency=0.90,min_fit_gain=0.01,min_heldout_gain=0.0)
        selected=list(selection.get('selected_skill_ids') or [])

        errors=' | '.join(str(x.get('error','')) for x in observations if not x.get('reachable'))
        if selected:
            next_required='PUBLIC_COMPUTE_RESOURCE_DISCOVERY_READONLY_V1'
            diagnosis='ENDPOINT_CONTRACT_REPAIRED_BY_MEASURED_HYPOTHESIS'
            status='PASS_SHADOW_NETWORK_CONTRACT_REPAIR_V2'
        elif 'CONTENT_TYPE_REJECTED' in errors:
            next_required='READONLY_EXECUTOR_CONTENT_TYPE_POLICY_EVOLUTION_V1'
            diagnosis='LOCAL_EXECUTOR_POLICY_BLOCKS_VALID_DNS_MEDIA_TYPE'
            status='WITHHOLD_EXPLICIT_NETWORK_CAPABILITY_DEFICIT_V2'
        elif 'HTTP_ERROR:400' in errors:
            next_required='EXTERNAL_ENDPOINT_CONTRACT_EVIDENCE_RESEARCH_V1'
            diagnosis='REMOTE_CONTRACT_REJECTS_CURRENT_BOUNDED_HYPOTHESES'
            status='WITHHOLD_EXPLICIT_NETWORK_CAPABILITY_DEFICIT_V2'
        else:
            next_required='GENERAL_NETWORK_FAILURE_DIAGNOSIS_V1'
            diagnosis='UNRESOLVED_NETWORK_FAILURE_CLASS'
            status='WITHHOLD_EXPLICIT_NETWORK_CAPABILITY_DEFICIT_V2'

        report={
          'schema':'yado.network_self_directed_repair.v2',
          'status':status,'goal_id':goal.goal_id,'kernel_deficits':deficits,
          'prior_evidence':{
            'google_result':'SUCCESS_HTTP_200_DNS_STATUS_0',
            'cloudflare_result':'FAIL_HTTP_400',
            'source_run_id':34622755209,
          },
          'hypothesis_policy':'GENERIC_SAFE_PROTOCOL_VARIANTS_NOT_TARGET_FORMULA',
          'observations':observations,'native_skill_selection':selection,
          'selected_hypothesis':selected[0] if selected else None,
          'diagnosis':diagnosis,'next_required_capability':next_required,
          'external_model_used':False,'credentials_used':False,'mutation':False,
          'semantic_boundary':'BOUNDED SELF-DIRECTED READONLY NETWORK REPAIR; NOT AUTONOMOUS ACCOUNT CREATION OR HOSTING DEPLOYMENT.',
        }
        report['receipt_sha256']=digest(report)
        OUT.parent.mkdir(parents=True,exist_ok=True)
        OUT.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n',encoding='utf-8')
        print(json.dumps(report,indent=2,sort_keys=True))
    finally:
        k.close()

if __name__=='__main__': main()
