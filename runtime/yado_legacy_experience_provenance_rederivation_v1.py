from __future__ import annotations
from pathlib import Path
import ast,copy,hashlib,json,os,re,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path.insert(0,str(ROOT))

from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_legacy_experience_retriever_v2 import LegacyExperienceRetrieverV1

HEAD=REPO/'canonical'/'yado-main-head-g2.json'
CORE=REPO/'canonical'/'yado-unified-core-v1.json'
REG=REPO/'canonical'/'yado-unified-experience-registry-v1.json'
RUNTIME=REPO/'runtime'/'yado_unified_core_v1.py'
LEDGER=REPO/'architecture'/'evolution-ledger.json'
DERIVED=REPO/'canonical'/'yado-legacy-experience-derived-provenance-v1.json'
OUT=ROOT/'yado_legacy_experience_provenance_rederivation_v1_receipt.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))

def scalar(v):
    return isinstance(v,(str,int,float,bool)) or v is None

def json_observations(obj,max_atoms=160,max_depth=8):
    out=[]
    def walk(x,path,depth):
        if len(out)>=max_atoms or depth>max_depth:return
        if isinstance(x,dict):
            for k in sorted(x):
                if len(out)>=max_atoms:return
                walk(x[k],path+[str(k)],depth+1)
        elif isinstance(x,list):
            for i,v in enumerate(x[:24]):
                if len(out)>=max_atoms:return
                walk(v,path+[str(i)],depth+1)
        elif scalar(x):
            key='.'.join(path)
            leaf=(path[-1].lower() if path else '')
            important=(
              leaf in {'status','verdict','result','pass','passed','score','accuracy','mode','state','component_id','schema','semantic_boundary'}
              or 'check' in key.lower() or 'metric' in key.lower() or leaf.endswith('_score') or leaf.endswith('_accuracy')
            )
            if important:
                out.append({'kind':'JSON_SCALAR','path':key,'value':x})
    walk(obj,[],0)
    return out

def python_observations(text,max_atoms=160):
    out=[]
    try:tree=ast.parse(text)
    except SyntaxError:return [{'kind':'PY_PARSE','value':'SYNTAX_ERROR'}]
    for n in ast.walk(tree):
        if len(out)>=max_atoms:break
        if isinstance(n,ast.ClassDef):
            out.append({'kind':'PY_CLASS','value':n.name})
        elif isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)):
            out.append({'kind':'PY_FUNCTION','value':n.name})
        elif isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name):
            name=n.targets[0].id
            if name.isupper() and isinstance(n.value,ast.Constant) and scalar(n.value.value):
                out.append({'kind':'PY_CONSTANT','path':name,'value':n.value.value})
    return out

def text_observations(text,max_atoms=100):
    out=[]
    for line in text.splitlines():
        if len(out)>=max_atoms:break
        s=line.strip()
        if not s or s.startswith('#'):continue
        m=re.match(r'^([A-Za-z_][A-Za-z0-9_-]{1,60})\s*:\s*(.{1,180})$',s)
        if m:
            out.append({'kind':'TEXT_KEY_VALUE','path':m.group(1),'value':m.group(2)})
    return out

head=load(HEAD);core=load(CORE);registry=load(REG);ledger=load(LEDGER)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['LEGACY_EXPERIENCE_SUMMARY_PROVENANCE']:raise RuntimeError('UNEXPECTED_FRONTIER')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')
retriever=LegacyExperienceRetrieverV1(REPO,registry)

legacy=[x for x in registry.get('branches',[]) if x.get('mode')=='EXPERIENCE_ONLY']
original_lessons={x['branch']:copy.deepcopy(x.get('lessons',[])) for x in legacy}
branches=[];failures=[];total_paths=0;retrieved_paths=0
for entry in legacy:
    evid=[]
    branch_obs=[]
    for path in entry.get('evidence',[]):
        total_paths+=1
        try:
            item=retriever.read_registered(entry['branch'],path)
            retrieved_paths+=1
            text=item['content']
            suffix=Path(path).suffix.lower()
            if suffix=='.json':
                try:obs=json_observations(json.loads(text))
                except Exception:obs=text_observations(text)
            elif suffix=='.py':
                obs=python_observations(text)
            else:
                obs=text_observations(text)
            # Exact file identity is itself a provenance observation, never a semantic lesson.
            file_atom={'kind':'FILE_IDENTITY','path':path,'sha256':item['sha256'],'bytes':item['bytes'],
                       'registered_commit':item['registered_commit'],'transport':item['transport']}
            branch_obs.append(file_atom)
            branch_obs.extend([{**o,'source_path':path,'source_sha256':item['sha256']} for o in obs])
            evid.append({'path':path,'sha256':item['sha256'],'bytes':item['bytes'],
                         'registered_commit':item['registered_commit'],'transport':item['transport'],
                         'observation_count':len(obs)+1})
        except Exception as exc:
            failures.append({'branch':entry['branch'],'path':path,'error':type(exc).__name__+':'+str(exc)[:220]})
    # Deduplicate exact structural observations.
    seen=set();dedup=[]
    for o in branch_obs:
        k=canon(o)
        if k not in seen:
            seen.add(k);dedup.append(o)
    branches.append({
      'branch':entry['branch'],'role':entry.get('role'),'registered_head_sha':entry.get('head_sha'),
      'host_curated_lessons':copy.deepcopy(entry.get('lessons',[])),
      'host_lesson_provenance':{
        'source_class':'HOST_CURATED_REGISTRY_SUMMARY',
        'semantic_validation_by_rederivation':False,
        'allowed_use':'NAVIGATION_AND_HYPOTHESIS_ONLY'
      },
      'yado_rederived':{
        'source_class':'YADO_REDERIVED_FROM_VERIFIED_RAW_EVIDENCE',
        'derivation_mode':'BOUNDED_STRUCTURAL_OBSERVATION_EXTRACTION_V1',
        'semantic_equivalence_to_host_lessons_claimed':False,
        'observation_count':len(dedup),
        'observations':dedup[:320],
      },
      'evidence':evid,
    })

coverage=sum(1 for b in branches if b['yado_rederived']['observation_count']>0)
retrieval_ratio=retrieved_paths/max(1,total_paths)
artifact={
 'schema':'yado.legacy_experience_derived_provenance.v1',
 'generation':ledger['current_head'],
 'source_registry_digest':registry.get('registry_digest'),
 'legacy_branch_count':len(legacy),
 'retrieval':{'registered_paths':total_paths,'retrieved_paths':retrieved_paths,'ratio':retrieval_ratio,'failures':failures},
 'provenance_policy':{
   'host_curated_lessons':'PRESERVED_UNCHANGED_AND_EXPLICITLY_LABELLED',
   'yado_rederived_observations':'DERIVED_ONLY_FROM_EXACT_REGISTERED_RAW_EVIDENCE',
   'semantic_equivalence_claimed':False,
   'legacy_code_execution':False,
 },
 'branches':branches,
}
artifact['artifact_digest']=h(artifact)

checks={
 'thirteen_legacy_branches':len(legacy)==13,
 'all_registered_paths_retrieved':retrieved_paths==total_paths and not failures,
 'all_legacy_branches_have_rederived_observations':coverage==len(legacy),
 'original_lessons_preserved':all(original_lessons[b['branch']]==b['host_curated_lessons'] for b in branches),
 'host_summaries_explicitly_labelled':all(b['host_lesson_provenance']['source_class']=='HOST_CURATED_REGISTRY_SUMMARY' for b in branches),
 'raw_rederived_layer_explicitly_labelled':all(b['yado_rederived']['source_class']=='YADO_REDERIVED_FROM_VERIFIED_RAW_EVIDENCE' for b in branches),
 'no_semantic_equivalence_overclaim':all(b['yado_rederived']['semantic_equivalence_to_host_lessons_claimed'] is False for b in branches),
 'no_legacy_execution':artifact['provenance_policy']['legacy_code_execution'] is False,
 'canonical_head_immutable_before_gate':ledger.get('current_head_digest')==head.get('canonical_head_digest'),
}
passed=all(checks.values())

post_head=None;post_core=None;post_reg=None
if passed:
    DERIVED.write_text(json.dumps(artifact,indent=2,sort_keys=True)+'\n')
    # Add provenance pointers without rewriting lesson content.
    new_reg=copy.deepcopy(registry);new_reg.pop('registry_digest',None)
    by_branch={b['branch']:b for b in branches}
    for e in new_reg.get('branches',[]):
        if e.get('mode')!='EXPERIENCE_ONLY':continue
        b=by_branch[e['branch']]
        e['lesson_provenance']={
          'source_class':'HOST_CURATED_REGISTRY_SUMMARY',
          'semantic_validation_by_rederivation':False,
          'allowed_use':'NAVIGATION_AND_HYPOTHESIS_ONLY'
        }
        e['rederived_evidence']={
          'artifact':'canonical/yado-legacy-experience-derived-provenance-v1.json',
          'artifact_digest':artifact['artifact_digest'],
          'source_class':'YADO_REDERIVED_FROM_VERIFIED_RAW_EVIDENCE',
          'observation_count':b['yado_rederived']['observation_count'],
          'semantic_equivalence_to_host_lessons_claimed':False,
        }
    new_reg['registry_digest']=h(new_reg);REG.write_text(json.dumps(new_reg,indent=2,sort_keys=True)+'\n')
    post_reg=new_reg['registry_digest']

    # Expose provenance through the actual unified-core experience search.
    runtime=RUNTIME.read_text(encoding='utf-8')
    old="""                    'lessons':entry.get('lessons',[]),
                    'evidence':entry.get('evidence',[]),
                    'claim_boundary':entry.get('claim_boundary'),"""
    new="""                    'lessons':entry.get('lessons',[]),
                    'lesson_provenance':entry.get('lesson_provenance'),
                    'rederived_evidence':entry.get('rederived_evidence'),
                    'evidence':entry.get('evidence',[]),
                    'claim_boundary':entry.get('claim_boundary'),"""
    if old not in runtime:raise RuntimeError('UNIFIED_CORE_EXPERIENCE_SEARCH_PATTERN_MISSING')
    runtime=runtime.replace(old,new)
    RUNTIME.write_text(runtime,encoding='utf-8');runtime_sha=fsha(RUNTIME)

    new_core=copy.deepcopy(core);new_core.pop('core_digest',None)
    new_core['experience_registry_digest']=post_reg
    new_core['runtime_sha256']=runtime_sha
    mem=next(x for x in new_core['planes'] if x.get('plane_id')=='MEMORY_AND_EXPERIENCE')
    mem['responsibilities']=sorted(set(mem.get('responsibilities',[])+['legacy_experience_provenance_separation']))
    new_core['legacy_experience_provenance']={
      'artifact':'canonical/yado-legacy-experience-derived-provenance-v1.json',
      'artifact_digest':artifact['artifact_digest'],
      'host_summary_class':'HOST_CURATED_REGISTRY_SUMMARY',
      'rederived_class':'YADO_REDERIVED_FROM_VERIFIED_RAW_EVIDENCE',
      'legacy_branch_coverage':coverage,
      'registered_path_coverage':retrieval_ratio,
      'semantic_equivalence_claimed':False,
      'gate_run_id':str(os.getenv('GITHUB_RUN_ID') or 'LOCAL'),
    }
    new_core['current_frontier']='UNIFIED_CORE_POST_LEGACY_PROVENANCE_SELF_AUDIT_V1'
    new_core['core_digest']=h(new_core);CORE.write_text(json.dumps(new_core,indent=2,sort_keys=True)+'\n')

    new_head=copy.deepcopy(head);new_head.pop('canonical_head_digest',None)
    new_head['unified_core']['experience_registry_digest']=post_reg
    new_head['unified_core']['runtime_sha256']=runtime_sha
    new_head['unified_core']['core_digest']=new_core['core_digest']
    new_head['unified_core']['legacy_experience_provenance_artifact_digest']=artifact['artifact_digest']
    new_head['current_frontier']='UNIFIED_CORE_POST_LEGACY_PROVENANCE_SELF_AUDIT_V1'
    new_head['canonical_head_digest']=h(new_head);HEAD.write_text(json.dumps(new_head,indent=2,sort_keys=True)+'\n')
    post_head=new_head['canonical_head_digest'];post_core=new_core['core_digest']
    status='PASS_LEGACY_EXPERIENCE_PROVENANCE_REDERIVATION_V1'
    next_cap='UNIFIED_CORE_POST_LEGACY_PROVENANCE_SELF_AUDIT_V1'
else:
    status='WITHHOLD_LEGACY_EXPERIENCE_PROVENANCE_REDERIVATION_V1'
    next_cap='LEGACY_EXPERIENCE_SUMMARY_PROVENANCE'

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={
 'schema':'yado.g2.legacy_experience_provenance_rederivation.v1','status':status,
 'checks':checks,'legacy_branch_count':len(legacy),'branch_coverage':coverage,
 'retrieval_ratio':retrieval_ratio,'failures':failures,
 'derived_artifact_digest':artifact['artifact_digest'],
 'canonical_mutation':passed,'promotion_applied':False,'generation_transition':False,'g3_genesis_performed':False,
 'post_head_digest':post_head,'post_core_digest':post_core,'post_registry_digest':post_reg,
 'next_required_capability':next_cap,
 'semantic_boundary':'SEPARATES HOST-CURATED LEGACY LESSON SUMMARIES FROM YADO-REDERIVED STRUCTURAL OBSERVATIONS GROUNDED IN EXACT RAW HISTORICAL EVIDENCE. DOES NOT CLAIM SEMANTIC EQUIVALENCE OR SUBJECTIVE MEMORY.'
}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_LEGACY_EXPERIENCE_PROVENANCE_REDERIVATION",
 'event_type':'LEGACY_EXPERIENCE_PROVENANCE_RECONCILIATION','status':'PASS' if passed else 'WITHHOLD',
 'generation':ledger['current_head'],'deficit':'LEGACY_EXPERIENCE_SUMMARY_PROVENANCE',
 'effect':'HOST_SUMMARIES_SEPARATED_FROM_YADO_RAW_REDERIVED_OBSERVATIONS' if passed else 'LEGACY_PROVENANCE_REDERIVATION_WITHHELD',
 'source_path':f'receipts/yado-legacy-experience-provenance-rederivation-v1-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':passed,'promotion_applied':False,'generation_transition':False}
if passed:
    e['previous_head_digest']=ledger['current_head_digest'];e['new_head_digest']=post_head
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
if passed:ledger['current_head_digest']=post_head
ledger['open_deficits']=[next_cap];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':status,'checks':checks,'branch_coverage':coverage,'retrieval_ratio':retrieval_ratio,
 'failures':failures,'post_head_digest':post_head,'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('LEGACY_EXPERIENCE_PROVENANCE_REDERIVATION_WITHHELD')
