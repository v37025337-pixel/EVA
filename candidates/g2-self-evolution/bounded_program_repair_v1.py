from __future__ import annotations
import ast,copy

class BoundedProgramRepairV1:
    COMPONENT_ID="ALG-G2-BOUNDED-PROGRAM-REPAIR-V1"
    SAFE_CALLS={"min":min,"max":max,"all":all,"any":any,"sum":sum,"abs":abs,"len":len}
    BIN_OPS=(ast.Add,ast.Sub,ast.Mult,ast.Mod)
    CMP_OPS=(ast.Eq,ast.NotEq,ast.Lt,ast.LtE,ast.Gt,ast.GtE)
    BOOL_OPS=(ast.And,ast.Or)

    @classmethod
    def _validate(cls,tree):
        banned=(ast.Import,ast.ImportFrom,ast.Attribute,ast.Global,ast.Nonlocal,ast.With,
                ast.AsyncFunctionDef,ast.ClassDef,ast.Lambda,ast.While,ast.For,ast.AsyncFor,
                ast.Try,ast.Raise,ast.Yield,ast.YieldFrom,ast.Await,ast.Delete)
        if any(isinstance(n,banned) for n in ast.walk(tree)):
            raise ValueError("UNSAFE_PROGRAM")
        funcs=[n for n in tree.body if isinstance(n,ast.FunctionDef)]
        if len(funcs)!=1 or len(tree.body)!=1:
            raise ValueError("EXACTLY_ONE_FUNCTION_REQUIRED")
        fname=funcs[0].name
        for n in ast.walk(tree):
            if isinstance(n,ast.Call):
                if not isinstance(n.func,ast.Name):
                    raise ValueError("UNSAFE_CALL")
                if n.func.id not in cls.SAFE_CALLS:
                    raise ValueError("CALL_NOT_ALLOWED")
            if isinstance(n,ast.Name) and n.id.startswith("__"):
                raise ValueError("DUNDER_FORBIDDEN")
        return fname

    @classmethod
    def execute(cls,source,function_name,args):
        tree=ast.parse(source)
        fname=cls._validate(tree)
        if fname!=function_name:
            raise ValueError("FUNCTION_NAME_MISMATCH")
        glb={"__builtins__":{}}
        loc=dict(cls.SAFE_CALLS)
        exec(compile(tree,"<yado-bounded-program>","exec"),glb,loc)
        return loc[function_name](*args)

    @classmethod
    def _mutations(cls,source,enabled=("binop","compare","boolop","constant")):
        tree=ast.parse(source);cls._validate(tree)
        all_nodes=list(ast.walk(tree))
        edits=[]
        for n in all_nodes:
            if "binop" in enabled and isinstance(n,ast.BinOp):
                for opcls in cls.BIN_OPS:
                    if not isinstance(n.op,opcls):edits.append((all_nodes.index(n),"op",opcls()))
            if "compare" in enabled and isinstance(n,ast.Compare) and len(n.ops)==1:
                for opcls in cls.CMP_OPS:
                    if not isinstance(n.ops[0],opcls):edits.append((all_nodes.index(n),"cmp",opcls()))
            if "boolop" in enabled and isinstance(n,ast.BoolOp):
                for opcls in cls.BOOL_OPS:
                    if not isinstance(n.op,opcls):edits.append((all_nodes.index(n),"op",opcls()))
            if "constant" in enabled and isinstance(n,ast.Constant) and isinstance(n.value,int) and not isinstance(n.value,bool):
                for v in (n.value-2,n.value-1,n.value+1,n.value+2,0,1,2,3):
                    if v!=n.value:edits.append((all_nodes.index(n),"value",v))
        seen=set()
        for idx,kind,val in edits:
            t=copy.deepcopy(tree);tn=list(ast.walk(t))[idx]
            if kind=="op":tn.op=val
            elif kind=="cmp":tn.ops[0]=val
            else:tn.value=val
            ast.fix_missing_locations(t)
            s=ast.unparse(t)+"\n"
            if s not in seen:
                seen.add(s);yield s

    @classmethod
    def repair(cls,source,function_name,train_examples,max_candidates=10000,enabled=("binop","compare","boolop","constant")):
        cls._validate(ast.parse(source))
        tried=0;solutions=[]
        for cand in cls._mutations(source,enabled=enabled):
            tried+=1
            if tried>max_candidates:break
            ok=True
            for args,expected in train_examples:
                try:got=cls.execute(cand,function_name,args)
                except Exception:ok=False;break
                if got!=expected:ok=False;break
            if ok:solutions.append(cand)
        solutions.sort(key=lambda s:(len(s),s))
        return {"source":solutions[0] if solutions else None,"candidate_count":len(solutions),"tried":tried}

__all__=["BoundedProgramRepairV1"]
