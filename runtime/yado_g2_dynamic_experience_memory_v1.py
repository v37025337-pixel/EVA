from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,subprocess

REPO=Path(__file__).resolve().parents[1]
REG=REPO/'canonical/yado-unified-experience-registry-v1.json'
REQ=REPO/'architecture/yado-g2-dynamic-experience-memory-v1-request.json'
OUT=REPO/'experience/yado-g2-dynamic-experience-memory-v1.json'
REDERIVED=REPO/'experience/yado-g2-raw-branch-evidence-rederivation-v1.json'

def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o): return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))

def remote_refs():
    cp=subprocess.run(['git','ls-remote','--heads','origin'],cwd=REPO,capture_output=True,text=True,timeout=30)
    if cp.returncode!=0:
        raise RuntimeError('REMOTE_BRANCH_QUERY_FAILED:'+cp.stderr[-300:])
    refs={}
    for line in cp.stdout.splitlines():
        parts=line.split()
        if len(parts)==2 and parts[1].startswith('refs/heads/'):
            refs[parts[1][len('refs/heads/'):]]=parts[0]
    if not refs:
        raise RuntimeError('NO_REMOTE_BRANCH_REFS')
    return refs

def classify_registered(entry):
    lp=entry.get('lesson_provenance') or {}
    rd=entry.get('rederived_evidence') or {}
    source=lp.get('source_class')
    if source=='YADO_REDERIVED_FROM_CURRENT_REACHABLE_GIT_HISTORY':
        return 'REGISTERED_REDERIVED_EXPERIENCE'
    if source=='HOST_CURATED_REGISTRY_SUMMARY':
        return 'REGISTERED_CURATED_SUMMARY_WITH_REDERIVED_OBSERVATIONS'
    if entry.get('mode')=='ACTIVE_LINEAGE':
        return 'ACTIVE_LINEAGE_STATE'
    return 'REGISTERED_METADATA_ONLY'

def build():
    req=load(REQ)
    reg=load(REG)
    refs=remote_refs()
    rederived=load(REDERIVED) if REDERIVED.exists() else {}
    rederived_by_branch={x.get('branch'):x for x in rederived.get('observations',[]) if x.get('branch')} if rederived.get('status')=='PASS_SHADOW_G2_RAW_BRANCH_EVIDENCE_REDERIVATION_V1' else {}
    active=req.get('active_branch') or reg.get('policy',{}).get('active_branch')
    registered={x.get('branch'):x for x in reg.get('branches',[]) if x.get('branch')}
    rows=[]
    for name in sorted(refs):
        tip=refs[name]
        if name in registered:
            src=copy.deepcopy(registered[name])
            row={
              'branch':name,
              'observed_tip':tip,
              'mode':'ACTIVE_LINEAGE' if name==active else 'EXPERIENCE_ONLY',
              'inventory_class':classify_registered(src),
              'registered':True,
              'registry_head_sha':src.get('head_sha'),
              'role':src.get('role'),
              'tags':src.get('tags') or [],
              'evidence':src.get('evidence') or [],
              'lessons':src.get('lessons') or [],
              'lesson_provenance':src.get('lesson_provenance'),
              'rederived_evidence':src.get('rederived_evidence'),
              'semantic_use_allowed': bool(
                  name==active or
                  (src.get('lesson_provenance') or {}).get('semantic_validation_by_rederivation') is True
              ),
            }
        else:
            obs=rederived_by_branch.get(name)
            if obs and obs.get('tip_commit')==tip:
                row={
                  'branch':name,
                  'observed_tip':tip,
                  'mode':'EXPERIENCE_ONLY',
                  'inventory_class':'DYNAMIC_REDERIVED_EXPERIENCE',
                  'registered':False,
                  'registry_head_sha':None,
                  'role':'DYNAMIC_REDERIVED_STRUCTURAL_HISTORY',
                  'tags':['lineage','rederived','structural_evidence'],
                  'evidence':['experience/yado-g2-raw-branch-evidence-rederivation-v1.json'],
                  'lessons':[],
                  'lesson_provenance':{
                    'source_class':'YADO_REDERIVED_FROM_EXACT_BRANCH_TREE',
                    'allowed_use':'STRUCTURAL_CAUSAL_HISTORY_EVIDENCE_AND_FUTURE_HYPOTHESIS_ONLY',
                    'semantic_validation_by_rederivation':False,
                  },
                  'rederived_evidence':{
                    'artifact':'experience/yado-g2-raw-branch-evidence-rederivation-v1.json',
                    'observation_digest':obs.get('observation_digest'),
                    'source_class':'YADO_REDERIVED_FROM_EXACT_BRANCH_TREE',
                    'semantic_equivalence_to_host_lessons_claimed':False,
                  },
                  'evidence_use_allowed':True,
                  'semantic_use_allowed':False,
                }
            else:
                row={
                  'branch':name,
                  'observed_tip':tip,
                  'mode':'EXPERIENCE_ONLY',
                  'inventory_class':'RAW_BRANCH_INVENTORY_ONLY',
                  'registered':False,
                  'registry_head_sha':None,
                  'role':'UNREAD_DYNAMIC_LINEAGE_EVIDENCE',
                  'tags':['lineage','unread','raw_evidence'],
                  'evidence':[],
                  'lessons':[],
                  'lesson_provenance':{
                    'source_class':'RAW_BRANCH_INVENTORY_ONLY',
                    'allowed_use':'LINEAGE_NAVIGATION_AND_EVIDENCE_DISCOVERY_ONLY',
                    'semantic_validation_by_rederivation':False,
                  },
                  'rederived_evidence':None,
                  'evidence_use_allowed':False,
                  'semantic_use_allowed':False,
                }
        rows.append(row)

    actual=set(refs); regset=set(registered)
    raw=[x for x in rows if x['inventory_class']=='RAW_BRANCH_INVENTORY_ONLY']
    dyn_rederived=[x for x in rows if x['inventory_class']=='DYNAMIC_REDERIVED_EXPERIENCE']
    active_rows=[x for x in rows if x['mode']=='ACTIVE_LINEAGE']
    bad_raw=[x['branch'] for x in raw if x.get('lessons') or x.get('semantic_use_allowed') or (x.get('lesson_provenance') or {}).get('source_class')!='RAW_BRANCH_INVENTORY_ONLY']
    bad_curated=[]
    for x in rows:
        lp=x.get('lesson_provenance') or {}
        if x['inventory_class']=='REGISTERED_CURATED_SUMMARY_WITH_REDERIVED_OBSERVATIONS':
            rd=x.get('rederived_evidence') or {}
            if not (
                lp.get('semantic_validation_by_rederivation') is False and
                lp.get('allowed_use') in {'NAVIGATION_AND_HYPOTHESIS_ONLY','PRIORITIZATION_GUARDS_TEST_SELECTION_ONLY'} and
                rd.get('source_class')=='YADO_REDERIVED_FROM_VERIFIED_RAW_EVIDENCE' and
                rd.get('semantic_equivalence_to_host_lessons_claimed') is False
            ):
                bad_curated.append(x['branch'])

    checks={
      'remote_inventory_nonempty':bool(refs),
      'one_active_lineage':len(active_rows)==1 and active_rows[0]['branch']==active,
      'dynamic_view_covers_every_remote_branch':{x['branch'] for x in rows}==actual,
      'canonical_registry_has_no_nonexistent_branch':len(regset-actual)==0,
      'raw_unregistered_branches_are_nonsemantic':len(bad_raw)==0,
      'dynamic_rederived_entries_are_structural_only':all((x.get('semantic_use_allowed') is False and x.get('evidence_use_allowed') is True and not x.get('lessons')) for x in dyn_rederived),
      'curated_summaries_are_explicitly_nonsemantic':len(bad_curated)==0,
      'no_automatic_canonical_mutation':req.get('canonical_mutation') is False,
      'no_automatic_promotion':req.get('automatic_promotion') is False,
      'g3_not_started':req.get('g3_genesis') is False,
    }
    status='PASS_SHADOW_G2_DYNAMIC_EXPERIENCE_MEMORY_V1' if all(checks.values()) else 'WITHHOLD_G2_DYNAMIC_EXPERIENCE_MEMORY_V1'
    out={
      'schema':'yado.g2.dynamic_experience_memory.v1',
      'status':status,
      'active_branch':active,
      'remote_branch_count':len(actual),
      'canonical_registry_branch_count':len(regset),
      'registered_experience_count':sum(1 for x in rows if x['registered'] and x['mode']=='EXPERIENCE_ONLY'),
      'raw_lineage_count':len(raw),
      'raw_lineage_branches':[x['branch'] for x in raw],
      'dynamic_rederived_count':len(dyn_rederived),
      'dynamic_rederived_branches':[x['branch'] for x in dyn_rederived],
      'rederivation_artifact_digest':rederived.get('experience_digest'),
      'missing_from_canonical_registry':sorted(actual-regset),
      'registry_only_branches':sorted(regset-actual),
      'branches':rows,
      'checks':checks,
      'policy':{
        'raw_branch_inventory_is_not_semantic_knowledge':True,
        'host_curated_summary_is_not_semantic_validation':True,
        'rederived_observations_require_exact_raw_evidence':True,
        'reuse_requires_fresh_admission':True,
        'legacy_code_execution':False,
        'canonical_mutation':False,
        'automatic_promotion':False,
        'g3_genesis':False,
      },
      'next_required_capability':'RAW_BRANCH_EVIDENCE_REDERIVATION' if raw else None,
      'semantic_boundary':'DYNAMIC GIT LINEAGE MEMORY. DISCOVERY OF A BRANCH IS EVIDENCE THAT THE BRANCH EXISTS, NOT EVIDENCE THAT ITS CONTENT HAS BEEN UNDERSTOOD OR VALIDATED.'
    }
    out['experience_digest']=digest(out)
    return out

if __name__=='__main__':
    out=build()
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps({
      'status':out['status'],
      'remote_branch_count':out['remote_branch_count'],
      'canonical_registry_branch_count':out['canonical_registry_branch_count'],
      'raw_lineage_count':out['raw_lineage_count'],
      'raw_lineage_branches':out['raw_lineage_branches'],
      'dynamic_rederived_count':out['dynamic_rederived_count'],
      'dynamic_rederived_branches':out['dynamic_rederived_branches'],
      'next_required_capability':out['next_required_capability'],
      'experience_digest':out['experience_digest'],
    },indent=2,sort_keys=True))
    if not out['status'].startswith('PASS_'):
        raise SystemExit(2)
