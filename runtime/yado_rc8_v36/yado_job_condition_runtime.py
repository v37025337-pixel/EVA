from __future__ import annotations
import re, math
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

class UnsupportedExpression(RuntimeError): pass

_TOKEN=re.compile(r"\s*(?:(\&\&|\|\||==|!=|!|\(|\)|,)|('(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\")|([A-Za-z_][A-Za-z0-9_.*-]*|-?\d+(?:\.\d+)?))")

def normalize_expr(expr:str)->str:
    s=(expr or '').strip()
    if s.startswith('${{') and s.endswith('}}'):s=s[3:-2].strip()
    return ' '.join(s.split())

def discover_operators(expr:str)->set[str]:
    s=normalize_expr(expr);ops=set()
    if '&&' in s:ops.add('AND')
    if '||' in s:ops.add('OR')
    if '==' in s:ops.add('EQ')
    if '!=' in s:ops.add('NEQ')
    if re.search(r'(?<![=!])!(?!=)',s):ops.add('NOT')
    funcs={'startsWith':'STARTS_WITH','contains':'CONTAINS','always':'ALWAYS','success':'SUCCESS','failure':'FAILURE'}
    for f,o in funcs.items():
        if re.search(rf'\b{re.escape(f)}\s*\(',s):ops.add(o)
    # A lone variable/function-free expression is GitHub truthiness.
    if not ops and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.*-]*',s):ops.add('TRUTHY')
    return ops

class JobConditionRuntime:
    def __init__(self,operators:Sequence[str]):self.operators=set(map(str,operators))
    def _need(self,op):
        if op not in self.operators:raise UnsupportedExpression(f'operator {op} not enabled')
    def evaluate(self,expr:str,context:Mapping[str,Any])->bool:
        s=normalize_expr(expr)
        if not s:return True
        toks=[];pos=0
        while pos<len(s):
            m=_TOKEN.match(s,pos)
            if not m:raise UnsupportedExpression(f'unparsed token near {s[pos:pos+30]!r}')
            toks.append(m.group(1) or m.group(2) or m.group(3));pos=m.end()
        self.toks=toks;self.i=0;self.ctx=dict(context)
        v=self._or()
        if self.i!=len(self.toks):raise UnsupportedExpression('trailing tokens')
        return self._truth(v)
    def _peek(self):return self.toks[self.i] if self.i<len(self.toks) else None
    def _eat(self,t=None):
        if self.i>=len(self.toks):raise UnsupportedExpression('unexpected end')
        v=self.toks[self.i]
        if t is not None and v!=t:raise UnsupportedExpression(f'expected {t}, got {v}')
        self.i+=1;return v
    def _truth(self,v):
        if isinstance(v,bool):return v
        self._need('TRUTHY');return bool(v)
    def _or(self):
        v=self._and()
        while self._peek()=='||':
            self._need('OR'); self._eat(); rhs=self._and(); v=self._truth(v) or self._truth(rhs)
        return v
    def _and(self):
        v=self._unary()
        while self._peek()=='&&':
            self._need('AND'); self._eat(); rhs=self._unary(); v=self._truth(v) and self._truth(rhs)
        return v
    def _unary(self):
        if self._peek()=='!':self._need('NOT');self._eat();return not self._truth(self._unary())
        return self._cmp()
    def _cmp(self):
        a=self._primary();p=self._peek()
        if p=='==':self._need('EQ');self._eat();return a==self._primary()
        if p=='!=':self._need('NEQ');self._eat();return a!=self._primary()
        return a
    def _primary(self):
        p=self._peek()
        if p=='(':
            self._eat('(');v=self._or();self._eat(')');return v
        t=self._eat()
        if (t.startswith("'") and t.endswith("'")) or (t.startswith('"') and t.endswith('"')):return bytes(t[1:-1],'utf-8').decode('unicode_escape')
        if re.fullmatch(r'-?\d+(?:\.\d+)?',t):return float(t) if '.' in t else int(t)
        if self._peek()=='(':
            self._eat('(');args=[]
            if self._peek()!=')':
                while True:
                    args.append(self._or())
                    if self._peek()!=',':break
                    self._eat(',')
            self._eat(')')
            if t=='startsWith':self._need('STARTS_WITH');return str(args[0]).startswith(str(args[1]))
            if t=='contains':self._need('CONTAINS');return args[1] in args[0]
            if t=='always':self._need('ALWAYS');return True
            if t=='success':self._need('SUCCESS');return bool(self.ctx.get('__job_success__',True))
            if t=='failure':self._need('FAILURE');return not bool(self.ctx.get('__job_success__',True))
            raise UnsupportedExpression(f'unknown function {t}')
        return self.ctx.get(t,'')

def matrix_cardinality(dimensions:Sequence[int])->int:
    return math.prod(int(x) for x in dimensions) if dimensions else 1

def eligible_job_instances(needs:Sequence[str],needs_status:Mapping[str,str],expr:str|None,context:Mapping[str,Any],dimensions:Sequence[int],operators:Sequence[str]):
    needs_ok=all(str(needs_status.get(n,'success')).lower()=='success' for n in needs)
    has_always='ALWAYS' in discover_operators(expr or '')
    if needs and not needs_ok and not has_always:return 0
    if expr:
        try:ok=JobConditionRuntime(operators).evaluate(expr,context)
        except UnsupportedExpression:return None
        if not ok:return 0
    return matrix_cardinality(dimensions)

__all__=['UnsupportedExpression','normalize_expr','discover_operators','JobConditionRuntime','matrix_cardinality','eligible_job_instances']
