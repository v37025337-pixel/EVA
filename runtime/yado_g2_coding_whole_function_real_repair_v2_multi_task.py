from __future__ import annotations
from pathlib import Path
from itertools import product
import ast,copy,hashlib,json,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_bounded_compositional_program_repair_v3 import BoundedCompositionalProgramRepairV3
from yado_neutral_evidence_profile_selector_v1 import NeutralEvidenceProfileSelectorV1,EvidenceCandidate
from yado_unified_core_v1 import UnifiedYADOCoreV1

WHOLE1=REPO/'candidates/kernel-self-generated/g2-coding-whole-function-real-repair-v1.json'
SUB3=REPO/'candidates/kernel-self-generated/g2-coding-whole-function-substrate-expansion-v3.json'
HEAD=REPO/'canonical/yado-main-head-g2.json'
OUT=REPO/'candidates/kernel-self-generated/g2-coding-whole-function-real-repair-v2-multi-task.json'
EXP=REPO/'experience/yado-coding-whole-function-real-repair-v2-multi-task.json'

def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def sha(s):return hashlib.sha256(s.encode()).hexdigest()

whole1,sub3,head=map(load,[WHOLE1,SUB3,HEAD])
if whole1.get('status')!='PASS_SHADOW_G2_CODING_WHOLE_FUNCTION_REAL_REPAIR_V1':raise RuntimeError('WHOLE_V1_PASS_REQUIRED')
if sub3.get('status')!='PASS_SHADOW_G2_CODING_WHOLE_FUNCTION_SUBSTRATE_EXPANSION_V3':raise RuntimeError('SUBSTRATE_V3_PASS_REQUIRED')
if sub3.get('next_required_capability')!='G2_CODING_WHOLE_FUNCTION_REAL_REPAIR_V2_MULTI_TASK':raise RuntimeError('SUBSTRATE_V3_FRONTIER_MISMATCH')
if set(sub3.get('added_safe_calls') or [])!={'float','str'}:raise RuntimeError('EXPECTED_FLOAT_STR_EXTENSIONS')
if set(sub3.get('added_readonly_attributes') or [])!={'get','items'}:raise RuntimeError('EXPECTED_GET_ITEMS_EXTENSIONS')
if 'RUNTIME-G2-EXPERIENCE-CONDITIONED-COGNITIVE-LAYER-V3' not in head.get('active_capabilities',[]):raise RuntimeError('COGNITIVE_LAYER_V3_REQUIRED')
core=UnifiedYADOCoreV1(REPO);head_before=copy.deepcopy(core.head)

class MultiWholeRepairV2(BoundedCompositionalProgramRepairV3):
    SAFE_CALLS=dict(BoundedCompositionalProgramRepairV3.SAFE_CALLS)
    SAFE_CALLS.update({'int':int,'float':float,'str':str})
    ALLOWED_ATTRS={'get','items'}

    @classmethod
    def _validate(cls,tree):
        banned=(ast.Import,ast.ImportFrom,ast.Global,ast.Nonlocal,ast.With,ast.AsyncFunctionDef,ast.ClassDef,ast.Lambda,
                ast.While,ast.For,ast.AsyncFor,ast.Try,ast.Raise,ast.Yield,ast.YieldFrom,ast.Await,ast.Delete)
        if any(isinstance(n,banned) for n in ast.walk(tree)):raise ValueError('UNSAFE_PROGRAM')
        funcs=[n for n in tree.body if isinstance(n,ast.FunctionDef)]
        if len(funcs)!=1 or len(tree.body)!=1:raise ValueError('EXACTLY_ONE_FUNCTION_REQUIRED')
        fname=funcs[0].name
        parents={}
        for p in ast.walk(tree):
            for c in ast.iter_child_nodes(p):parents[id(c)]=p
        for n in ast.walk(tree):
            if isinstance(n,ast.Attribute):
                par=parents.get(id(n))
                if not (isinstance(par,ast.Call) and par.func is n):raise ValueError('BARE_ATTRIBUTE_FORBIDDEN')
                if n.attr not in cls.ALLOWED_ATTRS:raise ValueError('ATTRIBUTE_NOT_ALLOWED')
            if isinstance(n,ast.Call):
                if isinstance(n.func,ast.Name):
                    if n.func.id not in cls.SAFE_CALLS:raise ValueError('CALL_NOT_ALLOWED')
                elif isinstance(n.func,ast.Attribute):
                    if n.func.attr not in cls.ALLOWED_ATTRS:raise ValueError('ATTRIBUTE_CALL_NOT_ALLOWED')
                else:raise ValueError('UNSAFE_CALL')
            if isinstance(n,ast.Name) and n.id.startswith('__'):raise ValueError('DUNDER_FORBIDDEN')
        return fname

    @classmethod
    def execute(cls,source,function_name,args):
        def safe_value(x,depth=0):
            if depth>5:return False
            if isinstance(x,(type(None),bool,int,float,str)):return True
            if isinstance(x,(tuple,list)):return len(x)<=32 and all(safe_value(v,depth+1) for v in x)
            if isinstance(x,dict):return len(x)<=32 and all(isinstance(k,(str,int,bool,float)) and safe_value(v,depth+1) for k,v in x.items())
            return False
        if not all(safe_value(a) for a in args):raise ValueError('NON_BUILTIN_ARGUMENT_FORBIDDEN')
        tree=ast.parse(source);fname=cls._validate(tree)
        if fname!=function_name:raise ValueError('FUNCTION_NAME_MISMATCH')
        env=dict(cls.SAFE_CALLS);env['__builtins__']={}
        exec(compile(tree,'<yado-multi-whole-v2>','exec'),env,env)
        return env[function_name](*copy.deepcopy(args))

def extract_function(path,name):
    src=Path(path).read_text(encoding='utf-8');tree=ast.parse(src)
    node=next((n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name),None)
    if node is None:raise RuntimeError('FUNCTION_NOT_FOUND:'+str(path)+':'+name)
    q=copy.deepcopy(node);q.decorator_list=[];q.returns=None;q.type_comment=None
    for a in list(q.args.posonlyargs)+list(q.args.args)+list(q.args.kwonlyargs):
        a.annotation=None;a.type_comment=None
    q.args.defaults=[];q.args.kw_defaults=[None for _ in q.args.kwonlyargs]
    ast.fix_missing_locations(q)
    out=ast.unparse(q)+'\n'
    MultiWholeRepairV2._validate(ast.parse(out))
    return out

targets=[]
s1=whole1['selected_function']
targets.append({'path':s1['path'],'function_name':s1['function_name'],'heritage':'WHOLE_V1'})
for path,name in sub3.get('incremental_identities') or []:
    targets.append({'path':path,'function_name':name,'heritage':'SUBSTRATE_V3_INCREMENTAL'})
uniq=[]
seen=set()
for t in targets:
    key=(t['path'],t['function_name'])
    if key in seen:continue
    seen.add(key);t['source']=extract_function(REPO/t['path'],t['function_name']);t['source_sha256']=sha(t['source']);uniq.append(t)
targets=uniq
if len(targets)!=2 or len({x['path'] for x in targets})!=2:raise RuntimeError('TWO_FUNCTION_TWO_FILE_TARGET_SET_REQUIRED')

def indirect_keys(tree,arg):
    keys=[]
    for comp in [x for x in ast.walk(tree) if isinstance(x,(ast.ListComp,ast.SetComp,ast.GeneratorExp,ast.DictComp))]:
        binds={}
        for g in comp.generators:
            if isinstance(g.target,ast.Name) and isinstance(g.iter,(ast.Tuple,ast.List)):
                vals=[];ok=True
                for e in g.iter.elts:
                    if not isinstance(e,ast.Constant) or not isinstance(e.value,(str,int)):ok=False;break
                    vals.append(e.value)
                if ok:binds[g.target.id]=vals
        for x in ast.walk(comp):
            if isinstance(x,ast.Subscript) and isinstance(x.value,ast.Name) and x.value.id==arg and isinstance(x.slice,ast.Name):
                for k in binds.get(x.slice.id,[]):
                    if k not in keys:keys.append(k)
    return keys

def arg_kind(tree,arg):
    keys=indirect_keys(tree,arg)
    direct=[]
    uses_items=False;uses_get=False
    for n in ast.walk(tree):
        if isinstance(n,ast.Subscript) and isinstance(n.value,ast.Name) and n.value.id==arg:
            if isinstance(n.slice,ast.Constant) and isinstance(n.slice.value,(str,int)) and n.slice.value not in direct:direct.append(n.slice.value)
        if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name) and n.func.value.id==arg:
            if n.func.attr=='items':uses_items=True
            if n.func.attr=='get':uses_get=True
    if keys:return ('BOOL_DICT',keys)
    if uses_items or uses_get or direct:return ('NUM_DICT',direct)
    return ('SCALAR',[])

def domain_for(source):
    tree=ast.parse(source);func=next(n for n in tree.body if isinstance(n,ast.FunctionDef))
    domains=[]
    for a in func.args.args:
        kind,keys=arg_kind(tree,a.arg)
        if kind=='BOOL_DICT':
            domains.append([dict(zip(keys,bits)) for bits in product((False,True),repeat=len(keys))])
        elif kind=='NUM_DICT':
            ds=[{}, {0:1.0},{0:2.0},{1:-1.0},{'0':3.0},{'a':1.0},{'b':-2.0},
                {0:1.0,1:2.0},{0:-1.0,1:3.0},{'0':2.0,'1':-1.0},{'a':2.0,'b':-1.0},
                {'a':0.5,'b':2.0},{0:1.0,'0':4.0},{1:0.5,'1':2.0}]
            domains.append(ds)
        else:
            domains.append([-3,-1,0,1,2,4])
    states=[]
    for combo in product(*domains):
        states.append(tuple(copy.deepcopy(combo)))
        if len(states)>=196:break
    # Keep only states that execute successfully under the reference.
    return states

def execute(src,name,args):return MultiWholeRepairV2.execute(src,name,copy.deepcopy(args))
def same_ast(a,b):
    try:return ast.dump(ast.parse(a),include_attributes=False)==ast.dump(ast.parse(b),include_attributes=False)
    except Exception:return False
def score(src,name,states,reference):
    ok=0
    for args in states:
        try:ok+=execute(src,name,args)==execute(reference,name,args)
        except Exception:pass
    return ok/max(1,len(states))

def partition(states):
    xs=sorted(states,key=lambda x:sha(canon(x)))
    n=len(xs)
    if n<24:raise RuntimeError('DOMAIN_TOO_SMALL:'+str(n))
    cal_n=max(8,min(20,n//5))
    seed_n=max(4,min(8,n//10))
    hidden_n=max(8,min(24,n//5))
    cal=xs[:cal_n];seed=xs[cal_n:cal_n+seed_n];hidden=xs[-hidden_n:]
    probe=xs[cal_n+seed_n:-hidden_n]
    if len(probe)<8:raise RuntimeError('PROBE_POOL_TOO_SMALL')
    return cal,seed,probe,hidden

def choose_defect(reference,name,calibration):
    examples=[(copy.deepcopy(a),execute(reference,name,a)) for a in calibration]
    cands=[];mp={}
    for cand in MultiWholeRepairV2._atomic_mutations(reference,examples,enable=('binop','compare','boolop','constant')):
        if same_ast(cand,reference):continue
        reversible=any(same_ast(back,reference) for back in MultiWholeRepairV2._atomic_mutations(cand,examples,enable=('binop','compare','boolop','constant')))
        if not reversible:continue
        sc=score(cand,name,calibration,reference)
        if sc>=.9:continue
        token='D-'+sha(cand)[:16];mp[token]=(cand,sc)
        cands.append(EvidenceCandidate(token=token,evidence=1.0-sc,complexity=1.0,risk=0.0,novelty=1.0))
    if not cands:raise RuntimeError('NO_REVERSIBLE_MATERIAL_DEFECT:'+name)
    sel=NeutralEvidenceProfileSelectorV1.select(cands,complexity_penalty=.01,risk_penalty=.5,novelty_bonus=.01)
    cand,sc=mp[sel['selected_token']]
    return cand,sc,sel

def hypotheses(mutated,name,known,max_count=160):
    xs=[];seen=set()
    def add(s):
        if not s or s in seen:return
        seen.add(s)
        try:
            if MultiWholeRepairV2._passes(s,name,known):xs.append(s)
        except Exception:pass
    add(mutated);first=[]
    for c in MultiWholeRepairV2._atomic_mutations(mutated,known,enable=('binop','compare','boolop','constant')):
        first.append(c);add(c)
        if len(first)>=220:break
    if len(xs)<2:
        for base in first[:120]:
            for c in MultiWholeRepairV2._atomic_mutations(base,known,enable=('binop','compare','boolop','constant')):
                add(c)
                if len(xs)>=max_count:break
            if len(xs)>=max_count:break
    xs.sort(key=lambda s:(len(s),sha(s),s))
    return xs[:max_count]

def distance(a,b):
    return 0.0 if canon(a)==canon(b) else 1.0

def run_task(meta):
    reference=meta['source'];name=meta['function_name']
    raw=domain_for(reference)
    states=[]
    for args in raw:
        try:
            y=execute(reference,name,args)
            if isinstance(y,(bool,int,float,str)):states.append(args)
        except Exception:pass
    # deterministic dedup
    unique=[];seen=set()
    for a in states:
        k=canon(a)
        if k not in seen:seen.add(k);unique.append(a)
    states=unique
    cal,seed,probe,hidden=partition(states)
    mutated,cal_score,defect_sel=choose_defect(reference,name,cal)
    mutated_hidden=score(mutated,name,hidden,reference)
    known=[(copy.deepcopy(a),execute(reference,name,a)) for a in seed]
    current=mutated;queried=[];trace=[]
    for cycle in range(12):
        hs=hypotheses(mutated,name,known)
        if MultiWholeRepairV2._passes(current,name,known) and current not in hs:hs=[current]+hs
        used={canon(x) for x in queried};remaining=[x for x in probe if canon(x) not in used]
        if not remaining:break
        think_e=core.cognitive_experience_decide('THINKING',{'oracle_available':True,'hypothesis_set_present':True,'state_known':True})
        intel_e=core.cognitive_experience_decide('INTELLIGENCE',{'hypothesis_set_present':True,'state_known':True})
        if think_e.get('decision')!='SEEK_EVIDENCE' or intel_e.get('decision')!='ACTIVE_EVIDENCE_SEARCH':
            trace.append({'cycle':cycle,'status':'COGNITIVE_WITHHOLD_EVIDENCE','thinking':think_e,'intelligence':intel_e});break
        pcs=[];pmap={}
        for args in remaining:
            outs=[]
            for s in hs:
                try:outs.append(canon(execute(s,name,args)))
                except Exception:outs.append('__ERROR__')
            disagree=(len(set(outs))-1)/max(1,len(hs))
            novelty=min([distance(args,z) for z in seed+queried] or [1.0])
            tok='P-'+sha(canon(args))[:16];pmap[tok]=args
            pcs.append(EvidenceCandidate(token=tok,evidence=disagree,complexity=0,risk=0,novelty=novelty))
        ps=NeutralEvidenceProfileSelectorV1.select(pcs,complexity_penalty=0,risk_penalty=.5,novelty_bonus=.05)
        args=pmap[ps['selected_token']];expected=execute(reference,name,args);queried.append(copy.deepcopy(args));known.append((copy.deepcopy(args),expected))
        think_r=core.cognitive_experience_decide('THINKING',{'formal_spec_present':False,'candidate_available':False,'state_known':True})
        intel_r=core.cognitive_experience_decide('INTELLIGENCE',{'reversible':True,'hypothesis_set_present':False,'formal_spec_present':True,'real_source':True,'state_known':True})
        if think_r.get('decision')!='REVISE' or intel_r.get('decision')!='ITERATIVE_REAL_REPAIR':
            trace.append({'cycle':cycle,'status':'COGNITIVE_WITHHOLD_REPAIR','thinking':think_r,'intelligence':intel_r});break
        repair=MultiWholeRepairV2.repair(mutated,name,known,max_candidates=20000,max_edit_depth=2,enabled=('binop','compare','boolop','constant'))
        if repair.get('source'):current=repair['source']
        think_t=core.cognitive_experience_decide('THINKING',{'candidate_available':True,'hypothesis_set_present':False,'formal_spec_present':False,'state_known':True})
        trace.append({'cycle':cycle,'probe_token':ps['selected_token'],'probe_args':args,'expected':expected,
          'hypothesis_count':len(hs),'selected_score':ps['selected_score'],'thinking_evidence':think_e.get('decision'),
          'intelligence_evidence':intel_e.get('decision'),'thinking_repair':think_r.get('decision'),
          'intelligence_repair':intel_r.get('decision'),'thinking_test':think_t.get('decision'),
          'candidate_sha256':sha(current),'edit_depth':repair.get('edit_depth'),'tried':repair.get('tried'),'reason':repair.get('reason')})
        if think_t.get('decision')!='TEST':break
        if MultiWholeRepairV2._passes(current,name,known):
            hs2=hypotheses(mutated,name,known)
            ambiguous=False
            for q in remaining:
                if canon(q)==canon(args):continue
                os=set()
                for s in hs2:
                    try:os.add(canon(execute(s,name,q)))
                    except Exception:os.add('__ERROR__')
                if len(os)>1:ambiguous=True;break
            if not ambiguous:break
    hidden_score=score(current,name,hidden,reference)
    full_score=score(current,name,states,reference)
    logic=core.cognitive_experience_decide('LOGIC',{'result_exact':full_score==1.0,'state_known':True})
    thinking=core.cognitive_experience_decide('THINKING',{'failure_seen':False,'state_known':True}) if full_score==1.0 else core.cognitive_experience_decide('THINKING',{'failure_seen':True,'repair_regressed':False,'state_known':True})
    hidden_set={canon(x) for x in hidden};seen_inputs={canon(x) for x in cal+seed+queried}
    return {'path':meta['path'],'function_name':name,'heritage':meta['heritage'],'reference_source_sha256':sha(reference),
      'domain_count':len(states),'calibration_count':len(cal),'seed_count':len(seed),'probe_pool_count':len(probe),'hidden_count':len(hidden),
      'defect_selector':defect_sel,'mutated_source_sha256':sha(mutated),'mutated_source':mutated,'defect_calibration_score':cal_score,
      'mutated_hidden_score':mutated_hidden,'selected_probe_count':len(queried),'selected_probes':queried,'trace':trace,
      'repaired_source_sha256':sha(current),'repaired_source':current,'repaired_hidden_score':hidden_score,'full_domain_score':full_score,
      'exact_parent_ast_recovered':same_ast(current,reference),'hidden_never_seen':hidden_set.isdisjoint(seen_inputs),
      'logic_final':logic,'thinking_final':thinking,'cognitive_layer_used':True}

episodes=[run_task(t) for t in targets]
restored=[run_task(t) for t in targets]
restore_exact=all(
 a['mutated_source_sha256']==b['mutated_source_sha256'] and
 a['repaired_source_sha256']==b['repaired_source_sha256'] and
 [canon(x) for x in a['selected_probes']]==[canon(x) for x in b['selected_probes']]
 for a,b in zip(episodes,restored)
)
mean_mut=sum(e['mutated_hidden_score'] for e in episodes)/len(episodes)
mean_rep=sum(e['repaired_hidden_score'] for e in episodes)/len(episodes)
mean_gain=mean_rep-mean_mut

gene={'schema':'yado.g2.coding_whole_function_real_repair_gene.v2',
 'gene_id':'GENE-G2-CODING-WHOLE-FUNCTION-REAL-REPAIR-V2-'+digest({'episodes':episodes,'substrate':sub3['substrate_gene']['gene_digest']})[:16],
 'organ':'THINKING','gene_scope':['THINKING','INTELLIGENCE','LOGIC','CODE','MEMORY'],
 'heritage':[whole1['gene_id'],whole1.get('receipt_sha256'),sub3['gene_id'],sub3.get('receipt_sha256'),'RUNTIME-G2-EXPERIENCE-CONDITIONED-COGNITIVE-LAYER-V3'],
 'mechanism_kind':'MULTI_TASK_COMPLETE_REAL_FUNCTION_ACTIVE_COUNTEREXAMPLE_COGNITIVE_REPAIR',
 'whole_function_task_count':len(episodes),'source_file_count':len({e['path'] for e in episodes}),
 'promotion_state':'SHADOW_ONLY'}
gene['gene_digest']=digest(gene)

checks={
 'whole_v1_consumed':True,'substrate_v3_consumed':True,
 'two_whole_functions_executed':len(episodes)==2,
 'two_distinct_source_files':len({e['path'] for e in episodes})==2,
 'all_complete_real_functions':all((REPO/e['path']).exists() for e in episodes),
 'all_shadow_defects_material':all(e['mutated_hidden_score']<=.75 for e in episodes),
 'all_self_selected_probe_used':all(e['selected_probe_count']>=1 for e in episodes),
 'all_cognitive_cycles_observed':all(any(z.get('thinking_evidence')=='SEEK_EVIDENCE' and z.get('intelligence_evidence')=='ACTIVE_EVIDENCE_SEARCH' and z.get('thinking_repair')=='REVISE' and z.get('intelligence_repair')=='ITERATIVE_REAL_REPAIR' and z.get('thinking_test')=='TEST' for z in e['trace']) for e in episodes),
 'all_hidden_never_seen':all(e['hidden_never_seen'] for e in episodes),
 'all_hidden_exact':all(e['repaired_hidden_score']==1.0 for e in episodes),
 'all_full_domain_exact':all(e['full_domain_score']==1.0 for e in episodes),
 'mean_repair_gain_material':mean_gain>=.25,
 'all_final_logic_accept':all(e['logic_final'].get('decision')=='ACCEPT' for e in episodes),
 'all_final_thinking_accept':all(e['thinking_final'].get('decision')=='ACCEPT' for e in episodes),
 'restore_exact':restore_exact and all(b['repaired_hidden_score']==a['repaired_hidden_score'] for a,b in zip(episodes,restored)),
 'host_selected_patch':False,'host_selected_probe':False,'external_coding_model_used':False,
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
 'automatic_canonical_promotion':False
}
false_keys=['host_selected_patch','host_selected_probe','external_coding_model_used','automatic_canonical_promotion']
passed=all(checks[k] is True for k in checks if k not in false_keys) and all(checks[k] is False for k in false_keys)
status='PASS_SHADOW_G2_CODING_WHOLE_FUNCTION_REAL_REPAIR_V2_MULTI_TASK' if passed else 'WITHHOLD_G2_CODING_WHOLE_FUNCTION_REAL_REPAIR_V2_MULTI_TASK'

experience={'schema':'yado.g2.coding_whole_function_real_repair.experience.v2','status':'TRAINED' if passed else 'WITHHOLD',
 'target_set':[{'path':x['path'],'function_name':x['function_name'],'heritage':x['heritage']} for x in targets],
 'episodes':episodes,'restore_episodes':restored,'mean_mutated_hidden_score':mean_mut,'mean_repaired_hidden_score':mean_rep,'mean_repair_gain':mean_gain,
 'whole_function_gene':gene,'canonical_mutation':False,
 'semantic_boundary':'MULTI-TASK BOUNDED COMPLETE-FUNCTION REPAIR ACROSS TWO REAL ACTIVE YADO RUNTIME FILES USING ONE SAFE SHADOW SUBSTRATE AND THE CANONICAL EXPERIENCE-CONDITIONED COGNITIVE LAYER. THIS IS NOT YET MULTI-FUNCTION DEPENDENCY OR MODULE REPAIR.'}
experience['experience_digest']=digest(experience);EXP.parent.mkdir(parents=True,exist_ok=True);EXP.write_text(json.dumps(experience,indent=2,sort_keys=True,default=str)+'\n')
report={'schema':'yado.g2.coding_whole_function_real_repair.v2_multi_task','status':status,
 'task_count':len(episodes),'source_file_count':len({e['path'] for e in episodes}),
 'tasks':[{'path':e['path'],'function_name':e['function_name'],'domain_count':e['domain_count'],'mutated_hidden_score':e['mutated_hidden_score'],
           'repaired_hidden_score':e['repaired_hidden_score'],'full_domain_score':e['full_domain_score'],'selected_probe_count':e['selected_probe_count'],
           'exact_parent_ast_recovered':e['exact_parent_ast_recovered']} for e in episodes],
 'mean_mutated_hidden_score':mean_mut,'mean_repaired_hidden_score':mean_rep,'mean_repair_gain':mean_gain,
 'gene_id':gene['gene_id'],'whole_function_gene':gene,'checks':checks,'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':'G2_CODING_MULTI_FUNCTION_MODULE_REPAIR_V1' if passed else 'G2_CODING_WHOLE_FUNCTION_REAL_REPAIR_V2_REPAIR'}
report['receipt_sha256']=digest(report);OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n')
print(json.dumps({'status':status,'task_count':report['task_count'],'source_file_count':report['source_file_count'],'tasks':report['tasks'],
 'mean_mutated_hidden_score':mean_mut,'mean_repaired_hidden_score':mean_rep,'mean_repair_gain':mean_gain,
 'gene_id':gene['gene_id'],'next_required_capability':report['next_required_capability'],'receipt_sha256':report['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit(2)
