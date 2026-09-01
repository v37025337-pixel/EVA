from __future__ import annotations
import ast,copy
from fractions import Fraction
from yado_bounded_compositional_program_repair_v3 import BoundedCompositionalProgramRepairV3

class _CanonicalSplitBaseV10:
    COMPONENT_ID="INTERNAL-CANONICAL-SPLIT-BASE-V10"
    BASE=BoundedCompositionalProgramRepairV3
    MAX_EDIT_DEPTH=2
    MAX_CANDIDATES=24000
    BASE_SEARCH_BUDGET=6000
    STRUCTURAL_SEARCH_BUDGET=18000
    MAX_CONDITIONAL_DEPTH=2
    MAX_SPLIT_TESTS=640
    MAX_SEARCH_NODES=4000
    MAX_BRANCH_MODELS=10

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
    def _raw_models(cls,tree,function_name,base,examples):
        vals=cls._base_values(tree,function_name,base,examples)
        if vals is None or not vals:return []
        out=[(copy.deepcopy(base),'IDENTITY',1),
             (ast.Call(func=ast.Name(id='abs',ctx=ast.Load()),args=[copy.deepcopy(base)],keywords=[]),'ABS',2)]
        ys=[e for _,e in vals]
        if all(y==ys[0] for y in ys):out.append((ast.Constant(ys[0]),'CONSTANT',3))
        try:
            diffs=[Fraction(y)-Fraction(x) for x,y in vals]
            if diffs and all(d==diffs[0] for d in diffs) and diffs[0].denominator==1:
                out.append((cls._add(base,int(diffs[0])),'OFFSET',2))
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
                out.append((cls._mul(base,int(ratio)),'SCALE',2))
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
                        out.append((e,'AFFINE',3))
                    break
        except Exception:pass
        return out

    @classmethod
    def _rank_models(cls,tree,function_name,base,subset,global_examples):
        candidates=[]
        for expr,label,complexity in cls._raw_models(tree,function_name,base,subset):
            try:
                src=cls._emit(tree,expr)
                if not all(cls.execute(src,function_name,args)==expected for args,expected in subset):continue
                support=sum(cls.execute(src,function_name,args)==expected for args,expected in global_examples)
                candidates.append((support,-complexity,label,ast.dump(expr),expr))
            except Exception:continue
        candidates.sort(key=lambda z:(-z[0],-z[1],z[2],z[3]))
        return [z[-1] for z in candidates[:cls.MAX_BRANCH_MODELS]]

    @classmethod
    def _test_value(cls,tree,function_name,test,args):
        return bool(cls.execute(cls._emit(tree,test),function_name,args))

    @classmethod
    def _tests(cls,func,examples):
        out=[]
        argc=len(func.args.args)
        for pos,name in enumerate([a.arg for a in func.args.args]):
            vals=[]
            for args,_ in examples:
                if pos < len(args):
                    v=args[pos]
                    if isinstance(v,(int,float)) and not isinstance(v,bool):
                        vals.append(v)
            uniq=sorted(set(vals))
            # Canonical numeric partitions: boundary is anchored on an observed
            # value, never invented inside an unseen gap.
            for v in uniq[:-1]:
                out.append(ast.Compare(left=ast.Name(id=name,ctx=ast.Load()),ops=[ast.LtE()],comparators=[ast.Constant(v)]))
                out.append(ast.Compare(left=ast.Name(id=name,ctx=ast.Load()),ops=[ast.Gt()],comparators=[ast.Constant(v)]))
                if len(out)>=cls.MAX_SPLIT_TESTS:return out
        return out

    @classmethod
    def _solve_subset(cls,tree,function_name,func,base,subset,global_examples,depth,counter):
        counter[0]+=1
        if counter[0]>cls.MAX_SEARCH_NODES:return None
        direct=cls._rank_models(tree,function_name,base,subset,global_examples)
        if direct:return direct[0]
        if depth<=0:return None
        for test in cls._tests(func,subset):
            try:
                yes=[z for z in subset if cls._test_value(tree,function_name,test,z[0])]
                no=[z for z in subset if not cls._test_value(tree,function_name,test,z[0])]
            except Exception:continue
            if not yes or not no:continue
            left=cls._solve_subset(tree,function_name,func,base,yes,global_examples,depth-1,counter)
            if left is None:continue
            right=cls._solve_subset(tree,function_name,func,base,no,global_examples,depth-1,counter)
            if right is None:continue
            return ast.IfExp(test=copy.deepcopy(test),body=left,orelse=right)
        return None

    @classmethod
    def _structural_candidate(cls,source,function_name,examples):
        tree=ast.parse(source);fname=cls.BASE._validate(tree)
        if fname!=function_name:raise ValueError('FUNCTION_NAME_MISMATCH')
        func=next(n for n in tree.body if isinstance(n,ast.FunctionDef))
        returns=[n for n in ast.walk(func) if isinstance(n,ast.Return) and n.value is not None]
        if len(returns)!=1:return None,0
        counter=[0]
        expr=cls._solve_subset(tree,function_name,func,returns[0].value,examples,examples,cls.MAX_CONDITIONAL_DEPTH,counter)
        if expr is None:return None,counter[0]
        return cls._emit(tree,expr),counter[0]

    @classmethod
    def repair(cls,source,function_name,train_examples,max_candidates=None,max_edit_depth=None,enabled=('binop','compare','boolop','constant','structural')):
        total=min(int(max_candidates or cls.MAX_CANDIDATES),cls.MAX_CANDIDATES)
        depth=min(int(max_edit_depth or cls.MAX_EDIT_DEPTH),cls.MAX_EDIT_DEPTH)
        base_budget=min(cls.BASE_SEARCH_BUDGET,total)
        base=cls.BASE.repair(source,function_name,train_examples,max_candidates=base_budget,max_edit_depth=depth,enabled=enabled)
        if base.get('source'):
            out=dict(base);out['repair_mode']='BASE_PORTFOLIO';return out
        cand,nodes=cls._structural_candidate(source,function_name,train_examples)
        if nodes>cls.STRUCTURAL_SEARCH_BUDGET:
            return {'source':None,'reason':'STRUCTURAL_SEARCH_BUDGET','search_nodes':nodes,'repair_mode':'SUPPORT_RANKED_RECURSIVE'}
        if cand and cls._passes(cand,function_name,train_examples):
            return {'source':cand,'search_nodes':nodes,'repair_mode':'SUPPORT_RANKED_RECURSIVE','conditional_depth':cls.MAX_CONDITIONAL_DEPTH}
        return {'source':None,'reason':'NO_REPAIR_WITHIN_SUPPORT_RANKED_BUDGET','search_nodes':nodes,'repair_mode':'SUPPORT_RANKED_RECURSIVE'}

__all__=[]


class AmbiguityAwareProgramRepairV11(_CanonicalSplitBaseV10):
    COMPONENT_ID="ALG-G2-AMBIGUITY-AWARE-PROGRAM-REPAIR-V11"

    @classmethod
    def _mutate_threshold(cls,source,node_index,new_value):
        tree=ast.parse(source)
        comps=[n for n in ast.walk(tree) if isinstance(n,ast.Compare) and len(n.ops)==1 and len(n.comparators)==1 and isinstance(n.comparators[0],ast.Constant)]
        if node_index>=len(comps):return None
        comps[node_index].comparators[0].value=new_value
        ast.fix_missing_locations(tree)
        try:cls.BASE._validate(tree)
        except Exception:return None
        return ast.unparse(tree)+"\n"

    @classmethod
    def _threshold_ambiguity(cls,source,function_name,examples):
        tree=ast.parse(source)
        func=next(n for n in tree.body if isinstance(n,ast.FunctionDef))
        arg_names=[a.arg for a in func.args.args]
        comps=[n for n in ast.walk(tree) if isinstance(n,ast.Compare) and len(n.ops)==1 and len(n.comparators)==1 and isinstance(n.left,ast.Name) and isinstance(n.comparators[0],ast.Constant)]
        for idx,node in enumerate(comps):
            name=node.left.id
            if name not in arg_names:continue
            pos=arg_names.index(name);k=node.comparators[0].value
            if not isinstance(k,int) or isinstance(k,bool):continue
            observed=sorted(set(args[pos] for args,_ in examples if pos<len(args) and isinstance(args[pos],int) and not isinstance(args[pos],bool)))
            if not observed:continue
            for alt_k in (k-1,k+1):
                alt=cls._mutate_threshold(source,idx,alt_k)
                if not alt or not cls._passes(alt,function_name,examples):continue
                # Find an integer probe in/near the unobserved threshold gap on which the programs disagree.
                probe_values=sorted(set([k-1,k,k+1,alt_k-1,alt_k,alt_k+1]))
                for pv in probe_values:
                    if pv in observed:continue
                    base_args=list(examples[0][0])
                    if pos>=len(base_args):continue
                    base_args[pos]=pv;args=tuple(base_args)
                    try:
                        a=cls.execute(source,function_name,args);b=cls.execute(alt,function_name,args)
                    except Exception:continue
                    if a!=b:
                        return {'ambiguous':True,'arg':name,'threshold':k,'alternative_threshold':alt_k,'probe_value':pv,'outputs':[a,b]}
        return {'ambiguous':False}

    @classmethod
    def repair(cls,source,function_name,train_examples,max_candidates=None,max_edit_depth=None,enabled=('binop','compare','boolop','constant','structural')):
        r=super().repair(source,function_name,train_examples,max_candidates=max_candidates,max_edit_depth=max_edit_depth,enabled=enabled)
        if not r.get('source'):return r
        ambiguity=cls._threshold_ambiguity(r['source'],function_name,train_examples)
        if ambiguity.get('ambiguous'):
            return {'source':None,'reason':'AMBIGUOUS_UNSEEN_THRESHOLD','ambiguity':ambiguity,'repair_mode':'AMBIGUITY_AWARE_WITHHOLD'}
        out=dict(r);out['ambiguity_checked']=True;return out

__all__=['AmbiguityAwareProgramRepairV11']
