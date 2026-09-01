from __future__ import annotations
from fractions import Fraction

class BudgetAdaptiveCompositionalLogicV2:
    COMPONENT_ID="ALG-G2-BUDGET-ADAPTIVE-COMPOSITIONAL-LOGIC-V2"
    MAX_BOOLEAN_CELLS=262144
    MAX_POLYNOMIAL_TERMS=20
    MAX_POLYNOMIAL_ROWS=256

    @classmethod
    def learn_symmetric_boolean(cls,rows):
        if not rows:raise ValueError("EMPTY_ROWS")
        fields=sorted(rows[0]["input"])
        if len(rows)*max(1,len(fields))>cls.MAX_BOOLEAN_CELLS:
            return {"kind":"WITHHOLD","reason":"BOOLEAN_WORK_BUDGET","fields":[],"count_to_output":{},"default":None}
        mapping={};counts={}
        for row in rows:
            if set(row["input"])!=set(fields):raise ValueError("SCHEMA_DRIFT")
            if any(not isinstance(row["input"].get(f),bool) for f in fields):raise ValueError("NON_BOOLEAN_FIELD")
            c=sum(row["input"][f] for f in fields);y=row["expected"]
            if c in mapping and mapping[c]!=y:raise ValueError("NOT_SYMMETRIC_DETERMINISTIC")
            mapping[c]=y;counts[y]=counts.get(y,0)+1
        default=sorted(counts,key=lambda y:(-counts[y],str(y)))[0]
        return {"kind":"SYMMETRIC_COUNT_MAP_V2","fields":fields,"count_to_output":mapping,"default":default,
                "work_cells":len(rows)*len(fields)}

    @staticmethod
    def predict_symmetric_boolean(model,x):
        if model.get("kind")=="WITHHOLD":raise ValueError("BOOLEAN_WORK_BUDGET")
        c=sum(bool(x.get(f,False)) for f in model["fields"])
        return model["count_to_output"].get(c,model["default"])

    @staticmethod
    def _basis(degree):
        out=[]
        for total in range(int(degree)+1):
            for i in range(total+1):out.append((i,total-i))
        return out

    @classmethod
    def _fit_degree(cls,rows,degree):
        basis=cls._basis(degree)
        if len(basis)>cls.MAX_POLYNOMIAL_TERMS or len(rows)>cls.MAX_POLYNOMIAL_ROWS:return None
        A=[]
        for r in rows:
            x=Fraction(r["x"]);y=Fraction(r["y"]);z=Fraction(r["expected"])
            A.append([x**i*y**j for i,j in basis]+[z])
        m=len(A);n=len(basis);rank=0;pivots=[]
        for col in range(n):
            pivot=next((i for i in range(rank,m) if A[i][col]!=0),None)
            if pivot is None:continue
            A[rank],A[pivot]=A[pivot],A[rank]
            q=A[rank][col];A[rank]=[v/q for v in A[rank]]
            for i in range(m):
                if i==rank or A[i][col]==0:continue
                q=A[i][col];A[i]=[a-q*b for a,b in zip(A[i],A[rank])]
            pivots.append(col);rank+=1
        for row in A:
            if all(row[c]==0 for c in range(n)) and row[-1]!=0:return None
        if rank<n:return None
        coeff=[Fraction(0) for _ in range(n)]
        for rix,col in enumerate(pivots[:n]):coeff[col]=A[rix][-1]
        model={"kind":"EXACT_BOUNDED_POLYNOMIAL_V2","degree":degree,"basis":basis,"coeff":coeff,
               "term_count":len(basis),"row_count":len(rows)}
        if all(cls.predict_polynomial(model,r["x"],r["y"])==Fraction(r["expected"]) for r in rows):return model
        return None

    @classmethod
    def fit_polynomial(cls,rows,max_degree=8):
        if not rows or len(rows)>cls.MAX_POLYNOMIAL_ROWS:
            return {"kind":"WITHHOLD","reason":"POLYNOMIAL_ROW_BUDGET","degree":None,"basis":[],"coeff":[]}
        for d in range(int(max_degree)+1):
            basis=cls._basis(d)
            if len(basis)>cls.MAX_POLYNOMIAL_TERMS:
                return {"kind":"WITHHOLD","reason":"POLYNOMIAL_TERM_BUDGET","degree":None,"basis":[],"coeff":[]}
            m=cls._fit_degree(rows,d)
            if m is not None:return m
        return {"kind":"WITHHOLD","reason":"NO_EXACT_MODEL_WITHIN_BUDGET","degree":None,"basis":[],"coeff":[]}

    @staticmethod
    def predict_polynomial(model,x,y):
        if model.get("kind")=="WITHHOLD":raise ValueError(model.get("reason","NO_POLYNOMIAL"))
        x=Fraction(x);y=Fraction(y)
        return sum(c*x**i*y**j for c,(i,j) in zip(model["coeff"],model["basis"]))
