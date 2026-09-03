from __future__ import annotations
import copy,hashlib,itertools,json,math

def _canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def _digest(o): return hashlib.sha256(_canon(o).encode()).hexdigest()

class GenericWeightedStateMetaLanguageV1:
    COMPONENT_ID='LANG-G2-GENERIC-WEIGHTED-STATE-META-V1'
    DIRECTIONS=('FORWARD','REVERSE')
    COMBINES=('PLUS','EDGE_ONLY','MAX')
    AGGREGATES=('MIN','MAX')
    ITERATIONS=('ONCE','TWICE','THRICE','UNTIL_STABLE')

    @classmethod
    def execute(cls,program,relation,start):
        direction=program['direction']; combine=program['combine']
        aggregate=program['aggregate']; iteration=program['iteration']
        dist={start:0}
        edges=list(relation)
        max_rounds={'ONCE':1,'TWICE':2,'THRICE':3,'UNTIL_STABLE':256}[iteration]
        for _ in range(max_rounds):
            before=dict(dist)
            nxt=dict(dist)
            for raw in edges:
                if not isinstance(raw,(list,tuple)) or len(raw)!=3:
                    raise ValueError('BAD_WEIGHTED_EDGE')
                a,b,w=raw
                if direction=='REVERSE':
                    a,b=b,a
                if a not in dist:
                    continue
                base=dist[a]
                if combine=='PLUS':
                    cand=base+w
                elif combine=='EDGE_ONLY':
                    cand=w
                elif combine=='MAX':
                    cand=max(base,w)
                else:
                    raise ValueError('BAD_COMBINE')
                if b not in nxt:
                    nxt[b]=cand
                elif aggregate=='MIN':
                    if cand<nxt[b]: nxt[b]=cand
                elif aggregate=='MAX':
                    if cand>nxt[b]: nxt[b]=cand
                else:
                    raise ValueError('BAD_AGGREGATE')
            dist=nxt
            if iteration=='UNTIL_STABLE' and dist==before:
                break
        return tuple(sorted(((k,dist[k]) for k in dist),key=lambda kv:(str(type(kv[0])),str(kv[0]))))

    @classmethod
    def accuracy(cls,program,examples):
        if not examples: return 0.0
        ok=0
        for row in examples:
            try: got=cls.execute(program,row['relation'],row['start'])
            except Exception: got=None
            ok += (got==row['expected'])
        return ok/len(examples)

    @classmethod
    def synthesize(cls,examples):
        if not examples:
            raise ValueError('EMPTY_EXAMPLES')
        exact=[]
        tested=0
        for direction,combine,aggregate,iteration in itertools.product(
            cls.DIRECTIONS,cls.COMBINES,cls.AGGREGATES,cls.ITERATIONS
        ):
            p={
              'schema':'yado.g2.generic_weighted_state_program.v1',
              'direction':direction,'combine':combine,'aggregate':aggregate,
              'iteration':iteration,'seed':'START_ZERO','output':'WEIGHTED_STATE_MAP',
            }
            tested+=1
            acc=cls.accuracy(p,examples)
            if acc==1.0:
                complexity={
                  'ONCE':1,'TWICE':2,'THRICE':3,'UNTIL_STABLE':4
                }[iteration]
                # Prefer fewer semantic commitments, deterministic ties.
                p['train_accuracy']=1.0
                p['search_space_size']=tested
                p['program_digest']=_digest(p)
                exact.append((complexity,_canon(p),p))
        if not exact:
            return {'status':'WITHHOLD','reason':'NO_EXACT_WEIGHTED_STATE_PROGRAM','train_accuracy':0.0,'search_space_size':tested}
        exact.sort(key=lambda x:(x[0],x[1]))
        p=copy.deepcopy(exact[0][2])
        p['search_space_size']=tested
        p['program_digest']=_digest({k:v for k,v in p.items() if k!='program_digest'})
        p['synthesized_operator_id']='GENE-SELF-SYNTHESIZED-WEIGHTED-'+p['program_digest'][:16]
        p['novel_gene']=True
        return p

    @classmethod
    def ablations(cls,program):
        out=[]
        alternatives={
          'direction':[x for x in cls.DIRECTIONS if x!=program['direction']],
          'combine':[x for x in cls.COMBINES if x!=program['combine']],
          'aggregate':[x for x in cls.AGGREGATES if x!=program['aggregate']],
          'iteration':[x for x in cls.ITERATIONS if x!=program['iteration']],
        }
        for field,vals in alternatives.items():
            for value in vals:
                p=copy.deepcopy(program)
                p[field]=value
                p.pop('synthesized_operator_id',None);p.pop('program_digest',None)
                p['program_digest']=_digest(p)
                out.append({'ablated_field':field,'ablated_value':value,'program':p})
        return out

    @classmethod
    def component(cls):
        x={
          'schema':'yado.g2.generic_weighted_state_meta_language.v1',
          'component_id':cls.COMPONENT_ID,
          'primitives':['WEIGHTED_EDGE','SOURCE_SEED','STATE_VALUE','EDGE_COMBINE','STATE_AGGREGATE','ITERATION_POLICY'],
          'directions':list(cls.DIRECTIONS),
          'combines':list(cls.COMBINES),
          'aggregates':list(cls.AGGREGATES),
          'iterations':list(cls.ITERATIONS),
          'domain_specific_operator_names':False,
          'bounded_search':True,
          'semantic_boundary':'GENERIC BOUNDED WEIGHTED-STATE META-LANGUAGE. IT SEARCHES EDGE/STATE UPDATE COMPOSITIONS FROM IO EXAMPLES; IT DOES NOT RECEIVE A SHORTEST-PATH, BELLMAN-FORD, DIJKSTRA, OR SEMIRING OPERATOR NAME.'
        }
        x['component_digest']=_digest(x);return x

__all__=['GenericWeightedStateMetaLanguageV1']
