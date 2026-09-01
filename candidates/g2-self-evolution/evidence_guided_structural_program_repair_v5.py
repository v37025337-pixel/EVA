from __future__ import annotations
import ast,copy
from yado_bounded_compositional_program_repair_v3 import BoundedCompositionalProgramRepairV3

class EvidenceGuidedStructuralProgramRepairV5:
    COMPONENT_ID="ALG-G2-EVIDENCE-GUIDED-STRUCTURAL-PROGRAM-REPAIR-V5"
    BASE=BoundedCompositionalProgramRepairV3
    MAX_EDIT_DEPTH=2
    MAX_CANDIDATES=24000
    MAX_STRUCTURAL_CANDIDATES=12000
    MAX_BRANCH_EXPRESSIONS=64

    @classmethod
    def execute(cls,source,function_name,args):
        return cls.BASE.execute(source,function_name,args)

    @classmethod
    def _passes(cls,source,function_name,examples):
        return cls.BASE._passes(source,function_name,examples)

    @classmethod
    def _const_pool(cls,tree,examples):
        vals=set(cls.BASE._const_pool(tree,examples));vals.update({-4,-3,-2,-1,0,1,2,3,4,5})
        return tuple(sorted(vals,key=lambda x:(abs(x),x)))[:16]

    @staticmethod
    def _emit(tree,expr):
        t=copy.deepcopy(tree)
        ret=next(n for n in ast.walk(t) if isinstance(n,ast.Return) and n.value is not None)
        ret.value=copy.deepcopy(expr);ast.fix_missing_locations(t)
        BoundedCompositionalProgramRepairV3._validate(t)
        return ast.unparse(t)+"\n"

    @classmethod
    def _expressions(cls,base,pool):
        out=[copy.deepcopy(base),ast.Call(func=ast.Name(id="abs",ctx=ast.Load()),args=[copy.deepcopy(base)],keywords=[])]
        for k in pool:
            out.extend([
              ast.BinOp(left=copy.deepcopy(base),op=ast.Mult(),right=ast.Constant(k)),
              ast.BinOp(left=copy.deepcopy(base),op=ast.Add(),right=ast.Constant(k)),
              ast.BinOp(left=copy.deepcopy(base),op=ast.Sub(),right=ast.Constant(k)),
              ast.Call(func=ast.Name(id="max",ctx=ast.Load()),args=[copy.deepcopy(base),ast.Constant(k)],keywords=[]),
              ast.Call(func=ast.Name(id="min",ctx=ast.Load()),args=[copy.deepcopy(base),ast.Constant(k)],keywords=[]),
            ])
        uniq=[];seen=set()
        for e in out:
            d=ast.dump(e)
            if d not in seen:seen.add(d);uniq.append(e)
        return uniq[:cls.MAX_BRANCH_EXPRESSIONS]

    @classmethod
    def _test_value(cls,tree,function_name,test,args):
        src=cls._emit(tree,test)
        return bool(cls.execute(src,function_name,args))

    @classmethod
    def _expr_fits_subset(cls,tree,function_name,expr,examples):
        src=cls._emit(tree,expr)
        for args,expected in examples:
            try:
                if cls.execute(src,function_name,args)!=expected:return False
            except Exception:return False
        return True

    @classmethod
    def _guided_structural_candidates(cls,source,function_name,examples):
        tree=ast.parse(source);fname=cls.BASE._validate(tree)
        if fname!=function_name:raise ValueError("FUNCTION_NAME_MISMATCH")
        func=next(n for n in tree.body if isinstance(n,ast.FunctionDef))
        returns=[n for n in ast.walk(func) if isinstance(n,ast.Return) and n.value is not None]
        if len(returns)!=1:return
        base=returns[0].value;args=[a.arg for a in func.args.args];pool=cls._const_pool(tree,examples)
        exprs=cls._expressions(base,pool)
        emitted=0;seen=set()

        # Whole-dataset structural arithmetic first.
        for expr in exprs:
            s=cls._emit(tree,expr)
            if s in seen:continue
            seen.add(s);emitted+=1
            if emitted>cls.MAX_STRUCTURAL_CANDIDATES:return
            yield s

        # Evidence-guided conditional decomposition.
        tests=[]
        for name in args:
            for k in pool:
                for op in (ast.Lt(),ast.LtE(),ast.Gt(),ast.GtE(),ast.Eq()):
                    tests.append(ast.Compare(left=ast.Name(id=name,ctx=ast.Load()),ops=[op],comparators=[ast.Constant(k)]))
        for test in tests:
            try:
                yes=[z for z in examples if cls._test_value(tree,function_name,test,z[0])]
                no=[z for z in examples if not cls._test_value(tree,function_name,test,z[0])]
            except Exception:
                continue
            if not yes or not no:continue
            yes_fit=[e for e in exprs if cls._expr_fits_subset(tree,function_name,e,yes)]
            if not yes_fit:continue
            no_fit=[e for e in exprs if cls._expr_fits_subset(tree,function_name,e,no)]
            if not no_fit:continue
            # Prefer simplest exact branch models; no Cartesian brute force.
            for body in yes_fit[:3]:
                for other in no_fit[:3]:
                    cond=ast.IfExp(test=copy.deepcopy(test),body=copy.deepcopy(body),orelse=copy.deepcopy(other))
                    s=cls._emit(tree,cond)
                    if s in seen:continue
                    seen.add(s);emitted+=1
                    if emitted>cls.MAX_STRUCTURAL_CANDIDATES:return
                    yield s

    @classmethod
    def repair(cls,source,function_name,train_examples,max_candidates=None,max_edit_depth=None,enabled=("binop","compare","boolop","constant","structural")):
        max_candidates=min(int(max_candidates or cls.MAX_CANDIDATES),cls.MAX_CANDIDATES)
        max_depth=min(int(max_edit_depth or cls.MAX_EDIT_DEPTH),cls.MAX_EDIT_DEPTH)
        base=cls.BASE.repair(source,function_name,train_examples,max_candidates=max_candidates,max_edit_depth=max_depth,enabled=enabled)
        if base.get("source"):
            out=dict(base);out["repair_mode"]="BASE_COMPOSITIONAL";return out
        tried=int(base.get("tried") or 0)
        for cand in cls._guided_structural_candidates(source,function_name,train_examples):
            tried+=1
            if tried>max_candidates:return {"source":None,"tried":tried-1,"reason":"SEARCH_BUDGET","repair_mode":"GUIDED_STRUCTURAL"}
            if cls._passes(cand,function_name,train_examples):
                return {"source":cand,"tried":tried,"edit_depth":None,"repair_mode":"EVIDENCE_GUIDED_STRUCTURAL"}
        return {"source":None,"tried":tried,"reason":"NO_REPAIR_WITHIN_GUIDED_STRUCTURAL_BUDGET","repair_mode":"GUIDED_STRUCTURAL"}

__all__=["EvidenceGuidedStructuralProgramRepairV5"]
