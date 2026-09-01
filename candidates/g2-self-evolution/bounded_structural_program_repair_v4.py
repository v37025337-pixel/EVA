from __future__ import annotations
import ast,copy
from yado_bounded_compositional_program_repair_v3 import BoundedCompositionalProgramRepairV3

class BoundedStructuralProgramRepairV4:
    COMPONENT_ID="ALG-G2-BOUNDED-STRUCTURAL-PROGRAM-REPAIR-V4"
    BASE=BoundedCompositionalProgramRepairV3
    MAX_EDIT_DEPTH=2
    MAX_CANDIDATES=24000
    MAX_STRUCTURAL_CANDIDATES=12000
    STRUCTURAL_MODES=("arithmetic_wrapper","conditional_expression")

    @classmethod
    def execute(cls,source,function_name,args):
        return cls.BASE.execute(source,function_name,args)

    @classmethod
    def _passes(cls,source,function_name,examples):
        return cls.BASE._passes(source,function_name,examples)

    @staticmethod
    def _copy_expr(expr):
        return copy.deepcopy(expr)

    @classmethod
    def _const_pool(cls,tree,train_examples):
        vals=set(cls.BASE._const_pool(tree,train_examples))
        vals.update({-3,-2,-1,0,1,2,3,4,5})
        return tuple(sorted(vals,key=lambda x:(abs(x),x)))[:14]

    @classmethod
    def _base_transforms(cls,expr,pool,mode_arithmetic=True):
        out=[cls._copy_expr(expr)]
        out.append(ast.Call(func=ast.Name(id="abs",ctx=ast.Load()),args=[cls._copy_expr(expr)],keywords=[]))
        for k in pool:
            if not mode_arithmetic:continue
            out.extend([
              ast.BinOp(left=cls._copy_expr(expr),op=ast.Mult(),right=ast.Constant(k)),
              ast.BinOp(left=cls._copy_expr(expr),op=ast.Add(),right=ast.Constant(k)),
              ast.BinOp(left=cls._copy_expr(expr),op=ast.Sub(),right=ast.Constant(k)),
              ast.Call(func=ast.Name(id="max",ctx=ast.Load()),args=[cls._copy_expr(expr),ast.Constant(k)],keywords=[]),
              ast.Call(func=ast.Name(id="min",ctx=ast.Load()),args=[cls._copy_expr(expr),ast.Constant(k)],keywords=[]),
            ])
        return out

    @classmethod
    def _structural_candidates(cls,source,function_name,train_examples,modes):
        tree=ast.parse(source)
        fname=cls.BASE._validate(tree)
        if fname!=function_name:raise ValueError("FUNCTION_NAME_MISMATCH")
        func=next(n for n in tree.body if isinstance(n,ast.FunctionDef))
        returns=[n for n in ast.walk(func) if isinstance(n,ast.Return) and n.value is not None]
        if len(returns)!=1:return
        ret=returns[0]
        args=[a.arg for a in func.args.args]
        pool=cls._const_pool(tree,train_examples)
        arithmetic="arithmetic_wrapper" in modes
        conditional="conditional_expression" in modes
        expressions=cls._base_transforms(ret.value,pool,arithmetic)
        seen=set();count=0

        def emit(expr):
            nonlocal count
            t=copy.deepcopy(tree)
            tret=next(n for n in ast.walk(t) if isinstance(n,ast.Return) and n.value is not None)
            tret.value=expr
            ast.fix_missing_locations(t)
            try:cls.BASE._validate(t)
            except Exception:return None
            s=ast.unparse(t)+"\n"
            if s in seen:return None
            seen.add(s);count+=1
            if count>cls.MAX_STRUCTURAL_CANDIDATES:return "__BUDGET__"
            return s

        for expr in expressions:
            s=emit(copy.deepcopy(expr))
            if s=="__BUDGET__":return
            if s:yield s

        if conditional:
            branch_pool=expressions[:]
            # Keep conditional search bounded around semantically simple transforms.
            if len(branch_pool)>48:branch_pool=branch_pool[:48]
            tests=[]
            for name in args:
                for k in pool:
                    left=ast.Name(id=name,ctx=ast.Load())
                    for op in (ast.Lt(),ast.LtE(),ast.Gt(),ast.GtE(),ast.Eq()):
                        tests.append(ast.Compare(left=copy.deepcopy(left),ops=[op],comparators=[ast.Constant(k)]))
            for test in tests:
                for body in branch_pool:
                    for other in branch_pool:
                        if ast.dump(body)==ast.dump(other):continue
                        s=emit(ast.IfExp(test=copy.deepcopy(test),body=copy.deepcopy(body),orelse=copy.deepcopy(other)))
                        if s=="__BUDGET__":return
                        if s:yield s

    @classmethod
    def repair(cls,source,function_name,train_examples,max_candidates=None,max_edit_depth=None,
               structural_modes=None,enabled=("binop","compare","boolop","constant","structural")):
        max_candidates=min(int(max_candidates or cls.MAX_CANDIDATES),cls.MAX_CANDIDATES)
        max_depth=min(int(max_edit_depth or cls.MAX_EDIT_DEPTH),cls.MAX_EDIT_DEPTH)
        base=cls.BASE.repair(source,function_name,train_examples,max_candidates=max_candidates,max_edit_depth=max_depth,enabled=enabled)
        if base.get("source"):
            base=dict(base);base["repair_mode"]="BASE_COMPOSITIONAL";return base
        modes=tuple(structural_modes or cls.STRUCTURAL_MODES)
        tried=int(base.get("tried") or 0)
        for cand in cls._structural_candidates(source,function_name,train_examples,modes):
            tried+=1
            if tried>max_candidates:
                return {"source":None,"tried":tried-1,"reason":"SEARCH_BUDGET","repair_mode":"STRUCTURAL"}
            if cls._passes(cand,function_name,train_examples):
                return {"source":cand,"tried":tried,"edit_depth":None,"repair_mode":"STRUCTURAL_EXPRESSION"}
        return {"source":None,"tried":tried,"reason":"NO_REPAIR_WITHIN_STRUCTURAL_BUDGET","repair_mode":"STRUCTURAL"}

__all__=["BoundedStructuralProgramRepairV4"]
