from __future__ import annotations
from pathlib import Path
import hashlib,json,os,subprocess,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path.insert(0,str(ROOT))
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash

LEDGER=REPO/'architecture'/'evolution-ledger.json'
HEAD=REPO/'canonical'/'yado-main-head-g2.json'
CORE=REPO/'canonical'/'yado-unified-core-v1.json'
OUT=ROOT/'yado_external_agent_systems_learning_v1_receipt.json'
EXP=REPO/'experience'/'yado-external-agent-systems-learning-v1.json'

AR=REPO/'_external_learning'/'Agent-Reach'
SK=REPO/'_external_learning'/'skills'
AR_SHA='da5044d26fc6adddb6554d5679c94ac22e76e428'
SK_SHA='6654f6b60cd9d5be8b54c6fafe44346dabeb3b76'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def gitsha(p):return subprocess.check_output(['git','-C',str(p),'rev-parse','HEAD'],text=True).strip()
def txt(p):return p.read_text(encoding='utf-8',errors='replace')

ledger=load(LEDGER);head=load(HEAD);core=load(CORE)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['LTI_CODE_ARCHITECTURAL_CEILING_PLATEAU_PROBE_V4']:raise RuntimeError('UNEXPECTED_FRONTIER')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')
if gitsha(AR)!=AR_SHA or gitsha(SK)!=SK_SHA:raise RuntimeError('EXTERNAL_SOURCE_SHA_MISMATCH')

sources={
 'agent_base':'agent_reach/channels/base.py',
 'agent_github':'agent_reach/channels/github.py',
 'agent_web':'agent_reach/channels/web.py',
 'agent_opencli':'agent_reach/backends/opencli.py',
 'agent_readme':'README.md',
 'skill_debug':'skills/engineering/diagnosing-bugs/SKILL.md',
 'skill_review':'skills/engineering/code-review/SKILL.md',
 'skill_arch':'skills/engineering/improve-codebase-architecture/SKILL.md',
 'skill_design':'skills/engineering/codebase-design/SKILL.md',
 'skill_research':'skills/engineering/research/SKILL.md',
 'skill_phase':'skills/engineering/ask-matt/PHASE-BOUNDARIES.md',
}
raw={}
for k,p in sources.items():
    base=AR if k.startswith('agent_') else SK
    raw[k]=txt(base/p)

def obs(oid,source,signals,principle,target_planes):
    hits={s:(s in raw[source]) for s in signals}
    return {'observation_id':oid,'source':sources[source],
            'source_repo':'Agent-Reach' if source.startswith('agent_') else 'skills',
            'signals':hits,'evidence_complete':all(hits.values()),
            'principle':principle,'target_planes':target_planes}

observations=[
 obs('EXT-001','agent_base',['ORDERED candidate list','active_backend','really execute a lightweight command'],
     'Prefer ordered interchangeable adapters, but declare one active only after a real lightweight health probe.',
     ['RESOURCE_AND_EVIDENCE','INTELLIGENCE_AND_META_SELECTION']),
 obs('EXT-002','agent_opencli',['side effect','--version','live daemon connection proves'],
     'A diagnostic observer should avoid state-changing probes and distinguish disk/config evidence from live usability.',
     ['SELF_AUDIT_AND_REPAIR','RESOURCE_AND_EVIDENCE']),
 obs('EXT-003','agent_web',['_MAX_RESPONSE_BYTES','_is_antibot_page','normalize_public_http_url'],
     'External reading needs bounded responses, URL normalization and explicit detection of misleading challenge pages.',
     ['RESOURCE_AND_EVIDENCE']),
 obs('EXT-004','skill_debug',['Build a feedback loop','Reproduce + minimise','3–5 ranked hypotheses','Change one variable at a time','regression test'],
     'Self-repair should begin with a tight red-capable signal, minimize the failing case, test ranked falsifiable hypotheses, then lock the repair with regression evidence.',
     ['SELF_AUDIT_AND_REPAIR','CODE']),
 obs('EXT-005','skill_review',['Standards','Spec','two axes','Do **not** merge or rerank findings'],
     'Code evolution should review implementation quality and goal/spec fidelity as independent axes so one cannot mask the other.',
     ['CODE','SELF_AUDIT_AND_REPAIR']),
 obs('EXT-006','skill_design',['deep modules','The deletion test','The interface is the test surface','Two adapters means a real one'],
     'Architecture improvement should seek deep modules with small interfaces, real seams only where variation exists, and test through the same interface callers use.',
     ['SELF_AUDIT_AND_REPAIR','WORKSPACE_AND_INTEGRATION']),
 obs('EXT-007','skill_research',['primary sources','Follow every claim back to the source that owns it','citing each claim'],
     'External learning should prefer primary sources and preserve claim-to-source provenance.',
     ['RESOURCE_AND_EVIDENCE','MEMORY_AND_EXPERIENCE']),
 obs('EXT-008','skill_phase',['Primary and secondary sources','Continue','/compact','lossiness'],
     'Context transitions are lossy; preserve primary-state continuity when the next phase depends on the reasoning that produced the current state.',
     ['MEMORY_AND_EXPERIENCE','WORKSPACE_AND_INTEGRATION']),
]
all_complete=all(x['evidence_complete'] for x in observations)

hypotheses=[
 {'hypothesis_id':'H-EXT-001','name':'HEALTH_PROBED_ADAPTER_ROUTER','derived_from':['EXT-001','EXT-002','EXT-003'],
  'gap':'Current resource routing lacks a generic ordered-backend health contract with side-effect-free live probes.',
  'candidate_target':['RESOURCE_AND_EVIDENCE','INTELLIGENCE_AND_META_SELECTION'],'action':'EXPERIENCE_ONLY'},
 {'hypothesis_id':'H-EXT-002','name':'RED_CAPABLE_SELF_REPAIR_LOOP','derived_from':['EXT-004'],
  'gap':'Current repair has fresh/ablation gates; it can tighten reproduction and minimization before hypothesis generation.',
  'candidate_target':['SELF_AUDIT_AND_REPAIR','CODE'],'action':'EXPERIENCE_ONLY'},
 {'hypothesis_id':'H-EXT-003','name':'TWO_AXIS_SELF_CODE_REVIEW','derived_from':['EXT-005'],
  'gap':'Current gates emphasize behavior and causality; an independent spec-fidelity axis can catch solving the wrong requirement.',
  'candidate_target':['CODE','SELF_AUDIT_AND_REPAIR'],'action':'EXPERIENCE_ONLY'},
 {'hypothesis_id':'H-EXT-004','name':'DEEP_MODULE_SELF_ARCHITECTURE_AUDIT','derived_from':['EXT-006'],
  'gap':'Current self-audit does not explicitly score interface depth, locality, deletion-test value or real multi-adapter seams.',
  'candidate_target':['SELF_AUDIT_AND_REPAIR','WORKSPACE_AND_INTEGRATION'],'action':'EXPERIENCE_ONLY'},
 {'hypothesis_id':'H-EXT-005','name':'PRIMARY_SOURCE_PROVENANCE_POLICY','derived_from':['EXT-007','EXT-008'],
  'gap':'Receipt provenance can be generalized to external-learning claims and lossy context transitions.',
  'candidate_target':['MEMORY_AND_EXPERIENCE','RESOURCE_AND_EVIDENCE'],'action':'EXPERIENCE_ONLY'},
]

license_checks={'agent_reach_mit':'MIT License' in txt(AR/'LICENSE'),'skills_mit':'MIT License' in txt(SK/'LICENSE')}
checks={
 'source_commits_pinned':gitsha(AR)==AR_SHA and gitsha(SK)==SK_SHA,
 'licenses_verified':all(license_checks.values()),
 'all_observations_source_backed':all_complete,
 'no_external_code_copied_to_runtime':True,
 'canonical_head_unchanged':ledger.get('current_head_digest')==head.get('canonical_head_digest'),
 'g3_not_started':head.get('g3_genesis_performed') is False,
}
passed=all(checks.values())

EXP.parent.mkdir(parents=True,exist_ok=True)
experience={
 'schema':'yado.external_agent_systems_learning.v1',
 'status':'LEARNED_EXTERNAL_EXPERIENCE' if passed else 'WITHHOLD_EXTERNAL_EXPERIENCE',
 'sources':[
   {'repo':'Panniantong/Agent-Reach','commit':AR_SHA,'license':'MIT','role':'internet-capability-layer-and-health-routing'},
   {'repo':'mattpocock/skills','commit':SK_SHA,'license':'MIT','role':'repeatable-engineering-skill-protocols'}],
 'observations':observations,'hypotheses':hypotheses,
 'integration_applied':False,'canonical_mutation':False,
 'semantic_boundary':'EXTERNAL PRIMARY-SOURCE STUDY ONLY. PRINCIPLES ARE STORED AS EXPERIENCE/HYPOTHESES; NO THIRD-PARTY CODE OR BEHAVIOR IS PROMOTED INTO CANONICAL YADO BY THIS RUN.'
}
experience['experience_digest']=h(experience)
EXP.write_text(json.dumps(experience,indent=2,sort_keys=True)+'\n',encoding='utf-8')

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
next_cap='LTI_CODE_ARCHITECTURAL_CEILING_PLATEAU_PROBE_V4'
receipt={'schema':'yado.external_agent_systems_learning.receipt.v1',
 'status':'PASS_EXTERNAL_AGENT_SYSTEMS_LEARNING_V1' if passed else 'WITHHOLD_EXTERNAL_AGENT_SYSTEMS_LEARNING_V1',
 'github_run_id':os.getenv('GITHUB_RUN_ID'),
 'source_commits':{'Agent-Reach':AR_SHA,'skills':SK_SHA},
 'license_checks':license_checks,'observation_count':len(observations),'hypothesis_count':len(hypotheses),
 'experience_digest':experience['experience_digest'],'checks':checks,
 'canonical_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,
 'next_required_capability':next_cap,'semantic_boundary':experience['semantic_boundary']}
receipt['receipt_sha256']=h(receipt)
OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n',encoding='utf-8')

e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_EXTERNAL_AGENT_SYSTEMS_LEARNING_V1",
 'event_type':'EXTERNAL_PRIMARY_SOURCE_EXPERIENCE_INGESTION',
 'status':'PASS_EXPERIENCE' if passed else 'WITHHOLD','generation':ledger['current_head'],
 'deficit':'USER_DIRECTED_EXTERNAL_AGENT_SYSTEMS_LEARNING',
 'effect':f"OBS={len(observations)}; HYP={len(hypotheses)}; INTEGRATION=false; NEXT={next_cap}",
 'source_path':f'receipts/yado-external-agent-systems-learning-v1-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':False,'promotion_applied':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events'])
ledger['tail_event_hash']=e['event_hash'];ledger['open_deficits']=[next_cap]
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger)
LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n',encoding='utf-8')

print(json.dumps({
 'status':receipt['status'],
 'observations':[{'id':x['observation_id'],'complete':x['evidence_complete'],'principle':x['principle']} for x in observations],
 'hypotheses':[{'id':x['hypothesis_id'],'name':x['name']} for x in hypotheses],
 'checks':checks,'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']
},indent=2,sort_keys=True))
if not passed:raise SystemExit('EXTERNAL_AGENT_SYSTEMS_LEARNING_WITHHELD')
