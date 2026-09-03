"""RC7 native bounded Boolean expression runtime.

Fresh implementation of the public V2.6 Boolean-search contract. It is validated
against the preserved compatibility runtime but is not claimed to be the lost
historical original.
"""
from __future__ import annotations
from typing import Any, Iterable, List, Mapping, Sequence, Tuple

PROVENANCE={
    'status':'RC7_NATIVE_REDERIVATION_V1',
    'source':'PUBLIC_BOOLEAN_SEARCH_CONTRACT_PLUS_EXHAUSTIVE_DIFFERENTIAL_VALIDATION',
    'scope':'V2_6_BOOLEAN_RULE_SEARCH_RUNTIME',
    'lost_original_recovered':False,
}
Expr=Tuple[Any,...]
VARS=('p','q','r')
BINARY=('AND','OR','XOR')

def eval_expr(expr:Expr,env:Mapping[str,bool])->bool:
    op=expr[0]
    if op=='VAR': return bool(env.get(str(expr[1]),False))
    if op=='NOT': return not eval_expr(expr[1],env)
    a=eval_expr(expr[1],env);b=eval_expr(expr[2],env)
    if op=='AND': return a and b
    if op=='OR': return a or b
    if op=='XOR': return bool(a)^bool(b)
    raise ValueError(op)

def _complexity(expr:Expr)->int:
    op=expr[0]
    if op=='VAR': return 1
    if op=='NOT': return 1+_complexity(expr[1])
    return 1+_complexity(expr[1])+_complexity(expr[2])

def generate_exprs(depth:int)->List[Expr]:
    if depth<0 or depth>2: raise ValueError('depth must be in [0,2]')
    current=[('VAR',v) for v in VARS]
    if depth==0:return current
    for _ in range(depth):
        ordered=[];seen=set()
        def admit(e):
            if e not in seen:seen.add(e);ordered.append(e)
        for e in current:admit(e)
        for e in current:admit(('NOT',e))
        for op in BINARY:
            for a in current:
                for b in current:admit((op,a,b))
        current=ordered
    return current

def score_expr(expr:Expr,cases:Sequence[Tuple[Mapping[str,bool],bool]])->float:
    if not cases:return 0.0
    return sum(eval_expr(expr,env)==expected for env,expected in cases)/len(cases)

def fit_expr(pool:Iterable[Expr],cases:Sequence[Tuple[Mapping[str,bool],bool]])->Tuple[Expr,float]:
    chosen=None;chosen_key=None;chosen_score=-1.0
    for expr in pool:
        sc=score_expr(expr,cases)
        key=(sc,-_complexity(expr),repr(expr))
        if chosen is None or key>chosen_key:
            chosen=expr;chosen_key=key;chosen_score=sc
    if chosen is None:raise ValueError('empty expression pool')
    return chosen,chosen_score

__all__=['PROVENANCE','eval_expr','fit_expr','generate_exprs','score_expr']
