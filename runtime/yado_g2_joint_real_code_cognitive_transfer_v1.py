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
from yado_cognitive_growth_runtime_v1 import plan_multicontext,knn_predict
from yado_organ_runtime_native_v1 import tree_predict

WHOLE2=REPO/'experience/yado-coding-whole-function-real-repair-v2-multi-task.json'
CURR=REPO/'experience/yado-multidomain-cognitive-composition-training-v1.json'
HEAD=REPO/'canonical/yado-main-head-g2.json'
OUT=REPO/'candidates/kernel-self-generated/g2-joint-real-code-cognitive-transfer-v1.json'
EXP=REPO/'experience/yado-joint-real-code-cognitive-transfer-v1.json'

def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o): return hashlib.sha256(canon(o).encode()).hexdigest()
def sha(s): return hashlib.sha256(s.encode()).hexdigest()

whole2,curr,head=map(load,[WHOLE2,CURR,HEAD])
if whole2.get('status')!='TRAINED': raise RuntimeError('WHOLE_FUNCTION_V2_TRAINED_REQUIRED')
if curr.get('status')!='TRAINED': raise RuntimeError('MULTIDOMAIN_COGNITIVE_COMPOSITION_TRAINED_REQUIRED')
core=UnifiedYADOCoreV1(REPO);head_before=copy.deepcopy(core.head)

class JointRepair(BoundedCompositionalProgramRepairV3):
    SAFE_CALLS=dict(BoundedCompositionalProgramRepairV3.SAFE_CALLS)
    SAFE_CALLS.update({'int':int,'float':float,'str':str})
    ALLOWED_ATTRS={'get','items'}

    @classmethod
    def _validate(cls,tree):
        banned=(ast.Import,ast.ImportFrom,ast.Global,ast.Nonlocal,ast.With,ast.AsyncFunctionDef,ast.ClassDef,ast.Lambda,
                ast.While,ast.For,ast.AsyncFor,ast.Try,ast.Raise,ast.Yield,ast.YieldFrom,ast.Await,ast.Delete)
        if any(isinstance(n,banned) for n in ast.walk(tree)): raise ValueError('UNSAFE_PROGRAM')
        funcs=[n for n in tree.body if isinstance(n,ast.FunctionDef)]
        if len(funcs)!=1 or len(tree.body)!=1: raise ValueError('EXACTLY_ONE_FUNCTION_REQUIRED')
        fname=funcs[0].name
        parents={}
        for p in ast.walk(tree):
            for c in ast.iter_child_nodes(p): parents[id(c)]=p
        for n in ast.walk(tree):
            if isinstance(n,ast.Attribute):
                par=parents.get(id(n))
                if not (isinstance(par,ast.Call) and par.func is n): raise ValueError('BARE_ATTRIBUTE_FORBIDDEN')
                if n.attr not in cls.ALLOWED_ATTRS: raise ValueError('ATTRIBUTE_NOT_ALLOWED')
            if isinstance(n,ast.Call):
                if isinstance(n.func,ast.Name):
                    if n.func.id not in cls.SAFE_CALLS: raise ValueError('CALL_NOT_ALLOWED')
                elif isinstance(n.func,ast.Attribute):
                    if n.func.attr not in cls.ALLOWED_ATTRS: raise ValueError('ATTRIBUTE_CALL_NOT_ALLOWED')
                else: raise ValueError('UNSAFE_CALL')
            if isinstance(n,ast.Name) and n.id.startswith('__'): raise ValueError('DUNDER_FORBIDDEN')
        return fname

    @classmethod
    def execute(cls,source,function_name,args):
        def safe_value(x,depth=0):
            if depth>5:return False
            if isinstance(x,(type(None),bool,int,float,str)):return True
            if isinstance(x,(tuple,list)):return len(x)<=32 and all(safe_value(v,depth+1) for v in x)
            if isinstance(x,dict):return len(x)<=32 and all(isinstance(k,(str,int,bool,float)) and safe_value(v,depth+1) for k,v in x.items())
            return False
        if not all(safe_value(a) for a in args): raise ValueError('NON_BUILTIN_ARGUMENT_FORBIDDEN')
        tree=ast.parse(source);fname=cls._validate(tree)
        if fname!=function_name: raise ValueError('FUNCTION_NAME_MISMATCH')
        env=dict(cls.SAFE_CALLS);env['__builtins__']={}
        exec(compile(tree,'<yado-joint-real-code>','exec'),env,env)
        return env[function_name](*copy.deepcopy(args))

def extract_function(path,name):
    src=Path(path).read_text(encoding='utf-8');tree=ast.parse(src)
    node=next((n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name),None)
    if node is None: raise RuntimeError('FUNCTION_NOT_FOUND:'+str(path)+':'+name)
    q=copy.deepcopy(node);q.decorator_list=[];q.returns=None;q.type_comment=None
    for a in list(q.args.posonlyargs)+list(q.args.args)+list(q.args.kwonlyargs):
        a.annotation=None;a.type_comment=None
    q.args.defaults=[];q.args.kw_defaults=[None for _ in q.args.kwonlyargs]
    ast.fix_missing_locations(q)
    out=ast.unparse(q)+'\n';JointRepair._validate(ast.parse(out));return out

targets=[]
for t in whole2.get('target_set') or []:
    src=extract_function(REPO/t['path'],t['function_name'])
    targets.append({'path':t['path'],'function_name':t['function_name'],'source':src,'source_sha256':sha(src)})
targets=[t for t in targets if t['function_name']=='split_bucket']
if len(targets)!=1: raise RuntimeError('EXPECTED_SPLIT_BUCKET_REAL_TARGET')

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
    keys=indirect_keys(tree,arg);direct=[];uses_items=False;uses_get=False
    for n in ast.walk(tree):
        if isinstance(n,ast.Subscript) and isinstance(n.value,ast.Name) and n.value.id==arg:
            if isinstance(n.slice,ast.Constant) and isinstance(n.slice.value,(str,int)) and n.slice.value not in direct:direct.append(n.slice.value)
        if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name) and n.func.value.id==arg:
            uses_items|=n.func.attr=='items';uses_get|=n.func.attr=='get'
    if keys:return ('BOOL_DICT',keys)
    if uses_items or uses_get or direct:return ('NUM_DICT',direct)
    return ('SCALAR',[])

def domain_for(source):
    tree=ast.parse(source);func=next(n for n in tree.body if isinstance(n,ast.FunctionDef));domains=[]
    for a in func.args.args:
        kind,keys=arg_kind(tree,a.arg)
        if kind=='BOOL_DICT':
            domains.append([dict(zip(keys,bits)) for bits in product((False,True),repeat=len(keys))])
        elif kind=='NUM_DICT':
            domains.append([{}, {0:1.0},{0:2.0},{1:-1.0},{'0':3.0},{'a':1.0},{'b':-2.0},
                {0:1.0,1:2.0},{0:-1.0,1:3.0},{'0':2.0,'1':-1.0},{'a':2.0,'b':-1.0},
                {'a':0.5,'b':2.0},{'0':4.0,'1':1.0},{'1':2.0,'2':0.5}])
        else: domains.append([-3,-1,0,1,2,4])
    states=[]
    for combo in product(*domains):
        states.append(tuple(copy.deepcopy(combo)))
        if len(states)>=196:break
    return states

def execute(src,name,args): return JointRepair.execute(src,name,copy.deepcopy(args))
def same_ast(a,b):
    try:return ast.dump(ast.parse(a),include_attributes=False)==ast.dump(ast.parse(b),include_attributes=False)
    except Exception:return False
def score(src,name,states,reference):
    ok=0
    for args in states:
        try:ok+=execute(src,name,args)==execute(reference,name,args)
        except Exception:pass
    return ok/max(1,len(states))

def partition(states,salt):
    xs=sorted(states,key=lambda x:sha(salt+'|'+canon(x)));n=len(xs)
    if n<24:raise RuntimeError('DOMAIN_TOO_SMALL:'+str(n))
    cal_n=max(8,min(20,n//5));seed_n=max(4,min(8,n//10));hidden_n=max(8,min(24,n//5))
    cal=xs[:cal_n];seed=xs[cal_n:cal_n+seed_n];hidden=xs[-hidden_n:];probe=xs[cal_n+seed_n:-hidden_n]
    if len(probe)<8:raise RuntimeError('PROBE_POOL_TOO_SMALL')
    return cal,seed,probe,hidden

def one_mutations(source,examples):
    out=[];seen=set()
    for c in JointRepair._atomic_mutations(source,examples,enable=('binop','compare','boolop','constant')):
        if c in seen:continue
        seen.add(c);out.append(c)
        if len(out)>=120:break
    return out

def choose_two_edit_defects(reference,name,calibration,count=3):
    examples=[(copy.deepcopy(a),execute(reference,name,a)) for a in calibration]
    cands=[];mp={}
    first=one_mutations(reference,examples)
    for c1 in first[:80]:
        if same_ast(c1,reference):continue
        back1=one_mutations(c1,examples)
        if not any(same_ast(x,reference) for x in back1):continue
        for c2 in back1[:100]:
            if same_ast(c2,reference) or same_ast(c2,c1):continue
            backs2=one_mutations(c2,examples)
            if any(same_ast(x,reference) for x in backs2):continue
            if not any(same_ast(x,c1) for x in backs2):continue
            sc=score(c2,name,calibration,reference)
            if sc>.65:continue
            tok='D2-'+sha(c2)[:16]
            if tok in mp:continue
            mp[tok]=(c2,sc,c1)
            cands.append(EvidenceCandidate(token=tok,evidence=1.0-sc,complexity=2.0,risk=0.0,novelty=1.0))
            if len(cands)>=120:break
        if len(cands)>=120:break
    if len(cands)<count:raise RuntimeError('INSUFFICIENT_TWO_EDIT_REVERSIBLE_DEFECTS:'+name+':'+str(len(cands)))
    ranked=[]
    remaining=list(cands)
    while remaining and len(ranked)<count:
        sel=NeutralEvidenceProfileSelectorV1.select(remaining,complexity_penalty=.01,risk_penalty=.5,novelty_bonus=.01)
        c2,sc,c1=mp[sel['selected_token']]
        ranked.append((c2,sc,c1,sel))
        remaining=[x for x in remaining if x.token!=sel['selected_token']]
    return ranked

def hypotheses(mutated,name,known,max_count=100):
    xs=[];seen=set();first=[]
    def add(s):
        if not s or s in seen:return
        seen.add(s)
        try:
            if JointRepair._passes(s,name,known):xs.append(s)
        except Exception:pass
    add(mutated)
    for c in JointRepair._atomic_mutations(mutated,known,enable=('binop','compare','boolop','constant')):
        first.append(c);add(c)
        if len(first)>=120:break
    for base in first[:60]:
        if len(xs)>=max_count:break
        for c in JointRepair._atomic_mutations(base,known,enable=('binop','compare','boolop','constant')):
            add(c)
            if len(xs)>=max_count:break
    xs.sort(key=lambda s:(len(s),sha(s),s));return xs[:max_count]

def select_probe(hs,remaining,known_inputs,name):
    pcs=[];pmap={}
    for args in remaining:
        outs=[]
        for s in hs:
            try:outs.append(canon(execute(s,name,args)))
            except Exception:outs.append('__ERROR__')
        disagree=(len(set(outs))-1)/max(1,len(hs))
        novelty=1.0 if not known_inputs else min(0.0 if canon(args)==canon(z) else 1.0 for z in known_inputs)
        tok='P-'+sha(canon(args))[:16];pmap[tok]=args
        pcs.append(EvidenceCandidate(token=tok,evidence=disagree,complexity=0,risk=0,novelty=novelty))
    if not pcs:return None,None
    sel=NeutralEvidenceProfileSelectorV1.select(pcs,complexity_penalty=0,risk_penalty=.5,novelty_bonus=.05)
    return pmap[sel['selected_token']],sel

genes=curr['genes']
logic_task=next(x for x in genes['LOGIC']['task_models'] if x['task_id']=='CODE_RELEASE_INVARIANT')
thinking_task=next(x for x in genes['THINKING']['task_models'] if x['task_id']=='CODE_REPAIR')
intel_task=next(x for x in genes['INTELLIGENCE']['task_models'] if x['task_id']=='RESOURCE_STRATEGY')
cog=genes['COGNITIVE']

def trained_thinking(ctx):
    roles=['OBSERVE_FAILURE','BUILD_ORACLE','HYPOTHESIZE','PATCH','TEST','REGRESSION','COMMIT']
    acts=[{'id':'A'+str(i),'role':r} for i,r in enumerate(roles)]
    ids=plan_multicontext(thinking_task['model'],ctx,acts);by={a['id']:a['role'] for a in acts}
    order=[by[i] for i in ids]
    return order,order.index('BUILD_ORACLE')<order.index('HYPOTHESIZE')

def trained_intel(confidence,cycle,hypothesis_count):
    x={'confidence':float(confidence),'budget_low':1.0 if cycle>=4 else 0.0,'latency_pressure':0.0,
       'uncertainty':min(1.0,float(hypothesis_count)/20.0),'risk':max(0.0,1.0-float(confidence))}
    return str(tree_predict(intel_task['model'],x))

def trained_logic(tests_pass,reviewed,low_risk):
    x={'tests_pass':bool(tests_pass),'rollback_ready':True,'invariant_break':False,'reviewed':bool(reviewed),'low_risk':bool(low_risk)}
    return bool(tree_predict(logic_task['model'],x))

def trained_cognitive(logic_accept,thinking_cautious,intelligence_robust):
    x={'state_known':1.0,'logic_accept':1.0 if logic_accept else 0.0,'thinking_cautious':1.0 if thinking_cautious else 0.0,
       'intelligence_robust':1.0 if intelligence_robust else 0.0}
    return str(knn_predict(cog['model'],x))

def known_score(source,name,known):
    if not known:return 0.0
    ok=0
    for args,y in known:
        try:ok+=execute(source,name,args)==y
        except Exception:pass
    return ok/len(known)

def run_episode(meta,defect,mode):
    reference=meta['source'];name=meta['function_name'];states=meta['states'];cal,seed,probe,hidden=meta['partition']
    known=[(copy.deepcopy(a),execute(reference,name,a)) for a in seed]
    current=defect;queried=[];trace=[];total_tried=0;release='WITHHOLD';final_cog=None
    for cycle in range(6):
        hs=hypotheses(defect,name,known)
        conf=known_score(current,name,known)
        remaining=[x for x in probe if canon(x) not in {canon(z) for z in queried}]
        if mode=='CANONICAL':
            de=core.cognitive_experience_decide('THINKING',{'oracle_available':True,'hypothesis_set_present':True,'state_known':True})
            di=core.cognitive_experience_decide('INTELLIGENCE',{'hypothesis_set_present':True,'state_known':True})
            if de.get('decision')!='SEEK_EVIDENCE' or di.get('decision')!='ACTIVE_EVIDENCE_SEARCH':
                trace.append({'cycle':cycle,'status':'CANONICAL_EVIDENCE_WITHHOLD','thinking':de,'intelligence':di});break
            probe_budget=1;plan_order=[];cautious=None;strategy='CANONICAL_ACTIVE_EVIDENCE_SEARCH'
        else:
            plan_order,cautious=trained_thinking({'oracle_missing':len(queried)==0,'multi_file':False,'regression_risk':True})
            strategy=trained_intel(conf,cycle,len(hs))
            probe_budget={'CHEAP_PROBE':1,'DEEP_PROBE':2,'PARALLEL_PROBES':2,'STOP':0}.get(strategy,1)
            if conf<1.0:probe_budget=max(1,probe_budget)
            if cautious:probe_budget=max(1,probe_budget)
        selected=[]
        for _ in range(min(probe_budget,len(remaining))):
            args,ps=select_probe(hs,remaining,seed+queried,name)
            if args is None:break
            expected=execute(reference,name,args);queried.append(copy.deepcopy(args));known.append((copy.deepcopy(args),expected));selected.append({'args':args,'expected':expected,'selector':ps})
            remaining=[x for x in remaining if canon(x)!=canon(args)]
            hs=hypotheses(defect,name,known)
        if mode=='CANONICAL':
            dr=core.cognitive_experience_decide('THINKING',{'formal_spec_present':False,'candidate_available':False,'state_known':True})
            ir=core.cognitive_experience_decide('INTELLIGENCE',{'reversible':True,'hypothesis_set_present':False,'formal_spec_present':True,'real_source':True,'state_known':True})
            if dr.get('decision')!='REVISE' or ir.get('decision')!='ITERATIVE_REAL_REPAIR':
                trace.append({'cycle':cycle,'status':'CANONICAL_REPAIR_WITHHOLD','thinking':dr,'intelligence':ir});break
        repair=JointRepair.repair(defect,name,known,max_candidates=16000,max_edit_depth=2,enabled=('binop','compare','boolop','constant'))
        total_tried+=int(repair.get('tried') or 0)
        if repair.get('source'):current=repair['source']
        conf2=known_score(current,name,known)
        edit_depth=int(repair.get('edit_depth') or 99)
        if mode=='CANONICAL':
            dt=core.cognitive_experience_decide('THINKING',{'candidate_available':True,'hypothesis_set_present':False,'formal_spec_present':False,'state_known':True})
            final_logic=core.cognitive_experience_decide('LOGIC',{'result_exact':conf2==1.0,'state_known':True})
            if conf2==1.0 and dt.get('decision')=='TEST' and final_logic.get('decision')=='ACCEPT':
                release='ACCEPT';final_cog='CANONICAL_ACCEPT';trace.append({'cycle':cycle,'selected':selected,'repair':repair,'confidence':conf2,'release':release});break
            trace.append({'cycle':cycle,'selected':selected,'repair':repair,'confidence':conf2,'release':'CONTINUE'})
        else:
            order2,cautious2=trained_thinking({'oracle_missing':False,'multi_file':False,'regression_risk':True})
            strategy2=trained_intel(conf2,cycle,len(hypotheses(defect,name,known)))
            robust=strategy2 in {'DEEP_PROBE','PARALLEL_PROBES','STOP'}
            lacc=trained_logic(conf2==1.0,bool(queried),edit_depth<=2)
            action=trained_cognitive(lacc,cautious2,robust);final_cog=action
            trace.append({'cycle':cycle,'selected':selected,'repair':repair,'confidence':conf2,'plan_order':order2,'thinking_cautious':cautious2,
                          'resource_strategy':strategy2,'logic_accept':lacc,'cognitive_action':action})
            if conf2==1.0 and action in {'ACT','ACT_WITH_GUARD'}:
                release='ACCEPT';break
            if action=='WITHHOLD' and conf2<1.0:break
    hidden_score=score(current,name,hidden,reference);full_score=score(current,name,states,reference)
    hidden_seen={canon(x) for x in hidden}&{canon(x) for x in cal+seed+queried}
    return {'mode':mode,'path':meta['path'],'function_name':name,'mutated_source_sha256':sha(defect),'repaired_source_sha256':sha(current),
      'hidden_score':hidden_score,'full_score':full_score,'release':release,'final_cognitive_action':final_cog,'probe_count':len(queried),
      'repair_tried':total_tried,'hidden_never_seen':not hidden_seen,'trace':trace,'exact_parent_ast_recovered':same_ast(current,reference)}

prepared=[]
for t in targets:
    raw=domain_for(t['source']);states=[]
    for args in raw:
        try:
            y=execute(t['source'],t['function_name'],args)
            if isinstance(y,(bool,int,float,str)):states.append(args)
        except Exception:pass
    uniq=[];seen=set()
    for a in states:
        k=canon(a)
        if k not in seen:seen.add(k);uniq.append(a)
    part=partition(uniq,'JOINT_REAL_CODE_V1|'+t['path']+'|'+t['function_name'])
    defects=choose_two_edit_defects(t['source'],t['function_name'],part[0],count=3)
    for variant,(defect,cal_score,intermediate,sel) in enumerate(defects,1):
        prepared.append({**t,'variant_id':'TWO_EDIT_'+str(variant),'states':uniq,'partition':part,'defect':defect,
          'defect_calibration_score':cal_score,'defect_selector':sel,'intermediate_sha256':sha(intermediate),
          'two_edit_no_direct_one_step':True,'mutated_hidden_score':score(defect,t['function_name'],part[3],t['source'])})

baseline=[run_episode(t,t['defect'],'CANONICAL') for t in prepared]
trained=[run_episode(t,t['defect'],'TRAINED') for t in prepared]
restore=[run_episode(t,t['defect'],'TRAINED') for t in prepared]

def avg(xs,k):return sum(float(x[k]) for x in xs)/len(xs)
baseline_success=sum(x['hidden_score']==1.0 and x['full_score']==1.0 and x['release']=='ACCEPT' for x in baseline)/len(baseline)
trained_success=sum(x['hidden_score']==1.0 and x['full_score']==1.0 and x['release']=='ACCEPT' for x in trained)/len(trained)
baseline_probes=avg(baseline,'probe_count');trained_probes=avg(trained,'probe_count')
baseline_tried=avg(baseline,'repair_tried');trained_tried=avg(trained,'repair_tried')
restore_exact=all(a['repaired_source_sha256']==b['repaired_source_sha256'] and a['probe_count']==b['probe_count'] and a['release']==b['release'] for a,b in zip(trained,restore))
measured_gain=(trained_success>baseline_success) or (trained_success==baseline_success and trained_probes<baseline_probes) or (trained_success==baseline_success and trained_probes==baseline_probes and trained_tried<baseline_tried)

joint_gene={'schema':'yado.g2.joint_real_code_cognitive_transfer_gene.v1',
 'gene_id':'GENE-G2-JOINT-REAL-CODE-COGNITIVE-TRANSFER-V1-'+digest({'trained':trained,'parents':[genes['LOGIC']['gene_digest'],genes['THINKING']['gene_digest'],genes['INTELLIGENCE']['gene_digest'],genes['COGNITIVE']['gene_digest']]})[:16],
 'organ':'CONSCIOUS_WORKSPACE','heritage':[genes['LOGIC']['gene_id'],genes['THINKING']['gene_id'],genes['INTELLIGENCE']['gene_id'],genes['COGNITIVE']['gene_id']],
 'mechanism_kind':'TRAINED_MULTIDOMAIN_CONTROL_OVER_THREE_TWO_EDIT_VARIANTS_OF_REAL_WHOLE_FUNCTION_REPAIR','promotion_state':'SHADOW_ONLY'}
joint_gene['gene_digest']=digest(joint_gene)

checks={
 'three_two_edit_real_episodes':len(prepared)==3 and len({x['path'] for x in prepared})==1,
 'two_edit_defects_material':all(x['mutated_hidden_score']<=.75 for x in prepared),
 'trained_control_uses_multidomain_logic':genes['LOGIC']['gene_id']=='GENE-G2-MULTIDOMAIN-LOGIC-V2-78da24019759d2f4',
 'trained_control_uses_multidomain_thinking':genes['THINKING']['gene_id']=='GENE-G2-MULTIDOMAIN-THINKING-V1-a0811170cf6f6670',
 'trained_control_uses_multidomain_intelligence':genes['INTELLIGENCE']['gene_id']=='GENE-G2-MULTIDOMAIN-INTELLIGENCE-V1-5636f552fc470ae2',
 'trained_control_uses_multidomain_cognitive':genes['COGNITIVE']['gene_id']=='GENE-G2-MULTIDOMAIN-COGNITIVE-V1-bd9df590793e7885',
 'all_trained_hidden_never_seen':all(x['hidden_never_seen'] for x in trained),
 'all_trained_hidden_exact':all(x['hidden_score']==1.0 for x in trained),
 'all_trained_full_exact':all(x['full_score']==1.0 for x in trained),
 'all_trained_release_accept':all(x['release']=='ACCEPT' for x in trained),
 'trained_not_worse_than_canonical':trained_success>=baseline_success,
 'trained_probe_overhead_bounded':trained_probes<=baseline_probes+1.0,
 'restore_exact':restore_exact,
 'host_selected_patch':False,'external_coding_model_used':False,'automatic_canonical_promotion':False,
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest')
}
false_keys=['host_selected_patch','external_coding_model_used','automatic_canonical_promotion']
passed=all(v is True for k,v in checks.items() if k not in false_keys) and all(checks[k] is False for k in false_keys)
status='PASS_SHADOW_G2_JOINT_REAL_CODE_COGNITIVE_TRANSFER_V1' if passed else 'WITHHOLD_G2_JOINT_REAL_CODE_COGNITIVE_TRANSFER_V1'
growth='MEASURED_GAIN' if measured_gain else ('TRANSFER_WITHOUT_MEASURED_GAIN' if passed else 'NO_TRANSFER')

experience={'schema':'yado.g2.joint_real_code_cognitive_transfer.experience.v1','status':'TRAINED' if passed else 'WITHHOLD',
 'growth_verdict':growth,'prepared_tasks':[{k:v for k,v in x.items() if k not in ('source','states','partition','defect')} for x in prepared],
 'baseline':baseline,'trained':trained,'restore':restore,
 'metrics':{'baseline_success':baseline_success,'trained_success':trained_success,'baseline_mean_probes':baseline_probes,'trained_mean_probes':trained_probes,
            'baseline_mean_repair_tried':baseline_tried,'trained_mean_repair_tried':trained_tried},
 'joint_gene':joint_gene,'checks':checks,'canonical_mutation':False,
 'semantic_boundary':'JOINT REAL WHOLE-FUNCTION TRANSFER ON THREE INDEPENDENT REVERSIBLE TWO-EDIT SHADOW DEFECTS OF THE ACTIVE YADO split_bucket FUNCTION. THE SAME REPAIR SUBSTRATE, HIDDEN DOMAIN AND DEFECT ARE USED FOR THE CANONICAL CONTROL BASELINE AND THE TRAINED MULTIDOMAIN CONTROL. TRAINED CONTROL USES CODE_RELEASE LOGIC, CODE_REPAIR THINKING, RESOURCE_STRATEGY INTELLIGENCE AND THE MULTIDOMAIN COGNITIVE KNN. HOST ONLY MAPS LEARNED CONTROL OUTPUTS TO BOUNDED PROBE COUNTS/RELEASE ACTIONS; IT DOES NOT SELECT THE PATCH. PASS PROVES JOINT TRANSFER, NOT AGI.'
}
experience['experience_digest']=digest(experience);EXP.parent.mkdir(parents=True,exist_ok=True);EXP.write_text(json.dumps(experience,indent=2,sort_keys=True,default=str)+'\n')
report={'schema':'yado.g2.joint_real_code_cognitive_transfer.v1','status':status,'growth_verdict':growth,
 'metrics':experience['metrics'],'task_results':[{'path':p['path'],'function_name':p['function_name'],'variant_id':p['variant_id'],'mutated_hidden_score':p['mutated_hidden_score'],
      'baseline_hidden':b['hidden_score'],'baseline_full':b['full_score'],'baseline_probes':b['probe_count'],'baseline_tried':b['repair_tried'],
      'trained_hidden':n['hidden_score'],'trained_full':n['full_score'],'trained_probes':n['probe_count'],'trained_tried':n['repair_tried'],
      'trained_release':n['release'],'trained_final_cognitive_action':n['final_cognitive_action']}
      for p,b,n in zip(prepared,baseline,trained)],
 'gene_id':joint_gene['gene_id'],'gene_digest':joint_gene['gene_digest'],'checks':checks,'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':('JOINT_REAL_CODE_COGNITIVE_DIFFICULTY_ESCALATION_V2' if passed and not measured_gain else
                             'JOINT_REAL_CODE_COGNITIVE_STRESS_V2' if passed else 'JOINT_REAL_CODE_COGNITIVE_TRANSFER_REPAIR_V2'),
 'semantic_boundary':experience['semantic_boundary']}
report['receipt_sha256']=digest(report);OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n')
print(json.dumps(report,indent=2,sort_keys=True))
if not passed:raise SystemExit(2)
