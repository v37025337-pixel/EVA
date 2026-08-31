from __future__ import annotations
from fractions import Fraction
from itertools import product

class BoundedCompositionalLogicV1:
    COMPONENT_ID="ALG-G2-BOUNDED-COMPOSITIONAL-LOGIC-V1"
    MAX_BOOLEAN_FIELDS=12
    MAX_POLYNOMIAL_DEGREE=3
    MAX_POLYNOMIAL_TERMS=10

    @classmethod
    def learn_symmetric_boolean(cls,rows):
        if not rows:raise ValueError("EMPTY_ROWS")
        fields=sorted(rows[0]["input"])[:cls.MAX_BOOLEAN_FIELDS]
        mapping={}
        counts={}
        for row in rows:
            if any(not isinstance(row["input"].get(f),bool) for f in fields):raise ValueError("NON_BOOLEAN_FIELD")
            c=sum(row["input"][f] for f in fields);y=row["expected"]
            if c in mapping and mapping[c]!=y:raise ValueError("NOT_SYMMETRIC_DETERMINISTIC")
            mapping[c]=y;counts[y]=counts.get(y,0)+1
        default=sorted(counts,key=lambda y:(-counts[y],str(y)))[0]
        return {"kind":"SYMMETRIC_COUNT_MAP","fields":fields,"count_to_output":mapping,"default":default}

    @staticmethod
    def predict_symmetric_boolean(model,x):
        c=sum(bool(x.get(f,False)) for f in model["fields"])
        return model["count_to_output"].get(c,model["default"])

    @staticmethod
    def _basis(degree):
        out=[]
        for total in range(degree+1):
            for i in range(total+1):out.append((i,total-i))
        return out

    @classmethod
    def _fit_degree(cls,rows,degree):
        basis=cls._basis(degree)
        if len(basis)>cls.MAX_POLYNOMIAL_TERMS:return None
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
        model={"kind":"EXACT_BOUNDED_POLYNOMIAL","degree":degree,"basis":basis,"coeff":coeff}
        if all(cls.predict_polynomial(model,r["x"],r["y"])==Fraction(r["expected"]) for r in rows):return model
        return None

    @classmethod
    def fit_polynomial(cls,rows,max_degree=3):
        cap=min(int(max_degree),cls.MAX_POLYNOMIAL_DEGREE)
        for d in range(cap+1):
            m=cls._fit_degree(rows,d)
            if m is not None:return m
        return {"kind":"WITHHOLD","degree":None,"basis":[],"coeff":[]}

    @staticmethod
    def predict_polynomial(model,x,y):
        if model.get("kind")=="WITHHOLD":raise ValueError("NO_POLYNOMIAL")
        x=Fraction(x);y=Fraction(y)
        return sum(c*x**i*y**j for c,(i,j) in zip(model["coeff"],model["basis"]))
