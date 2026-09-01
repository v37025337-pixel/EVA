from __future__ import annotations
import ast,copy

class BoundedCompositionalProgramRepairV3:
    COMPONENT_ID="ALG-G2-BOUNDED-COMPOSITIONAL-PROGRAM-REPAIR-V3"
    SAFE_CALLS={"min":min,"max":max,"all":all,"any":any,"sum":sum,"abs":abs,"len":len}
    BIN_OPS=(ast.Add,ast.Sub,ast.Mult,ast.Mod)
    CMP_OPS=(ast.Eq,ast.NotEq,ast.Lt,ast.LtE,ast.Gt,ast.GtE)
    BOOL_OPS=(ast.And,ast.Or)
    MAX_EDIT_DEPTH=2
    MAX_CANDIDATES=20000
    MAX_STRUCTURAL_CONSTANTS=12

    @classmethod
    def _validate(cls,tree):
        banned=(ast.Import,ast.ImportFrom,ast.Attribute,ast.Global,ast.Nonlocal,ast.With,
                ast.AsyncFunctionDef,ast.ClassDef,ast.Lambda,ast.While,ast.For,ast.AsyncFor,
                ast.Try,ast.Raise,ast.Yield,ast.YieldFrom,ast.Await,ast.Delete)
        if any(isinstance(n,banned) for n in ast.walk(tree)):raise ValueError("UNSAFE_PROGRAM")
        funcs=[n for n in tree.body if isinstance(n,ast.FunctionDef)]
        if len(funcs)!=1 or len(tree.body)!=1:raise ValueError("EXACTLY_ONE_FUNCTION_REQUIRED")
        fname=funcs[0].name
        for n in ast.walk(tree):
            if isinstance(n,ast.Call):
                if not isinstance(n.func,ast.Name):raise ValueError("UNSAFE_CALL")
                if n.func.id not in cls.SAFE_CALLS:raise ValueError("CALL_NOT_ALLOWED")
            if isinstance(n,ast.Name) and n.id.startswith("__"):raise ValueError("DUNDER_FORBIDDEN")
        return fname

    @classmethod
    def execute(cls,source,function_name,args):
        tree=ast.parse(source);fname=cls._validate(tree)
        if fname!=function_name:raise ValueError("FUNCTION_NAME_MISMATCH")
        env=dict(cls.SAFE_CALLS);env["__builtins__"]={}
        exec(compile(tree,"<yado-bounded-program-v3>","exec"),env,env)
        return env[function_name](*args)

    @staticmethod
    def _const_pool(tree,train_examples):
        vals={-2,-1,0,1,2,3}
        for n in ast.walk(tree):
            if isinstance(n,ast.Constant) and isinstance(n.value,int) and not isinstance(n.value,bool):
                vals.update({n.value,n.value-1,n.value+1,n.value-2,n.value+2})
        for args,expected in train_examples:
            for x in tuple(args)+(expected,):
                if isinstance(x,int) and not isinstance(x,bool) and abs(x)<=100:
                    vals.add(x)
        return tuple(sorted(vals,key=lambda x:(abs(x),x)))[:BoundedCompositionalProgramRepairV3.MAX_STRUCTURAL_CONSTANTS]

    @classmethod
    def _atomic_mutations(cls,source,train_examples,enable=("binop","compare","boolop","constant","structural")):
        tree=ast.parse(source);cls._validate(tree);nodes=list(ast.walk(tree));pool=cls._const_pool(tree,train_examples)
        edits=[]
        for idx,n in enumerate(nodes):
            if "binop" in enable and isinstance(n,ast.BinOp):
                for opcls in cls.BIN_OPS:
                    if not isinstance(n.op,opcls):edits.append((idx,"op",opcls()))
            if "compare" in enable and isinstance(n,ast.Compare) and len(n.ops)==1:
                for opcls in cls.CMP_OPS:
                    if not isinstance(n.ops[0],opcls):edits.append((idx,"cmp",opcls()))
            if "boolop" in enable and isinstance(n,ast.BoolOp):
                for opcls in cls.BOOL_OPS:
                    if not isinstance(n.op,opcls):edits.append((idx,"op",opcls()))
            if "constant" in enable and isinstance(n,ast.Constant) and isinstance(n.value,int) and not isinstance(n.value,bool):
                for v in pool:
                    if v!=n.value:edits.append((idx,"value",v))
            if "structural" in enable and isinstance(n,ast.Return) and n.value is not None:
                edits.append((idx,"wrap_abs",None))
                for fn in ("min","max"):
                    for v in pool:edits.append((idx,"wrap_call",(fn,v)))
        seen=set()
        for idx,kind,val in edits:
            t=copy.deepcopy(tree);tn=list(ast.walk(t))[idx]
            if kind=="op":tn.op=val
            elif kind=="cmp":tn.ops[0]=val
            elif kind=="value":tn.value=val
            elif kind=="wrap_abs":
                tn.value=ast.Call(func=ast.Name(id="abs",ctx=ast.Load()),args=[tn.value],keywords=[])
            elif kind=="wrap_call":
                fn,v=val
                tn.value=ast.Call(func=ast.Name(id=fn,ctx=ast.Load()),args=[tn.value,ast.Constant(v)],keywords=[])
            ast.fix_missing_locations(t)
            try:cls._validate(t)
            except Exception:continue
            s=ast.unparse(t)+"\n"
            if s not in seen:
                seen.add(s);yield s

    @classmethod
    def _passes(cls,source,function_name,examples):
        for args,expected in examples:
            try:got=cls.execute(source,function_name,args)
            except Exception:return False
            if got!=expected:return False
        return True

    @classmethod
    def repair(cls,source,function_name,train_examples,max_candidates=None,max_edit_depth=None,
               enabled=("binop","compare","boolop","constant","structural")):
        cls._validate(ast.parse(source))
        max_candidates=min(int(max_candidates or cls.MAX_CANDIDATES),cls.MAX_CANDIDATES)
        max_depth=min(int(max_edit_depth or cls.MAX_EDIT_DEPTH),cls.MAX_EDIT_DEPTH)
        if cls._passes(source,function_name,train_examples):
            return {"source":source,"candidate_count":1,"tried":0,"edit_depth":0}
        frontier=[source];seen={source};tried=0;solutions=[]
        for depth in range(1,max_depth+1):
            nxt=[]
            for base in frontier:
                for cand in cls._atomic_mutations(base,train_examples,enable=enabled):
                    if cand in seen:continue
                    seen.add(cand);tried+=1
                    if tried>max_candidates:
                        return {"source":None,"candidate_count":len(solutions),"tried":tried-1,"edit_depth":None,"reason":"SEARCH_BUDGET"}
                    if cls._passes(cand,function_name,train_examples):
                        solutions.append((depth,cand))
                    else:nxt.append(cand)
            if solutions:
                solutions.sort(key=lambda z:(z[0],len(z[1]),z[1]))
                d,s=solutions[0]
                return {"source":s,"candidate_count":len(solutions),"tried":tried,"edit_depth":d}
            frontier=nxt
        return {"source":None,"candidate_count":0,"tried":tried,"edit_depth":None,"reason":"NO_REPAIR_WITHIN_EDIT_BUDGET"}

__all__=["BoundedCompositionalProgramRepairV3"]
