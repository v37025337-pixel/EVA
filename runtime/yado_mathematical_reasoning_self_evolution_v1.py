from __future__ import annotations
from pathlib import Path
import hashlib,json,os,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path.insert(0,str(ROOT))
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash

HEAD=REPO/'canonical'/'yado-main-head-g2.json'
LEDGER=REPO/'architecture'/'evolution-ledger.json'
DIAG=REPO/'receipts'/'yado-real-world-generalization-self-directed-v1-run-33405588896.json'
CAND_DIR=REPO/'candidates'/'g2-self-evolution';CAND_DIR.mkdir(parents=True,exist_ok=True)
CAND_SRC=CAND_DIR/'semantic_expression_synthesizer_v1.py'
CAND_META=CAND_DIR/'semantic_expression_synthesizer_v1.json'
OUT=ROOT/'yado_mathematical_reasoning_self_evolution_v1_receipt.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))

head=load(HEAD);ledger=load(LEDGER);diag=load(DIAG)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['REAL_MATHEMATICAL_REASONING_TRANSFER_REPAIR_V1']:raise RuntimeError('UNEXPECTED_FRONTIER')
if diag.get('domain_pass',{}).get('REAL_MATHEMATICAL_REASONING_TRANSFER') is not False:raise RuntimeError('MATH_NOT_FAILED')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')

candidate_source=r'''from __future__ import annotations

class SemanticExpressionSynthesizerV1:
    COMPONENT_ID="ALG-G2-SEMANTIC-EXPRESSION-SYNTHESIZER-V1"
    OPS=("+","-","*")
    BASE=("x","y",-3,-2,-1,0,1,2,3)

    @staticmethod
    def _eval(expr,x,y):
        if expr=="x": return x
        if expr=="y": return y
        if isinstance(expr,(int,float)): return expr
        op,a,b=expr
        av=SemanticExpressionSynthesizerV1._eval(a,x,y)
        bv=SemanticExpressionSynthesizerV1._eval(b,x,y)
        if op=="+": return av+bv
        if op=="-": return av-bv
        if op=="*": return av*bv
        raise ValueError("UNKNOWN_OP")

    @staticmethod
    def render(expr):
        if expr=="x" or expr=="y": return expr
        if isinstance(expr,(int,float)): return str(expr)
        op,a,b=expr
        return f"({SemanticExpressionSynthesizerV1.render(a)}{op}{SemanticExpressionSynthesizerV1.render(b)})"

    @classmethod
    def synthesize(cls,train_rows,max_ops=3,max_states_per_level=30000):
        pts=[(r["x"],r["y"]) for r in train_rows]
        target=tuple(r["expected"] for r in train_rows)
        levels=[]
        l0={}
        for e in cls.BASE:
            sig=tuple(cls._eval(e,x,y) for x,y in pts)
            s=cls.render(e)
            if sig not in l0 or (len(s),s)<(len(cls.render(l0[sig])),cls.render(l0[sig])):
                l0[sig]=e
        levels.append(l0)
        if target in l0:return {"expression":l0[target],"ops":0,"states":[len(l0)]}

        for opcount in range(1,max_ops+1):
            cur={}
            for left_ops in range(opcount):
                right_ops=opcount-1-left_ops
                left=levels[left_ops];right=levels[right_ops]
                for ls,le in left.items():
                    for rs,re in right.items():
                        for op in cls.OPS:
                            if op=="+":
                                sig=tuple(a+b for a,b in zip(ls,rs))
                            elif op=="-":
                                sig=tuple(a-b for a,b in zip(ls,rs))
                            else:
                                sig=tuple(a*b for a,b in zip(ls,rs))
                            expr=(op,le,re);rend=cls.render(expr)
                            old=cur.get(sig)
                            if old is None or (len(rend),rend)<(len(cls.render(old)),cls.render(old)):
                                cur[sig]=expr
                if len(cur)>max_states_per_level*2:
                    keep=sorted(cur.items(),key=lambda kv:(len(cls.render(kv[1])),cls.render(kv[1])))[:max_states_per_level]
                    cur=dict(keep)
            if len(cur)>max_states_per_level:
                keep=sorted(cur.items(),key=lambda kv:(len(cls.render(kv[1])),cls.render(kv[1])))[:max_states_per_level]
                cur=dict(keep)
            levels.append(cur)
            if target in cur:
                return {"expression":cur[target],"ops":opcount,"states":[len(x) for x in levels]}
        return {"expression":None,"ops":None,"states":[len(x) for x in levels]}

    @classmethod
    def predict(cls,result,x,y):
        if result.get("expression") is None: raise ValueError("NO_EXPRESSION")
        return cls._eval(result["expression"],x,y)
'''

CAND_SRC.write_text(candidate_source,encoding='utf-8')
sys.path.insert(0,str(CAND_DIR))
from semantic_expression_synthesizer_v1 import SemanticExpressionSynthesizerV1 as Syn

train_pts=[(-3,-2),(-1,4),(0,0),(2,3),(5,-1),(4,2)]
blind_pts=[(-5,7),(-2,-9),(1,8),(3,6),(7,2),(9,-4),(11,5)]
tasks=[
 ('M1_AFFINE',lambda x,y:2*x+3),
 ('M2_BILINEAR',lambda x,y:x*y+x),
 ('M3_SQUARES',lambda x,y:x*x+y*y),
 ('M4_DIFF_SQUARES',lambda x,y:(x-y)*(x+y)),
]
fresh=[
 ('MF1_SHIFT_SQUARE',lambda x,y:(x+1)*(x+1)),
 ('MF2_FACTORED',lambda x,y:y*(x-y)),
 ('MF3_DISTANCE_SQUARE',lambda x,y:(x-y)*(x-y)),
 ('MF4_LINEAR',lambda x,y:3*x-y),
]
def run_task(tid,fn):
    tr=[{'x':x,'y':y,'expected':fn(x,y)} for x,y in train_pts]
    res=Syn.synthesize(tr,max_ops=3,max_states_per_level=30000)
    hidden=[]
    if res['expression'] is not None:
        for x,y in blind_pts:
            got=Syn.predict(res,x,y);exp=fn(x,y)
            hidden.append({'x':x,'y':y,'expected':exp,'got':got,'ok':got==exp})
    return {'id':tid,'expression':Syn.render(res['expression']) if res['expression'] is not None else None,
            'ops':res['ops'],'states':res['states'],'blind_pass':bool(hidden) and all(z['ok'] for z in hidden),'blind':hidden}

old_score=float(diag['mathematics']['score'])
rows=[run_task(*t) for t in tasks]
fresh_rows=[run_task(*t) for t in fresh]
score=sum(x['blind_pass'] for x in rows)/len(rows)
fresh_score=sum(x['blind_pass'] for x in fresh_rows)/len(fresh_rows)

# Causal ablation: max_ops=1 cannot express the failed higher-composition counterexamples.
ablation=[]
for tid,fn in tasks[2:]:
    tr=[{'x':x,'y':y,'expected':fn(x,y)} for x,y in train_pts]
    res=Syn.synthesize(tr,max_ops=1,max_states_per_level=30000)
    ablation.append({'id':tid,'found':res['expression'] is not None})
ablation_fail=all(not x['found'] for x in ablation)

checks={
 'repairs_original_math_counterexamples':score==1.0,
 'fresh_math_transfer':fresh_score>=.75,
 'gain_over_old_math':score-old_score>=.40,
 'causal_depth_ablation':ablation_fail,
 'bounded_state_counts':all(max(x['states'])<=30000 for x in rows+fresh_rows),
 'candidate_source_present':fsha(CAND_SRC)==hashlib.sha256(candidate_source.encode()).hexdigest(),
 'canonical_head_immutable':ledger.get('current_head_digest')==head.get('canonical_head_digest'),
}
passed=all(checks.values())
next_cap='REAL_MATHEMATICAL_REASONING_TRANSFER_FRESH_ADMISSION_V1' if passed else 'REAL_MATHEMATICAL_REASONING_SEARCH_EVOLUTION_V2'

meta={'schema':'yado.g2.semantic_expression_synthesizer_candidate.v1',
 'component_id':Syn.COMPONENT_ID,'generation':ledger['current_head'],'parent_head_digest':head['canonical_head_digest'],
 'source_counterexamples':['M3_SQUARES','M4_DIFF_SQUARES'],'old_score':old_score,'repaired_score':score,'fresh_score':fresh_score,
 'candidate_source_sha256':fsha(CAND_SRC),'checks':checks,
 'state':'AUTHORIZED_FOR_SHADOW_ADMISSION' if passed else 'WITHHOLD','canonical_active':False,'promotion_applied':False,
 'semantic_boundary':'BOUNDED SYMBOLIC EXPRESSION SYNTHESIS BY TRAIN-SEMANTIC SIGNATURES; NOT GENERAL THEOREM PROVING OR MATHEMATICAL UNDERSTANDING.'}
meta['candidate_digest']=h(meta);CAND_META.write_text(json.dumps(meta,indent=2,sort_keys=True)+'\n')

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={'schema':'yado.g2.mathematical_reasoning_self_evolution.v1',
 'status':'PASS_MATHEMATICAL_REASONING_SELF_EVOLUTION_V1' if passed else 'WITHHOLD_MATHEMATICAL_REASONING_SELF_EVOLUTION_V1',
 'source_diagnostic_receipt':diag['receipt_sha256'],'old_score':old_score,'repaired_tasks':rows,'fresh_tasks':fresh_rows,
 'repaired_score':score,'fresh_score':fresh_score,'ablation':ablation,'checks':checks,
 'candidate_digest':meta['candidate_digest'],'candidate_source_sha256':meta['candidate_source_sha256'],
 'canonical_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,'next_required_capability':next_cap,
 'semantic_boundary':meta['semantic_boundary']}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_MATHEMATICAL_REASONING_SELF_EVOLUTION",
 'event_type':'KERNEL_NATIVE_CODE_EVOLUTION_FROM_REAL_COUNTEREXAMPLE','status':'PASS_SHADOW' if passed else 'WITHHOLD',
 'generation':ledger['current_head'],'deficit':'REAL_MATHEMATICAL_REASONING_TRANSFER_REPAIR_V1',
 'effect':f"SEMANTIC_EXPRESSION_SYNTHESIS; OLD={old_score}; REPAIRED={score}; FRESH={fresh_score}",
 'source_path':f'receipts/yado-mathematical-reasoning-self-evolution-v1-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':False,'promotion_applied':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['open_deficits']=[next_cap];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':receipt['status'],'old_score':old_score,'repaired_score':score,'fresh_score':fresh_score,'checks':checks,'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('MATH_SELF_EVOLUTION_WITHHELD')
