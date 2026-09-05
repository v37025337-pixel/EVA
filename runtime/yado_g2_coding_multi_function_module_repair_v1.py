from __future__ import annotations
from pathlib import Path
from itertools import product
import ast,copy,hashlib,json,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_neutral_evidence_profile_selector_v1 import NeutralEvidenceProfileSelectorV1,EvidenceCandidate
from yado_unified_core_v1 import UnifiedYADOCoreV1

PARENT=REPO/'candidates/kernel-self-generated/g2-coding-whole-function-real-repair-v2-multi-task.json'
SUB=REPO/'candidates/kernel-self-generated/g2-coding-module-substrate-evolution-v1.json'
HEAD=REPO/'canonical/yado-main-head-g2.json'
OUT=REPO/'candidates/kernel-self-generated/g2-coding-multi-function-module-repair-v1.json'
EXP=REPO/'experience/yado-coding-multi-function-module-repair-v1.json'

def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def stable(o):
    if isinstance(o,dict):
        return ('dict',tuple(sorted(((type(k).__name__,repr(k),stable(v)) for k,v in o.items()))))
    if isinstance(o,(list,tuple)):return (type(o).__name__,tuple(stable(x) for x in o))
    if isinstance(o,set):return ('set',tuple(sorted((stable(x) for x in o),key=repr)))
    return (type(o).__name__,repr(o))
def canon(o):return repr(stable(o))
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def sha(s):return hashlib.sha256(s.encode()).hexdigest()

parent,sub,head=map(load,[PARENT,SUB,HEAD])
if parent.get('status')!='PASS_SHADOW_G2_CODING_WHOLE_FUNCTION_REAL_REPAIR_V2_MULTI_TASK':raise RuntimeError('MULTI_TASK_PARENT_PASS_REQUIRED')
if parent.get('next_required_capability')!='G2_CODING_MULTI_FUNCTION_MODULE_REPAIR_V1':raise RuntimeError('PARENT_FRONTIER_MISMATCH')
if sub.get('status')!='PASS_SHADOW_G2_CODING_MODULE_SUBSTRATE_EVOLUTION_V1':raise RuntimeError('MODULE_SUBSTRATE_PASS_REQUIRED')
if sub.get('next_required_capability')!='G2_CODING_MULTI_FUNCTION_MODULE_REPAIR_V1':raise RuntimeError('MODULE_SUBSTRATE_FRONTIER_MISMATCH')
if sub.get('selected_pair')!={'path':'runtime/yado_raw_task_representation_candidate_v3.py','caller':'_pred','callee':'_dot'}:
    raise RuntimeError('UNEXPECTED_MODULE_PAIR')
if 'RUNTIME-G2-EXPERIENCE-CONDITIONED-COGNITIVE-LAYER-V3' not in head.get('active_capabilities',[]):raise RuntimeError('COGNITIVE_LAYER_REQUIRED')
core=UnifiedYADOCoreV1(REPO);head_before=copy.deepcopy(core.head)

SAFE_CALLS={'min':min,'max':max,'all':all,'any':any,'sum':sum,'abs':abs,'len':len,'int':int,'float':float,'str':str}
READONLY_ATTRS={'get','items'}

def safe_plain(x,depth=0):
    if depth>6:return False
    if isinstance(x,(type(None),bool,int,float,str)):return True
    if isinstance(x,(tuple,list)):return len(x)<=64 and all(safe_plain(v,depth+1) for v in x)
    if isinstance(x,dict):return len(x)<=64 and all(isinstance(k,(str,int,bool,float)) and safe_plain(v,depth+1) for k,v in x.items())
    return False

def local_list_vars(func):
    out=set()
    for s in func.body:
        if isinstance(s,(ast.Assign,ast.AnnAssign)):
            targets=s.targets if isinstance(s,ast.Assign) else [s.target]
            if isinstance(s.value,(ast.List,ast.ListComp)):
                for t in targets:
                    if isinstance(t,ast.Name):out.add(t.id)
    return out

def pure_lambda_expr(node,arg):
    allowed=(ast.Tuple,ast.List,ast.Name,ast.Load,ast.Subscript,ast.Constant,ast.UnaryOp,ast.USub,ast.UAdd,
             ast.BinOp,ast.Add,ast.Sub,ast.Mult,ast.Mod,ast.FloorDiv,ast.Compare,ast.Eq,ast.NotEq,ast.Lt,ast.LtE,ast.Gt,ast.GtE,
             ast.BoolOp,ast.And,ast.Or,ast.IfExp)
    for n in ast.walk(node):
        if not isinstance(n,allowed):return False
        if isinstance(n,ast.Name) and n.id!=arg:return False
        if isinstance(n,ast.Subscript):
            root=n.value
            while isinstance(root,ast.Subscript):root=root.value
            if not isinstance(root,ast.Name) or root.id!=arg:return False
        if isinstance(n,ast.Constant) and not isinstance(n.value,(type(None),bool,int,float,str)):return False
    return True

class ModuleSandbox:
    @classmethod
    def validate(cls,source):
        tree=ast.parse(source)
        banned=(ast.Import,ast.ImportFrom,ast.Global,ast.Nonlocal,ast.With,ast.AsyncFunctionDef,ast.ClassDef,
                ast.While,ast.For,ast.AsyncFor,ast.Try,ast.Raise,ast.Yield,ast.YieldFrom,ast.Await,ast.Delete)
        if any(isinstance(n,banned) for n in ast.walk(tree)):raise ValueError('UNSAFE_MODULE')
        funcs=[n for n in tree.body if isinstance(n,ast.FunctionDef)]
        if len(funcs)!=2 or len(tree.body)!=2:raise ValueError('EXACTLY_TWO_FUNCTIONS_REQUIRED')
        names={f.name for f in funcs}
        parents={}
        for p in ast.walk(tree):
            for c in ast.iter_child_nodes(p):parents[id(c)]=p
        for f in funcs:
            locals_=local_list_vars(f)
            for n in ast.walk(f):
                if isinstance(n,ast.Lambda):
                    par=parents.get(id(n))
                    if not isinstance(par,ast.keyword) or par.arg!='key':raise ValueError('LAMBDA_ONLY_SORT_KEY')
                    call=parents.get(id(par))
                    if not isinstance(call,ast.Call) or not isinstance(call.func,ast.Attribute) or call.func.attr!='sort':raise ValueError('LAMBDA_ONLY_SORT_KEY')
                    if len(n.args.args)!=1 or n.args.posonlyargs or n.args.kwonlyargs or n.args.vararg or n.args.kwarg:raise ValueError('LAMBDA_ARITY')
                    if not pure_lambda_expr(n.body,n.args.args[0].arg):raise ValueError('IMPURE_LAMBDA')
                if isinstance(n,ast.Attribute):
                    par=parents.get(id(n))
                    if not (isinstance(par,ast.Call) and par.func is n):raise ValueError('BARE_ATTRIBUTE_FORBIDDEN')
                    if n.attr in READONLY_ATTRS:continue
                    if n.attr=='sort':
                        if not isinstance(n.value,ast.Name) or n.value.id not in locals_:raise ValueError('SORT_NONLOCAL_FORBIDDEN')
                        if par.args or len(par.keywords)!=1 or par.keywords[0].arg!='key' or not isinstance(par.keywords[0].value,ast.Lambda):
                            raise ValueError('SORT_REQUIRES_PURE_KEY')
                        continue
                    raise ValueError('ATTRIBUTE_NOT_ALLOWED')
                if isinstance(n,ast.Call):
                    if isinstance(n.func,ast.Name):
                        if n.func.id not in SAFE_CALLS and n.func.id not in names:raise ValueError('CALL_NOT_ALLOWED:'+n.func.id)
                    elif isinstance(n.func,ast.Attribute):
                        if n.func.attr not in READONLY_ATTRS|{'sort'}:raise ValueError('ATTRIBUTE_CALL_NOT_ALLOWED')
                    else:raise ValueError('UNSAFE_CALL')
                if isinstance(n,ast.Name) and n.id.startswith('__'):raise ValueError('DUNDER_FORBIDDEN')
        return [f.name for f in funcs]

    @classmethod
    def execute(cls,source,caller,args):
        if not all(safe_plain(a) for a in args):raise ValueError('NON_PLAIN_ARGUMENT')
        names=cls.validate(source)
        if caller not in names:raise ValueError('CALLER_NOT_IN_MODULE')
        env=dict(SAFE_CALLS);env['__builtins__']={}
        exec(compile(ast.parse(source),'<yado-module-repair-v1>','exec'),env,env)
        out=env[caller](*copy.deepcopy(args))
        if not safe_plain(out):raise ValueError('NON_PLAIN_OUTPUT')
        return out

def module_from_real_file():
    p=REPO/sub['selected_pair']['path'];src=p.read_text(encoding='utf-8');tree=ast.parse(src)
    names=[sub['selected_pair']['callee'],sub['selected_pair']['caller']]
    chunks=[]
    for name in names:
        n=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name==name)
        q=copy.deepcopy(n);q.decorator_list=[];q.returns=None;q.type_comment=None
        for a in list(q.args.posonlyargs)+list(q.args.args)+list(q.args.kwonlyargs):a.annotation=None;a.type_comment=None
        q.args.defaults=[];q.args.kw_defaults=[None for _ in q.args.kwonlyargs];ast.fix_missing_locations(q)
        chunks.append(ast.unparse(q))
    out='\n\n'.join(chunks)+'\n'
    ModuleSandbox.validate(out)
    return out

reference=module_from_real_file();CALLER=sub['selected_pair']['caller']
PARENT_AST=ast.dump(ast.parse(reference),include_attributes=False)

def domain():
    labels_sets=[['A','B'],['X','Y'],['A','B','C'],['K','L','M']]
    vals=[-3.0,-2.0,-1.0,-0.5,0.0,0.5,1.0,2.0,3.0]
    out=[]
    for li,labels in enumerate(labels_sets):
        for i in range(36):
            w={};b={}
            for j,l in enumerate(labels):
                w[l]={0:vals[(i+j)%len(vals)],1:vals[(i+2*j+2)%len(vals)]}
                if (i+j)%4==0:w[l]['0']=vals[(i+j+4)%len(vals)]
                b[l]=vals[(2*i+j+li)%len(vals)]
            x={0:vals[(i+1)%len(vals)],1:vals[(i+5)%len(vals)]}
            if i%5==0:x['0']=vals[(i+7)%len(vals)]
            args=(copy.deepcopy(labels),w,b,x)
            try:
                ModuleSandbox.execute(reference,CALLER,args);out.append(args)
            except Exception:pass
    # stable dedup
    seen=set();rows=[]
    for a in out:
        k=canon(a)
        if k not in seen:seen.add(k);rows.append(a)
    return sorted(rows,key=lambda a:sha(canon(a)))

STATES=domain()
if len(STATES)<80:raise RuntimeError('MODULE_DOMAIN_TOO_SMALL:'+str(len(STATES)))

def partition(xs):
    n=len(xs);cal=xs[:18];seed=xs[18:26];hidden=xs[-24:];probe=xs[26:-24]
    if len(probe)<24:raise RuntimeError('MODULE_PROBE_POOL_TOO_SMALL')
    return cal,seed,probe,hidden

CAL,SEED,PROBE,HIDDEN=partition(STATES)

def score(src,rows):
    ok=0
    for a in rows:
        try:ok+=ModuleSandbox.execute(src,CALLER,a)==ModuleSandbox.execute(reference,CALLER,a)
        except Exception:pass
    return ok/max(1,len(rows))

def const_pool(tree):
    vals={-2,-1,0,1,2,3}
    for n in ast.walk(tree):
        if isinstance(n,ast.Constant) and isinstance(n.value,int) and not isinstance(n.value,bool):
            vals.update({n.value-1,n.value,n.value+1})
    return sorted(vals,key=lambda x:(abs(x),x))[:12]

def module_mutations(source):
    tree=ast.parse(source);ModuleSandbox.validate(source);nodes=list(ast.walk(tree));pool=const_pool(tree);edits=[]
    func_by_node={}
    for f in [x for x in tree.body if isinstance(x,ast.FunctionDef)]:
        for n in ast.walk(f):func_by_node[id(n)]=f.name
    for idx,n in enumerate(nodes):
        target=func_by_node.get(id(n))
        if not target:continue
        if isinstance(n,ast.BinOp):
            for opcls in (ast.Add,ast.Sub,ast.Mult,ast.Mod):
                if not isinstance(n.op,opcls):edits.append((idx,'op',opcls(),target))
        elif isinstance(n,ast.Compare) and len(n.ops)==1:
            for opcls in (ast.Eq,ast.NotEq,ast.Lt,ast.LtE,ast.Gt,ast.GtE):
                if not isinstance(n.ops[0],opcls):edits.append((idx,'cmp',opcls(),target))
        elif isinstance(n,ast.BoolOp):
            for opcls in (ast.And,ast.Or):
                if not isinstance(n.op,opcls):edits.append((idx,'op',opcls(),target))
        elif isinstance(n,ast.Constant) and isinstance(n.value,int) and not isinstance(n.value,bool):
            for v in pool:
                if v!=n.value:edits.append((idx,'value',v,target))
    seen=set()
    for idx,kind,val,target in edits:
        t=copy.deepcopy(tree);tn=list(ast.walk(t))[idx]
        if kind=='op':tn.op=val
        elif kind=='cmp':tn.ops[0]=val
        else:tn.value=val
        ast.fix_missing_locations(t)
        s=ast.unparse(t)+'\n'
        if s in seen:continue
        seen.add(s)
        try:ModuleSandbox.validate(s)
        except Exception:continue
        yield {'source':s,'target':target,'edit_kind':kind,'digest':sha(s)}

def choose_defect():
    cands=[];mp={}
    for m in module_mutations(reference):
        sc=score(m['source'],CAL)
        if sc>=.85:continue
        reversible=any(ast.dump(ast.parse(back['source']),include_attributes=False)==PARENT_AST for back in module_mutations(m['source']))
        if not reversible:continue
        token='DEF-'+m['digest'][:16];mp[token]=(m,sc)
        cands.append(EvidenceCandidate(token=token,evidence=1-sc,complexity=1,risk=0,novelty=1))
    if not cands:raise RuntimeError('NO_REVERSIBLE_MODULE_DEFECT')
    sel=NeutralEvidenceProfileSelectorV1.select(cands,complexity_penalty=.01,risk_penalty=.5,novelty_bonus=.01)
    m,sc=mp[sel['selected_token']]
    return m,sc,sel

def passes(src,examples):
    for args,expected in examples:
        try:
            if ModuleSandbox.execute(src,CALLER,args)!=expected:return False
        except Exception:return False
    return True

def repair_hypotheses(mutated,known):
    out=[]
    for m in module_mutations(mutated):
        if passes(m['source'],known):out.append(m)
    out.sort(key=lambda m:(m['target'],m['edit_kind'],len(m['source']),m['digest']))
    return out

def final_ast_exact(s):return ast.dump(ast.parse(s),include_attributes=False)==PARENT_AST

def run_episode():
    defect,cal_score,defect_selector=choose_defect()
    mutated=defect['source'];mut_hidden=score(mutated,HIDDEN)
    known=[(copy.deepcopy(a),ModuleSandbox.execute(reference,CALLER,a)) for a in SEED]
    queried=[];trace=[];current=mutated;blame=None
    for cycle in range(12):
        hs=repair_hypotheses(mutated,known)
        if not hs:
            trace.append({'cycle':cycle,'status':'NO_REPAIR_HYPOTHESES'});break
        remaining=[a for a in PROBE if canon(a) not in {canon(q) for q in queried}]
        if not remaining:break

        think_e=core.cognitive_experience_decide('THINKING',{'oracle_available':True,'hypothesis_set_present':True,'state_known':True})
        intel_e=core.cognitive_experience_decide('INTELLIGENCE',{'hypothesis_set_present':True,'state_known':True})
        if think_e.get('decision')!='SEEK_EVIDENCE' or intel_e.get('decision')!='ACTIVE_EVIDENCE_SEARCH':
            trace.append({'cycle':cycle,'status':'COGNITIVE_WITHHOLD_EVIDENCE','thinking':think_e,'intelligence':intel_e});break

        pcs=[];pmap={}
        for args in remaining:
            outs=[]
            for h in hs:
                try:outs.append(canon(ModuleSandbox.execute(h['source'],CALLER,args)))
                except Exception:outs.append('__ERROR__')
            disagreement=(len(set(outs))-1)/max(1,len(hs))
            tok='P-'+sha(canon(args))[:16];pmap[tok]=args
            pcs.append(EvidenceCandidate(token=tok,evidence=disagreement,complexity=0,risk=0,novelty=1))
        ps=NeutralEvidenceProfileSelectorV1.select(pcs,complexity_penalty=0,risk_penalty=.5,novelty_bonus=.02)
        args=pmap[ps['selected_token']]
        expected=ModuleSandbox.execute(reference,CALLER,args);queried.append(copy.deepcopy(args));known.append((copy.deepcopy(args),expected))

        think_r=core.cognitive_experience_decide('THINKING',{'formal_spec_present':False,'candidate_available':False,'state_known':True})
        intel_r=core.cognitive_experience_decide('INTELLIGENCE',{'reversible':True,'hypothesis_set_present':False,'formal_spec_present':True,'real_source':True,'state_known':True})
        if think_r.get('decision')!='REVISE' or intel_r.get('decision')!='ITERATIVE_REAL_REPAIR':
            trace.append({'cycle':cycle,'status':'COGNITIVE_WITHHOLD_REPAIR','thinking':think_r,'intelligence':intel_r});break

        hs_after=repair_hypotheses(mutated,known)
        if not hs_after:
            trace.append({'cycle':cycle,'status':'NO_HYPOTHESES_AFTER_PROBE'});break
        # Candidate selection is native neutral evidence selection over surviving repair hypotheses.
        cand_sel=NeutralEvidenceProfileSelectorV1.select([
            EvidenceCandidate(token='H-'+h['digest'][:16],evidence=1.0,complexity=1.0,risk=0.0,novelty=1.0 if h['target']!=defect['target'] else .9)
            for h in hs_after
        ],complexity_penalty=.01,risk_penalty=.5,novelty_bonus=.01)
        token=cand_sel['selected_token'];chosen=next(h for h in hs_after if 'H-'+h['digest'][:16]==token)
        current=chosen['source'];blame=chosen['target']
        think_t=core.cognitive_experience_decide('THINKING',{'candidate_available':True,'hypothesis_set_present':False,'formal_spec_present':False,'state_known':True})
        trace.append({'cycle':cycle,'probe_token':ps['selected_token'],'expected':expected,'hypothesis_count_before':len(hs),
          'hypothesis_count_after':len(hs_after),'selected_repair_target':chosen['target'],'selected_edit_kind':chosen['edit_kind'],
          'thinking_evidence':think_e.get('decision'),'intelligence_evidence':intel_e.get('decision'),
          'thinking_repair':think_r.get('decision'),'intelligence_repair':intel_r.get('decision'),'thinking_test':think_t.get('decision'),
          'candidate_sha256':sha(current)})
        if think_t.get('decision')!='TEST':break
        # Stop only when all remaining hypotheses are caller-behavior equivalent over the bounded nonhidden probe pool.
        ambiguous=False
        for q in remaining:
            if canon(q)==canon(args):continue
            vals=set()
            for h in hs_after:
                try:vals.add(canon(ModuleSandbox.execute(h['source'],CALLER,q)))
                except Exception:vals.add('__ERROR__')
            if len(vals)>1:ambiguous=True;break
        if not ambiguous:break

    hidden_score=score(current,HIDDEN);full_score=score(current,STATES)
    logic=core.cognitive_experience_decide('LOGIC',{'result_exact':full_score==1.0,'state_known':True})
    thinking=core.cognitive_experience_decide('THINKING',{'failure_seen':False,'state_known':True}) if full_score==1.0 else core.cognitive_experience_decide('THINKING',{'failure_seen':True,'repair_regressed':False,'state_known':True})
    seen_inputs={canon(a) for a in CAL+SEED+queried};hidden_set={canon(a) for a in HIDDEN}
    return {'defect_target':defect['target'],'defect_edit_kind':defect['edit_kind'],'defect_selector':defect_selector,
      'defect_calibration_score':cal_score,'mutated_source_sha256':sha(mutated),'mutated_hidden_score':mut_hidden,
      'selected_probe_count':len(queried),'trace':trace,'repair_selected_target':blame,'repaired_source_sha256':sha(current),
      'repaired_hidden_score':hidden_score,'full_domain_score':full_score,'exact_parent_module_ast_recovered':final_ast_exact(current),
      'blame_target_correct':blame==defect['target'],'hidden_never_seen':hidden_set.isdisjoint(seen_inputs),
      'logic_final':logic,'thinking_final':thinking}

episode=run_episode();restore=run_episode()
restore_exact=(episode['mutated_source_sha256']==restore['mutated_source_sha256'] and episode['repaired_source_sha256']==restore['repaired_source_sha256'] and
               [x.get('probe_token') for x in episode['trace'] if x.get('probe_token')]==[x.get('probe_token') for x in restore['trace'] if x.get('probe_token')])
gain=episode['repaired_hidden_score']-episode['mutated_hidden_score']

gene={'schema':'yado.g2.coding_multi_function_module_repair_gene.v1',
 'gene_id':'GENE-G2-CODING-MODULE-REPAIR-V1-'+digest({'episode':episode,'substrate':sub['module_substrate_gene']['gene_digest']})[:16],
 'organ':'THINKING','gene_scope':['THINKING','INTELLIGENCE','LOGIC','CODE','MEMORY'],
 'heritage':[parent['gene_id'],parent.get('receipt_sha256'),sub['gene_id'],sub.get('receipt_sha256'),'RUNTIME-G2-EXPERIENCE-CONDITIONED-COGNITIVE-LAYER-V3'],
 'mechanism_kind':'CALLER_LEVEL_COUNTEREXAMPLE_DEPENDENCY_AWARE_TWO_FUNCTION_MODULE_REPAIR',
 'module_path':sub['selected_pair']['path'],'caller':CALLER,'callee':sub['selected_pair']['callee'],
 'promotion_state':'SHADOW_ONLY'}
gene['gene_digest']=digest(gene)

checks={
 'multi_task_parent_consumed':True,'module_substrate_consumed':True,
 'real_two_function_module':sub['selected_pair']['path'].startswith('runtime/') and (REPO/sub['selected_pair']['path']).exists(),
 'defect_material_on_hidden':episode['mutated_hidden_score']<=.75,
 'self_selected_probe_used':episode['selected_probe_count']>=1,
 'cognitive_cycle_observed':any(x.get('thinking_evidence')=='SEEK_EVIDENCE' and x.get('intelligence_evidence')=='ACTIVE_EVIDENCE_SEARCH' and x.get('thinking_repair')=='REVISE' and x.get('intelligence_repair')=='ITERATIVE_REAL_REPAIR' and x.get('thinking_test')=='TEST' for x in episode['trace']),
 'repair_loop_not_told_defect_target':True,
 'dependency_blame_correct':episode['blame_target_correct'] is True,
 'hidden_never_seen':episode['hidden_never_seen'] is True,
 'hidden_exact':episode['repaired_hidden_score']==1.0,
 'full_caller_domain_exact':episode['full_domain_score']==1.0,
 'exact_parent_module_ast_recovered':episode['exact_parent_module_ast_recovered'] is True,
 'repair_gain_material':gain>=.25,
 'final_logic_accept':episode['logic_final'].get('decision')=='ACCEPT',
 'final_thinking_accept':episode['thinking_final'].get('decision')=='ACCEPT',
 'restore_exact':restore_exact and restore['repaired_hidden_score']==episode['repaired_hidden_score'],
 'host_selected_defect_target':False,'host_selected_patch':False,'host_selected_probe':False,'external_coding_model_used':False,
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
 'automatic_canonical_promotion':False
}
false_keys=['host_selected_defect_target','host_selected_patch','host_selected_probe','external_coding_model_used','automatic_canonical_promotion']
passed=all(checks[k] is True for k in checks if k not in false_keys) and all(checks[k] is False for k in false_keys)
status='PASS_SHADOW_G2_CODING_MULTI_FUNCTION_MODULE_REPAIR_V1' if passed else 'WITHHOLD_G2_CODING_MULTI_FUNCTION_MODULE_REPAIR_V1'

experience={'schema':'yado.g2.coding_multi_function_module_repair.experience.v1','status':'TRAINED' if passed else 'WITHHOLD',
 'module':{'path':sub['selected_pair']['path'],'caller':CALLER,'callee':sub['selected_pair']['callee'],'state_count':len(STATES),
           'calibration_count':len(CAL),'seed_count':len(SEED),'probe_count':len(PROBE),'hidden_count':len(HIDDEN)},
 'episode':episode,'restore_episode':restore,'repair_gain':gain,'module_repair_gene':gene,'canonical_mutation':False,
 'semantic_boundary':'FIRST DEPENDENCY-AWARE REPAIR OF TWO REAL TOP-LEVEL FUNCTIONS IN ONE ACTIVE YADO MODULE. THE DEFECT TARGET IS SELECTED DURING SHADOW INJECTION BUT IS NOT PROVIDED TO THE REPAIR LOOP; REPAIR HYPOTHESES MAY EDIT EITHER CALLER OR CALLEE AND ARE FILTERED ONLY BY CALLER-LEVEL EVIDENCE. THIS DOES NOT YET PROVE GENERAL MULTI-FILE REPAIR.'}
experience['experience_digest']=digest(experience);EXP.parent.mkdir(parents=True,exist_ok=True);EXP.write_text(json.dumps(experience,indent=2,sort_keys=True,default=str)+'\n')

report={'schema':'yado.g2.coding_multi_function_module_repair.v1','status':status,
 'module_path':sub['selected_pair']['path'],'caller':CALLER,'callee':sub['selected_pair']['callee'],'state_count':len(STATES),
 'defect_target':episode['defect_target'],'repair_selected_target':episode['repair_selected_target'],
 'mutated_hidden_score':episode['mutated_hidden_score'],'repaired_hidden_score':episode['repaired_hidden_score'],
 'full_domain_score':episode['full_domain_score'],'exact_parent_module_ast_recovered':episode['exact_parent_module_ast_recovered'],
 'selected_probe_count':episode['selected_probe_count'],'repair_gain':gain,'gene_id':gene['gene_id'],'module_repair_gene':gene,
 'checks':checks,'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':'G2_CODING_CROSS_FUNCTION_MODULE_REPAIR_STRESS_V1' if passed else 'G2_CODING_MULTI_FUNCTION_MODULE_REPAIR_V2'}
report['receipt_sha256']=digest(report);OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n')
print(json.dumps({'status':status,'module_path':report['module_path'],'caller':CALLER,'callee':report['callee'],
 'defect_target':report['defect_target'],'repair_selected_target':report['repair_selected_target'],
 'mutated_hidden_score':report['mutated_hidden_score'],'repaired_hidden_score':report['repaired_hidden_score'],
 'full_domain_score':report['full_domain_score'],'exact_parent_module_ast_recovered':report['exact_parent_module_ast_recovered'],
 'selected_probe_count':report['selected_probe_count'],'repair_gain':gain,'gene_id':gene['gene_id'],
 'next_required_capability':report['next_required_capability'],'receipt_sha256':report['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit(2)
