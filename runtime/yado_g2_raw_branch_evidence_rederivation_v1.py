from __future__ import annotations
from pathlib import Path
import hashlib,json,subprocess

REPO=Path(__file__).resolve().parents[1]
MEM=REPO/'experience/yado-g2-dynamic-experience-memory-v1.json'
REQ=REPO/'architecture/yado-g2-raw-branch-evidence-rederivation-v1-request.json'
OUT=REPO/'experience/yado-g2-raw-branch-evidence-rederivation-v1.json'
CAND=REPO/'candidates/kernel-self-generated/g2-raw-branch-evidence-rederivation-v1.json'

def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o): return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def run(args,check=True):
    cp=subprocess.run(args,cwd=REPO,capture_output=True,text=True,timeout=30)
    if check and cp.returncode!=0:
        raise RuntimeError('GIT_FAIL:'+repr(args)+':'+cp.stderr[-300:])
    return cp
def show_text(tip,path,max_chars=600000):
    cp=run(['git','show',f'{tip}:{path}'],check=False)
    if cp.returncode!=0: return None
    return cp.stdout[:max_chars]
def show_json(tip,path):
    txt=show_text(tip,path)
    if txt is None: return None
    try:return json.loads(txt)
    except Exception:return None

req=load(REQ); mem=load(MEM)
if mem.get('status')!='PASS_SHADOW_G2_DYNAMIC_EXPERIENCE_MEMORY_V1':
    raise RuntimeError('DYNAMIC_MEMORY_NOT_PASS')
targets=list(mem.get('raw_lineage_branches') or [])
if not targets:
    raise RuntimeError('NO_RAW_BRANCH_TARGETS')
by_branch={x['branch']:x for x in mem.get('branches',[])}

observations=[]
failures=[]
for name in targets:
    row=by_branch.get(name) or {}
    tip=row.get('observed_tip')
    try:
        if not tip: raise RuntimeError('MISSING_TIP')
        run(['git','cat-file','-e',tip+'^{commit}'])
        tree=run(['git','rev-parse',tip+'^{tree}']).stdout.strip()
        meta=run(['git','show','-s','--format=%H%n%P%n%ct%n%s',tip]).stdout.splitlines()
        paths=run(['git','ls-tree','-r','--name-only',tip]).stdout.splitlines()
        changed=run(['git','diff-tree','--no-commit-id','--name-only','-r',tip],check=False).stdout.splitlines()
        ancestor=run(['git','merge-base','--is-ancestor',tip,'origin/yado-architecture-shadow-search'],check=False).returncode==0

        head=show_json(tip,'canonical/yado-main-head-g2.json') or {}
        ledger=show_json(tip,'architecture/evolution-ledger.json') or {}
        candidate_paths=[p for p in paths if p.startswith('candidates/kernel-self-generated/') and p.endswith('.json')]
        experience_paths=[p for p in paths if p.startswith('experience/') and p.endswith('.json')]
        receipt_paths=[p for p in paths if p.startswith('receipts/') and p.endswith('.json')]
        runtime_paths=[p for p in paths if p.startswith('runtime/') and p.endswith('.py')]
        architecture_paths=[p for p in paths if p.startswith('architecture/') and p.endswith('.json')]

        status_counts={}
        sampled=[]
        for p in candidate_paths[-40:]:
            d=show_json(tip,p)
            if not isinstance(d,dict): continue
            st=str(d.get('status') or '')
            if st:
                cls='PASS' if st.startswith('PASS') else 'WITHHOLD' if st.startswith('WITHHOLD') else 'OTHER'
                status_counts[cls]=status_counts.get(cls,0)+1
                sampled.append({'path':p,'status':st,'receipt_sha256':d.get('receipt_sha256')})
        events=ledger.get('events') if isinstance(ledger.get('events'),list) else []
        obs={
          'branch':name,
          'tip_commit':tip,
          'tree_sha':tree,
          'tip_parent_shas':meta[1].split() if len(meta)>1 else [],
          'tip_unix_time':int(meta[2]) if len(meta)>2 and meta[2].isdigit() else None,
          'tip_subject':meta[3] if len(meta)>3 else '',
          'is_ancestor_of_active_shadow':ancestor,
          'tree_counts':{
            'total_files':len(paths),'runtime_python':len(runtime_paths),'architecture_json':len(architecture_paths),
            'candidate_json':len(candidate_paths),'experience_json':len(experience_paths),'receipt_json':len(receipt_paths)
          },
          'tip_changed_paths':changed[:80],
          'canonical_head_observation':{
            'generation_id':head.get('generation_id'),
            'canonical_head_digest':head.get('canonical_head_digest'),
            'current_frontier':head.get('current_frontier'),
            'active_capability_count':len(head.get('active_capabilities') or []),
            'g3_genesis_performed':head.get('g3_genesis_performed'),
          },
          'ledger_observation':{
            'event_count':len(events),
            'current_head':ledger.get('current_head'),
            'current_head_digest':ledger.get('current_head_digest'),
            'current_head_event_id':ledger.get('current_head_event_id'),
            'open_deficits':ledger.get('open_deficits') or [],
          },
          'sampled_candidate_status_counts':status_counts,
          'sampled_candidates':sampled,
          'source_class':'YADO_REDERIVED_FROM_EXACT_BRANCH_TREE',
          'semantic_equivalence_claimed':False,
          'branch_code_executed':False,
          'allowed_use':'STRUCTURAL_CAUSAL_HISTORY_EVIDENCE_AND_FUTURE_HYPOTHESIS_ONLY',
        }
        obs['observation_digest']=digest(obs)
        observations.append(obs)
    except Exception as e:
        failures.append({'branch':name,'error':type(e).__name__+':'+str(e)[:300]})

observed={x['branch'] for x in observations}
checks={
  'all_raw_branches_read':observed==set(targets) and not failures,
  'exact_tip_identity_preserved':all(x['tip_commit']==by_branch[x['branch']]['observed_tip'] for x in observations),
  'no_branch_code_executed':all(x['branch_code_executed'] is False for x in observations),
  'semantic_equivalence_not_claimed':all(x['semantic_equivalence_claimed'] is False for x in observations),
  'source_class_exact_rederivation':all(x['source_class']=='YADO_REDERIVED_FROM_EXACT_BRANCH_TREE' for x in observations),
  'canonical_mutation_false':req.get('canonical_mutation') is False,
  'automatic_promotion_false':req.get('automatic_promotion') is False,
  'g3_false':req.get('g3_genesis') is False,
}
status='PASS_SHADOW_G2_RAW_BRANCH_EVIDENCE_REDERIVATION_V1' if all(checks.values()) else 'WITHHOLD_G2_RAW_BRANCH_EVIDENCE_REDERIVATION_V1'
report={
  'schema':'yado.g2.raw_branch_evidence_rederivation.v1',
  'status':status,
  'parent_dynamic_memory_digest':mem.get('experience_digest'),
  'target_count':len(targets),
  'observation_count':len(observations),
  'failure_count':len(failures),
  'targets':targets,
  'observations':observations,
  'failures':failures,
  'checks':checks,
  'remaining_raw_lineage_branches':sorted(set(targets)-observed),
  'canonical_mutation':False,
  'automatic_promotion':False,
  'g3_genesis':False,
  'next_required_capability':'DYNAMIC_MEMORY_REBIND_REDERIVED_EVIDENCE' if status.startswith('PASS_') else 'RAW_BRANCH_EVIDENCE_REDERIVATION_REPAIR',
  'semantic_boundary':'EXACT BRANCH TREES AND JSON STATE WERE READ AS DATA. NO HISTORICAL BRANCH CODE WAS EXECUTED. STRUCTURAL OBSERVATIONS DO NOT CLAIM SEMANTIC EQUIVALENCE TO CURATED LESSONS.'
}
report['experience_digest']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True); CAND.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n',encoding='utf-8')
CAND.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n',encoding='utf-8')
print(json.dumps({
 'status':status,'target_count':len(targets),'observation_count':len(observations),
 'failure_count':len(failures),'remaining_raw_lineage_branches':report['remaining_raw_lineage_branches'],
 'next_required_capability':report['next_required_capability'],'experience_digest':report['experience_digest']
},indent=2,sort_keys=True))
if not status.startswith('PASS_'): raise SystemExit(2)
