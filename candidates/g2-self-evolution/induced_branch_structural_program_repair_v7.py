from __future__ import annotations
import ast,copy
from fractions import Fraction
from yado_bounded_compositional_program_repair_v3 import BoundedCompositionalProgramRepairV3

class InducedBranchStructuralProgramRepairV7:
    COMPONENT_ID="ALG-G2-INDUCED-BRANCH-STRUCTURAL-PROGRAM-REPAIR-V7"
    BASE=BoundedCompositionalProgramRepairV3
    MAX_EDIT_DEPTH=2
    MAX_CANDIDATES=24000
    BASE_SEARCH_BUDGET=6000
    STRUCTURAL_SEARCH_BUDGET=18000
    MAX_SPLIT_TESTS=640
    MAX_BRANCH_MODELS=8

    @classmethod
    def execute(cls,source,function_name,args):
        return cls.BASE.execute(source,function_name,args)

    @classmethod
    def _passes(cls,source,function_name,examples):
        return cls.BASE._passes(source,function_name,examples)

    @staticmethod
    def _emit(tree,expr):
        t=copy.deepcopy(tree)
        ret=next(n for n in ast.walk(t) if isinstance(n,ast.Return) and n.value is not None)
        ret.value=copy.deepcopy(expr);ast.fix_missing_locations(t)
        BoundedCompositionalProgramRepairV3._validate(t)
        return ast.unparse(t)+"\n"

    @classmethod
    def _base_values(cls,tree,function_name,base,examples):
        src=cls._emit(tree,base)
        vals=[]
        for args,expected in examples:
            try:vals.append((cls.execute(src,function_name,args),expected))
            except Exception:return None
        return vals

    @staticmethod
    def _mul(base,k):
        return ast.BinOp(left=copy.deepcopy(base),op=ast.Mult(),right=ast.Constant(k))

    @staticmethod
    def _add(expr,b):
        return ast.BinOp(left=copy.deepcopy(expr),op=ast.Add(),right=ast.Constant(b))

    @classmethod
    def _induce_exprs(cls,tree,function_name,base,examples):
        vals=cls._base_values(tree,function_name,base,examples)
        if vals is None or not vals:return []
        out=[copy.deepcopy(base),ast.Call(func=ast.Name(id="abs",ctx=ast.Load()),args=[copy.deepcopy(base)],keywords=[])]
        ys=[e for _,e in vals]
        if all(y==ys[0] for y in ys):out.append(ast.Constant(ys[0]))

        diffs=[]
        diff_ok=True
        for x,y in vals:
            try:diffs.append(Fraction(y)-Fraction(x))
            except Exception:diff_ok=False;break
        if diff_ok and diffs and all(d==diffs[0] for d in diffs) and diffs[0].denominator==1:
            out.append(cls._add(base,int(diffs[0])))

        ratio=None;ratio_ok=True
        for x,y in vals:
            try:
                fx,fy=Fraction(x),Fraction(y)
            except Exception:ratio_ok=False;break
            if fx==0:
                if fy!=0:ratio_ok=False;break
                continue
            r=fy/fx
            if ratio is None:ratio=r
            elif r!=ratio:ratio_ok=False;break
        if ratio_ok and ratio is not None and ratio.denominator==1:
            out.append(cls._mul(base,int(ratio)))

        distinct={}
        for x,y in vals:
            try:distinct.setdefault(Fraction(x),Fraction(y))
            except Exception:pass
        if len(distinct)>=2:
            items=list(distinct.items())
            x1,y1=items[0]
            for x2,y2 in items[1:]:
                if x2==x1:continue
                a=(y2-y1)/(x2-x1);b=y1-a*x1
                if a.denominator==1 and b.denominator==1 and all(Fraction(y)==a*Fraction(x)+b for x,y in vals):
                    expr=cls._mul(base,int(a))
                    if int(b)!=0:expr=cls._add(expr,int(b))
                    out.append(expr)
                break

        candidates=set(ys+[x for x,_ in vals])
        for c in sorted(candidates,key=lambda z:(abs(z) if isinstance(z,(int,float)) else 999999,str(z)))[:16]:
            if not isinstance(c,int) or isinstance(c,bool):continue
            try:
                if all(y==min(x,c) for x,y in vals):
                    out.append(ast.Call(func=ast.Name(id="min",ctx=ast.Load()),args=[copy.deepcopy(base),ast.Constant(c)],keywords=[]))
                if all(y==max(x,c) for x,y in vals):
                    out.append(ast.Call(func=ast.Name(id="max",ctx=ast.Load()),args=[copy.deepcopy(base),ast.Constant(c)],keywords=[]))
            except Exception:pass

        uniq=[];seen=set()
        for e in out:
            try:
                s=cls._emit(tree,e)
                if all(cls.execute(s,function_name,args)==expected for args,expected in examples):
                    d=ast.dump(e)
                    if d not in seen:seen.add(d);uniq.append(e)
            except Exception:continue
        return uniq[:cls.MAX_BRANCH_MODELS]

    @classmethod
    def _test_value(cls,tree,function_name,test,args):
        return bool(cls.execute(cls._emit(tree,test),function_name,args))

    @classmethod
    def _split_constants(cls,func,examples):
        vals={-3,-2,-1,0,1,2,3}
        argc=len(func.args.args)
        for args,_ in examples:
            for v in tuple(args)[:argc]:
                if isinstance(v,int) and not isinstance(v,bool) and abs(v)<=100:
                    vals.update({v,v-1,v+1})
        return tuple(sorted(vals,key=lambda z:(abs(z),z)))[:24]

    @classmethod
    def _structural_candidates(cls,source,function_name,examples):
        tree=ast.parse(source);fname=cls.BASE._validate(tree)
        if fname!=function_name:raise ValueError("FUNCTION_NAME_MISMATCH")
        func=next(n for n in tree.body if isinstance(n,ast.FunctionDef))
        returns=[n for n in ast.walk(func) if isinstance(n,ast.Return) and n.value is not None]
        if len(returns)!=1:return
        base=returns[0].value
        emitted=0;seen=set()

        for expr in cls._induce_exprs(tree,function_name,base,examples):
            s=cls._emit(tree,expr)
            if s not in seen:
                seen.add(s);emitted+=1;yield s

        tests=[]
        for name in [a.arg for a in func.args.args]:
            for k in cls._split_constants(func,examples):
                for op in (ast.Lt(),ast.LtE(),ast.Gt(),ast.GtE(),ast.Eq()):
                    tests.append(ast.Compare(left=ast.Name(id=name,ctx=ast.Load()),ops=[op],comparators=[ast.Constant(k)]))
                    if len(tests)>=cls.MAX_SPLIT_TESTS:break
                if len(tests)>=cls.MAX_SPLIT_TESTS:break
            if len(tests)>=cls.MAX_SPLIT_TESTS:break

        for test in tests:
            try:
                yes=[z for z in examples if cls._test_value(tree,function_name,test,z[0])]
                no=[z for z in examples if not cls._test_value(tree,function_name,test,z[0])]
            except Exception:continue
            if not yes or not no:continue
            yes_models=cls._induce_exprs(tree,function_name,base,yes)
            if not yes_models:continue
            no_models=cls._induce_exprs(tree,function_name,base,no)
            if not no_models:continue
            for body in yes_models:
                for other in no_models:
                    cond=ast.IfExp(test=copy.deepcopy(test),body=copy.deepcopy(body),orelse=copy.deepcopy(other))
                    s=cls._emit(tree,cond)
                    if s in seen:continue
                    seen.add(s);emitted+=1
                    if emitted>cls.STRUCTURAL_SEARCH_BUDGET:return
                    yield s

    @classmethod
    def repair(cls,source,function_name,train_examples,max_candidates=None,max_edit_depth=None,enabled=("binop","compare","boolop","constant","structural")):
        total=min(int(max_candidates or cls.MAX_CANDIDATES),cls.MAX_CANDIDATES)
        depth=min(int(max_edit_depth or cls.MAX_EDIT_DEPTH),cls.MAX_EDIT_DEPTH)
        base_budget=min(cls.BASE_SEARCH_BUDGET,total)
        base=cls.BASE.repair(source,function_name,train_examples,max_candidates=base_budget,max_edit_depth=depth,enabled=enabled)
        if base.get("source"):
            out=dict(base);out["repair_mode"]="BASE_PORTFOLIO";return out
        remaining=max(0,total-base_budget);tried=0
        for cand in cls._structural_candidates(source,function_name,train_examples):
            tried+=1
            if tried>remaining:return {"source":None,"tried":tried-1,"reason":"STRUCTURAL_SEARCH_BUDGET","repair_mode":"INDUCED_BRANCH"}
            if cls._passes(cand,function_name,train_examples):
                return {"source":cand,"tried":tried,"repair_mode":"INDUCED_BRANCH","edit_depth":None}
        return {"source":None,"tried":tried,"reason":"NO_REPAIR_WITHIN_INDUCED_BRANCH_BUDGET","repair_mode":"INDUCED_BRANCH"}

__all__=["InducedBranchStructuralProgramRepairV7"]
