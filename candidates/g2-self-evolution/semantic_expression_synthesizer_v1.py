from __future__ import annotations

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
