from __future__ import annotations
import ast,copy
from fractions import Fraction
from yado_bounded_compositional_program_repair_v3 import BoundedCompositionalProgramRepairV3

class RecursivePartitionStructuralProgramRepairV8:
    COMPONENT_ID="ALG-G2-RECURSIVE-PARTITION-STRUCTURAL-PROGRAM-REPAIR-V8"
    BASE=BoundedCompositionalProgramRepairV3
    MAX_EDIT_DEPTH=2
    MAX_CANDIDATES=24000
    BASE_SEARCH_BUDGET=6000
    STRUCTURAL_SEARCH_BUDGET=18000
    MAX_CONDITIONAL_DEPTH=2
    MAX_SPLIT_TESTS=640
    MAX_BRANCH_MODELS=8
    MAX_SEARCH_NODES=4000

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
        src=cls._emit(tree,base);out=[]
        for args,expected in examples:
            try:out.append((cls.execute(src,function_name,args),expected))
            except Exception:return None
        return out

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
        try:
            diffs=[Fraction(y)-Fraction(x) for x,y in vals]
            if diffs and all(d==diffs[0] for d in diffs) and diffs[0].denominator==1:
                out.append(cls._add(base,int(diffs[0])))
        except Exception:pass
        try:
            ratio=None;ok=True
            for x,y in vals:
                fx,fy=Fraction(x),Fraction(y)
                if fx==0:
                    if fy!=0:ok=False;break
                    continue
                r=fy/fx
                if ratio is None:ratio=r
                elif r!=ratio:ok=False;break
            if ok and ratio is not None and ratio.denominator==1:
                out.append(cls._mul(base,int(ratio)))
        except Exception:pass
        try:
            distinct={}
            for x,y in vals:distinct.setdefault(Fraction(x),Fraction(y))
            if len(distinct)>=2:
                items=list(distinct.items());x1,y1=items[0]
                for x2,y2 in items[1:]:
                    if x2==x1:continue
                    a=(y2-y1)/(x2-x1);b=y1-a*x1
                    if a.denominator==1 and b.denominator==1 and all(Fraction(y)==a*Fraction(x)+b for x,y in vals):
                        e=cls._mul(base,int(a))
                        if int(b)!=0:e=cls._add(e,int(b))
                        out.append(e)
                    break
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
    def _tests(cls,func,examples):
        vals={-3,-2,-1,0,1,2,3}
        for args,_ in examples:
            for v in args[:len(func.args.args)]:
                if isinstance(v,int) and not isinstance(v,bool) and abs(v)<=100:
                    vals.update({v,v-1,v+1})
        constants=tuple(sorted(vals,key=lambda z:(abs(z),z)))[:24]
        out=[]
        for name in [a.arg for a in func.args.args]:
            for k in constants:
                for op in (ast.Lt(),ast.LtE(),ast.Gt(),ast.GtE(),ast.Eq()):
                    out.append(ast.Compare(left=ast.Name(id=name,ctx=ast.Load()),ops=[op],comparators=[ast.Constant(k)]))
                    if len(out)>=cls.MAX_SPLIT_TESTS:return out
        return out

    @classmethod
    def _solve_subset(cls,tree,function_name,func,base,examples,depth,counter):
        counter[0]+=1
        if counter[0]>cls.MAX_SEARCH_NODES:return None
        direct=cls._induce_exprs(tree,function_name,base,examples)
        if direct:return direct[0]
        if depth<=0:return None
        for test in cls._tests(func,examples):
            try:
                yes=[z for z in examples if cls._test_value(tree,function_name,test,z[0])]
                no=[z for z in examples if not cls._test_value(tree,function_name,test,z[0])]
            except Exception:continue
            if not yes or not no or len(yes)==len(examples) or len(no)==len(examples):continue
            left=cls._solve_subset(tree,function_name,func,base,yes,depth-1,counter)
            if left is None:continue
            right=cls._solve_subset(tree,function_name,func,base,no,depth-1,counter)
            if right is None:continue
            return ast.IfExp(test=copy.deepcopy(test),body=left,orelse=right)
        return None

    @classmethod
    def _structural_candidate(cls,source,function_name,examples):
        tree=ast.parse(source);fname=cls.BASE._validate(tree)
        if fname!=function_name:raise ValueError("FUNCTION_NAME_MISMATCH")
        func=next(n for n in tree.body if isinstance(n,ast.FunctionDef))
        returns=[n for n in ast.walk(func) if isinstance(n,ast.Return) and n.value is not None]
        if len(returns)!=1:return None,0
        counter=[0]
        expr=cls._solve_subset(tree,function_name,func,returns[0].value,examples,cls.MAX_CONDITIONAL_DEPTH,counter)
        if expr is None:return None,counter[0]
        return cls._emit(tree,expr),counter[0]

    @classmethod
    def repair(cls,source,function_name,train_examples,max_candidates=None,max_edit_depth=None,enabled=("binop","compare","boolop","constant","structural")):
        total=min(int(max_candidates or cls.MAX_CANDIDATES),cls.MAX_CANDIDATES)
        depth=min(int(max_edit_depth or cls.MAX_EDIT_DEPTH),cls.MAX_EDIT_DEPTH)
        base_budget=min(cls.BASE_SEARCH_BUDGET,total)
        base=cls.BASE.repair(source,function_name,train_examples,max_candidates=base_budget,max_edit_depth=depth,enabled=enabled)
        if base.get("source"):
            out=dict(base);out["repair_mode"]="BASE_PORTFOLIO";return out
        cand,nodes=cls._structural_candidate(source,function_name,train_examples)
        if nodes>cls.STRUCTURAL_SEARCH_BUDGET:
            return {"source":None,"reason":"STRUCTURAL_SEARCH_BUDGET","search_nodes":nodes,"repair_mode":"RECURSIVE_PARTITION"}
        if cand and cls._passes(cand,function_name,train_examples):
            return {"source":cand,"search_nodes":nodes,"repair_mode":"RECURSIVE_PARTITION","conditional_depth":cls.MAX_CONDITIONAL_DEPTH}
        return {"source":None,"reason":"NO_REPAIR_WITHIN_RECURSIVE_PARTITION_BUDGET","search_nodes":nodes,"repair_mode":"RECURSIVE_PARTITION"}

__all__=["RecursivePartitionStructuralProgramRepairV8"]
