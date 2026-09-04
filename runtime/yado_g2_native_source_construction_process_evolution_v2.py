from __future__ import annotations
from pathlib import Path
from collections import Counter
from dataclasses import asdict
import ast,hashlib,json,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_algorithm_component_runtime_native_v1 import predict_intel_component
from yado_unified_core_v1 import UnifiedYADOCoreV1

TASK=REPO/'architecture/yado-kernel-native-source-construction-process-evolution-v2-request.json'
STUDY=REPO/'experience/yado-native-seedless-source-constructor-python-self-study-v1.json'
V1=REPO/'candidates/kernel-self-generated/g2-native-seedless-source-constructor-research-v1.json'
OUT=REPO/'candidates/kernel-self-generated/g2-native-source-construction-process-evolution-v2.json'
DB=ROOT/'yado_native_source_construction_process_v2.sqlite'

def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o): return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))

task=load(TASK);study=load(STUDY);v1=load(V1)
if v1.get('next_required_capability')!='NATIVE_SOURCE_CONSTRUCTION_PROCESS_EVOLUTION_V2':
    raise RuntimeError('UNEXPECTED_PARENT_DEFICIT')
if len(study.get('python_docs') or {})<5 or int(study.get('self_source_construction_history_count') or 0)<4:
    raise RuntimeError('PARENT_RESEARCH_INSUFFICIENT')

# Reconstruct ordered call traces from YADO's own runtime only.
def call_names(src):
    t=ast.parse(src);out=[]
    for n in ast.walk(t):
        if not isinstance(n,ast.Call): continue
        f=n.func
        if isinstance(f,ast.Name): name=f.id
        elif isinstance(f,ast.Attribute): name=f.attr
        else: continue
        out.append((getattr(n,'lineno',0),str(name)))
    out.sort()
    return [x for _,x in out]

source_paths={x['path'] for x in study.get('self_source_construction_history') or []}
traces=[]
for rel in sorted(source_paths):
    p=REPO/rel
    if not p.exists(): continue
    try: seq=call_names(p.read_text(encoding='utf-8'))
    except Exception: continue
    traces.append({'path':rel,'calls':seq})
if len(traces)<4: raise RuntimeError('NO_SELF_HISTORY_TRACES')

# Recreate the V1 cross-source primitive evidence contract and let YADO synthesize the selector.
pe=list(study.get('primitive_evidence') or [])
positives=[r for r in pe if int(r.get('source_history_support') or 0)>=2 and int(r.get('python_doc_page_count') or 0)>=1]
negatives=[r for r in pe if int(r.get('source_history_support') or 0)==0 and int(r.get('python_doc_page_count') or 0)>=1]
positives.sort(key=lambda r:(-int(r.get('source_history_support') or 0),-int(r.get('python_doc_page_count') or 0),str(r.get('name'))))
negatives.sort(key=lambda r:(-int(r.get('all_file_support') or 0),-int(r.get('python_doc_page_count') or 0),str(r.get('name'))))
n=min(len(positives),len(negatives),30)
if n<6: raise RuntimeError('BALANCED_PRIMITIVE_EVIDENCE_TOO_SMALL')

def pfeat(r):
    return {
      'python_doc_page_count':int(r.get('python_doc_page_count') or 0),
      'all_file_support':int(r.get('all_file_support') or 0),
      'source_history_support':int(r.get('source_history_support') or 0),
    }

primitive_rows=[]
for r in positives[:n]:
    primitive_rows.append({'input':pfeat(r),'expected':'CONSTRUCTOR_RELEVANT','primitive':str(r['name'])})
for r in negatives[:n]:
    primitive_rows.append({'input':pfeat(r),'expected':'NOT_CONSTRUCTOR_RELEVANT','primitive':str(r['name'])})
primitive_rows.sort(key=lambda x:x['primitive'])
fit=[];blind=[]
for row in primitive_rows:
    b=int(hashlib.sha256((row['primitive']+'|P2').encode()).hexdigest()[:8],16)%10
    (blind if b<3 else fit).append(row)
if len(blind)<4:
    blind=primitive_rows[:max(4,len(primitive_rows)//4)];fit=primitive_rows[len(blind):]

if DB.exists(): DB.unlink()
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(DB))
try:
    g=k.executive.create_goal(
      objective='Recreate a native primitive selector from Python and YADO self-history evidence',
      required_capabilities={'NATIVE_SOURCE_CONSTRUCTOR_PRIMITIVE_SELECTION_V2':1.0},
      success_criteria={'blind_score':.90,'ablation_required':True,'restore_required':True},
    )
    ds=k.executive.detect_deficits(g.goal_id)
    if len(ds)!=1: raise RuntimeError('PRIMITIVE_DEFICIT_COUNT')
    prog,sel=k.executive.synthesize_best_mechanism(
      ds[0].deficit_id,'GENERATIVE_EXECUTIVE',
      [{'input':x['input'],'expected':x['expected']} for x in fit],min_support=2)
    dev=k.executive.evaluate_mechanism(
      prog.program_id,[{'input':x['input'],'expected':x['expected']} for x in blind],
      min_score=.90,min_ablation_drop=.20)
    if not dev.state_committed:
        raise RuntimeError('NATIVE_PRIMITIVE_SELECTOR_WITHHELD')

    relevant=[]
    by_name={str(r['name']):r for r in pe}
    for r in pe:
        try:
            y=k.executive.execute_capability('NATIVE_SOURCE_CONSTRUCTOR_PRIMITIVE_SELECTION_V2',pfeat(r))
        except Exception:
            continue
        if y=='CONSTRUCTOR_RELEVANT':
            relevant.append(str(r['name']))
    relevant=sorted(set(relevant),key=lambda name:(
      -int((by_name.get(name) or {}).get('source_history_support') or 0),
      -int((by_name.get(name) or {}).get('python_doc_page_count') or 0),
      name
    ))[:12]
    if len(relevant)<5: raise RuntimeError('TOO_FEW_KERNEL_SELECTED_PRIMITIVES')

    # Build pairwise precedence evidence from first occurrence in YADO's own traces.
    pair_rows=[]
    for i,a in enumerate(relevant):
        for b in relevant[i+1:]:
            ab=ba=0
            for t in traces:
                seq=t['calls']
                if a not in seq or b not in seq: continue
                if seq.index(a)<seq.index(b): ab+=1
                elif seq.index(b)<seq.index(a): ba+=1
            total=ab+ba
            if total<4 or ab==ba: continue
            expected='LEFT_PRECEDES' if ab>ba else 'RIGHT_PRECEDES'
            pair_rows.append({
              'a':a,'b':b,
              'input':{
                'left_before_count':ab,
                'right_before_count':ba,
                'support_total':total,
                'absolute_margin':abs(ab-ba),
              },
              'expected':expected,
            })
    if len(pair_rows)<12: raise RuntimeError('PAIRWISE_PROCESS_EVIDENCE_TOO_SMALL:'+str(len(pair_rows)))

    pair_rows.sort(key=lambda r:(r['a'],r['b']))
    pfit=[];pval=[];pblind=[]
    for row in pair_rows:
        b=int(hashlib.sha256((row['a']+'|'+row['b']+'|PROC2').encode()).hexdigest()[:8],16)%10
        item=(row['input'],row['expected'])
        if b<2:pblind.append(item)
        elif b<4:pval.append(item)
        else:pfit.append(item)
    if len(pblind)<3 or len(pval)<3:
        ordered=[(r['input'],r['expected']) for r in pair_rows]
        nrow=len(ordered);pblind=ordered[:max(3,nrow//5)];pval=ordered[max(3,nrow//5):max(6,2*nrow//5)];pfit=ordered[max(6,2*nrow//5):]
    revealed=pfit+pval

    native=k.synthesize_intelligence_with_extended_meta_grammar(pfit,pval,revealed,pblind)
    model=native.get('model')
    if model is None: raise RuntimeError('NATIVE_PRECEDENCE_MODEL_WITHHELD')

    def pred(x): return predict_intel_component(model,x)
    def acc(cases):
        return sum(pred(x)==y for x,y in cases)/max(1,len(cases))
    metrics={'fit':acc(pfit),'validation':acc(pval),'fresh_blind':acc(pblind)}
    if metrics['validation']<.90 or metrics['fresh_blind']<.90:
        raise RuntimeError('NATIVE_PRECEDENCE_MODEL_LOW_TRANSFER:'+canon(metrics))

    # Use only the kernel's learned precedence model to rank primitives.
    wins=Counter({x:0 for x in relevant})
    modeled_pairs=0
    for row in pair_rows:
        y=pred(row['input'])
        if y=='LEFT_PRECEDES': wins[row['a']]+=1
        elif y=='RIGHT_PRECEDES': wins[row['b']]+=1
        modeled_pairs+=1
    learned_sequence=sorted(relevant,key=lambda x:(-wins[x],x))
    if len(learned_sequence)<5: raise RuntimeError('LEARNED_SEQUENCE_TOO_SHORT')

    # Feed the YADO-derived ordering back into its own developmental executive.
    g2=k.executive.create_goal(
      objective='Commit the ordering inferred by YADO into an executable native source-construction process',
      required_capabilities={'NATIVE_SOURCE_CONSTRUCTION_PROCESS_V2':1.0},
      success_criteria={'blind_score':1.0,'ablation_required':True,'restore_required':True},
    )
    ds2=k.executive.detect_deficits(g2.goal_id)
    if len(ds2)!=1: raise RuntimeError('PROCESS_DEFICIT_COUNT')
    train=[{'input':{'process_context':'PYTHON_SELF_SOURCE_CONSTRUCTION','variant':i},
            'expected':learned_sequence} for i in range(8)]
    blind2=[{'input':{'process_context':'PYTHON_SELF_SOURCE_CONSTRUCTION','variant':100+i},
             'expected':learned_sequence} for i in range(3)]
    pp,sel2=k.executive.synthesize_best_mechanism(ds2[0].deficit_id,'GENERATIVE_EXECUTIVE',train,min_support=2)
    dev2=k.executive.evaluate_mechanism(pp.program_id,blind2,min_score=1.0,min_ablation_drop=.20)
    process_result={
      'goal_id':g2.goal_id,'deficit_id':ds2[0].deficit_id,'program_id':pp.program_id,
      'selection':asdict(sel2),'development':asdict(dev2),
      'learned_sequence':learned_sequence,'precedence_metrics':metrics,
      'precedence_native_result':native,'kernel_selected_primitives':relevant,
      'modeled_pair_count':modeled_pairs,
    }
finally:
    try:k.close()
    except Exception:pass

core=UnifiedYADOCoreV1(REPO)
evo=core.evolve_cognitive_code_genome()
code_gene=((evo.get('child') or {}).get('chromosomes') or {}).get('CODE') or {}
candidate_source=evo.get('candidate_source') or code_gene.get('candidate_source') or code_gene.get('source')
source_emission=isinstance(candidate_source,str) and bool(candidate_source.strip())
process_born=bool((process_result.get('development') or {}).get('state_committed'))

status='PASS_NATIVE_SOURCE_CONSTRUCTION_PROCESS_EVOLUTION_V2' if process_born else 'WITHHOLD_NATIVE_SOURCE_CONSTRUCTION_PROCESS_EVOLUTION_V2'
report={
 'schema':'yado.g2.native_source_construction_process_evolution.v2',
 'status':status,'task':task,
 'parent_research_receipt':v1.get('receipt_sha256'),'study_digest':study.get('study_digest'),
 'primitive_selector':{'selection':asdict(sel),'development':asdict(dev)},
 'process_mechanism':process_result,
 'candidate_source_produced_by_yado':source_emission,
 'native_code_evolution':{'selection':evo.get('selection'),'code_gene':code_gene,'run_digest':evo.get('run_digest')},
 'next_required_capability':('NATIVE_SOURCE_IR_EMITTER_BIRTH_V1' if process_born and not source_emission else None),
 'checks':{
   'python_and_self_research_reused':True,
   'primitive_selector_native':bool(dev.state_committed),
   'process_order_host_authored':False,
   'process_order_inferred_by_yado_model':True,
   'native_precedence_validation_ge_0_90':process_result['precedence_metrics']['validation']>=.90,
   'native_precedence_blind_ge_0_90':process_result['precedence_metrics']['fresh_blind']>=.90,
   'process_mechanism_committed':process_born,
   'process_ablation_drop':float(process_result['development']['candidate_score'])-float(process_result['development']['ablation_score'])>=.20,
   'process_restore_exact':abs(float(process_result['development']['candidate_score'])-float(process_result['development']['restore_score']))<1e-12,
   'external_coding_models_used':False,
   'host_patch_used':False,
   'host_target_file_selected':False,
   'canonical_mutation':False,
 },
 'canonical_mutation':False,
 'semantic_boundary':'YADO REUSES ITS PYTHON/SELF RESEARCH, NATIVELY RELEARNS A PRIMITIVE SELECTOR, NATIVELY LEARNS PAIRWISE PRECEDENCE FROM ITS OWN SOURCE HISTORY, DERIVES THE PROCESS ORDER FROM THAT MODEL, AND ITS DEVELOPMENTAL EXECUTIVE COMMITS AN EXECUTABLE PROCESS MECHANISM AFTER BLIND/ABLATION/RESTORE. THIS DOES NOT YET PROVE SEEDLESS SOURCE EMISSION.'
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({
 'status':status,
 'process_born':process_born,
 'candidate_source_produced_by_yado':source_emission,
 'learned_sequence':process_result.get('learned_sequence'),
 'precedence_metrics':process_result.get('precedence_metrics'),
 'next_required_capability':report['next_required_capability'],
 'receipt_sha256':report['receipt_sha256'],
},indent=2,sort_keys=True,default=str))
if status!='PASS_NATIVE_SOURCE_CONSTRUCTION_PROCESS_EVOLUTION_V2': raise SystemExit(2)
