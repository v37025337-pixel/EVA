from __future__ import annotations
from dataclasses import dataclass
from itertools import product
import copy,hashlib,json

def _canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def _digest(o):return hashlib.sha256(_canon(o).encode()).hexdigest()

class GenericRelationalMetaLanguageV1:
    COMPONENT_ID='LANG-G2-GENERIC-RELATIONAL-STATE-META-V1'
    DIRECTIONS=('FORWARD','REVERSE')
    MERGES=('REPLACE','UNION','INTERSECT')
    ITERATIONS=('ONCE','TWICE','THRICE','UNTIL_STABLE')
    SEEDS=('START','RELATION_LEFT_DOMAIN','RELATION_RIGHT_DOMAIN')
    MAX_STABLE_STEPS=64
    MAX_CANDIDATES=96

    @staticmethod
    def _norm_relation(relation):
        out=[]
        for e in relation:
            if not isinstance(e,(list,tuple)) or len(e)!=2:raise ValueError('RELATION_EDGE_ARITY')
            a,b=e
            if not isinstance(a,(str,int)) or not isinstance(b,(str,int)):raise ValueError('RELATION_ATOM_TYPE')
            out.append((a,b))
        if len(out)>256:raise ValueError('RELATION_EDGE_BUDGET')
        return tuple(out)

    @staticmethod
    def _norm_start(start):
        if isinstance(start,(str,int)):return {start}
        if isinstance(start,(list,tuple,set,frozenset)):
            xs=set(start)
            if len(xs)>64:raise ValueError('START_SET_BUDGET')
            return xs
        raise ValueError('START_TYPE')

    @classmethod
    def _seed(cls,program,relation,start):
        if program['seed']=='START':return cls._norm_start(start)
        if program['seed']=='RELATION_LEFT_DOMAIN':return {a for a,_ in relation}
        if program['seed']=='RELATION_RIGHT_DOMAIN':return {b for _,b in relation}
        raise ValueError('UNKNOWN_SEED')

    @staticmethod
    def _image(relation,state,direction):
        if direction=='FORWARD':return {b for a,b in relation if a in state}
        if direction=='REVERSE':return {a for a,b in relation if b in state}
        raise ValueError('UNKNOWN_DIRECTION')

    @staticmethod
    def _merge(state,image,mode):
        if mode=='REPLACE':return set(image)
        if mode=='UNION':return set(state)|set(image)
        if mode=='INTERSECT':return set(state)&set(image)
        raise ValueError('UNKNOWN_MERGE')

    @classmethod
    def execute(cls,program,relation,start):
        rel=cls._norm_relation(relation)
        state=cls._seed(program,rel,start)
        def step(x):
            return cls._merge(x,cls._image(rel,x,program['direction']),program['merge'])
        mode=program['iteration']
        if mode=='ONCE':state=step(state)
        elif mode=='TWICE':
            state=step(state);state=step(state)
        elif mode=='THRICE':
            state=step(state);state=step(state);state=step(state)
        elif mode=='UNTIL_STABLE':
            for _ in range(cls.MAX_STABLE_STEPS):
                nxt=step(state)
                if nxt==state:break
                state=nxt
            else:raise RuntimeError('STABLE_ITERATION_BUDGET')
        else:raise ValueError('UNKNOWN_ITERATION')
        return tuple(sorted(state,key=lambda x:(str(type(x)),str(x))))

    @classmethod
    def candidate_programs(cls):
        out=[]
        for seed,direction,merge,iteration in product(cls.SEEDS,cls.DIRECTIONS,cls.MERGES,cls.ITERATIONS):
            p={'seed':seed,'direction':direction,'merge':merge,'iteration':iteration,'output':'STATE'}
            p['program_digest']=_digest(p)
            out.append(p)
        if len(out)>cls.MAX_CANDIDATES:raise RuntimeError('META_LANGUAGE_CANDIDATE_BUDGET')
        return out

    @classmethod
    def synthesize(cls,train_examples):
        if not train_examples:raise ValueError('EMPTY_TRAIN')
        ranked=[]
        for p in cls.candidate_programs():
            ok=0
            for ex in train_examples:
                try:got=cls.execute(p,ex['relation'],ex['start'])
                except Exception:got=None
                if got==tuple(ex['expected']):ok+=1
            acc=ok/len(train_examples)
            complexity=(
              {'START':0,'RELATION_LEFT_DOMAIN':2,'RELATION_RIGHT_DOMAIN':2}[p['seed']]
              + {'FORWARD':0,'REVERSE':1}[p['direction']]
              + {'REPLACE':0,'UNION':1,'INTERSECT':2}[p['merge']]
              + {'ONCE':0,'TWICE':1,'THRICE':2,'UNTIL_STABLE':3}[p['iteration']]
            )
            ranked.append((-acc,complexity,p['program_digest'],p))
        ranked.sort()
        best=copy.deepcopy(ranked[0][3])
        best['train_accuracy']=-ranked[0][0]
        best['search_space_size']=len(ranked)
        best['synthesized_operator_id']='GENE-SELF-SYNTHESIZED-'+best['program_digest'][:16]
        best['novel_gene']=True
        return best

    @classmethod
    def ablations(cls,program):
        xs=[]
        for field,values in [
          ('direction',cls.DIRECTIONS),
          ('merge',cls.MERGES),
          ('iteration',cls.ITERATIONS),
          ('seed',cls.SEEDS),
        ]:
            for value in values:
                if value==program[field]:continue
                p=copy.deepcopy(program);p[field]=value
                for k in ('train_accuracy','search_space_size','synthesized_operator_id','novel_gene','program_digest'):p.pop(k,None)
                p['program_digest']=_digest(p)
                xs.append({'ablated_field':field,'ablated_value':value,'program':p})
        return xs

    @classmethod
    def component(cls):
        x={
          'schema':'yado.g2.generic_relational_state_meta_language.v1',
          'component_id':cls.COMPONENT_ID,
          'primitive_categories':['SEED','RELATIONAL_IMAGE','STATE_MERGE','BOUNDED_ITERATION'],
          'full_task_operator_predeclared':False,
          'candidate_program_count':len(cls.candidate_programs()),
          'max_stable_steps':cls.MAX_STABLE_STEPS,
          'arbitrary_python_generation':False,
          'canonical_active':False,
          'architecture_mutation':False,
          'semantic_boundary':'GENERIC BOUNDED PROGRAM SEARCH OVER RELATION/STATE PRIMITIVES. NO DOMAIN-SPECIFIC REACHABILITY/ANCESTRY/DEPENDENCY OPERATOR IS PREDECLARED.'
        }
        x['component_digest']=_digest(x);return x

__all__=['GenericRelationalMetaLanguageV1']
