from __future__ import annotations
import copy,hashlib,itertools,json

def _canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def _digest(o): return hashlib.sha256(_canon(o).encode()).hexdigest()

class GenericEventStateMetaLanguageV1:
    COMPONENT_ID='LANG-G2-GENERIC-EVENT-STATE-META-V1'
    STATE_MODES=('COUNT','SET','STACK')
    CLOSE_POLICIES=('ANY','MATCH_KEY','REMOVE_KEY')
    FAILURE_POLICIES=('REJECT','IGNORE')
    FINAL_POLICIES=('EMPTY_AND_VALID','VALID_ONLY')

    @classmethod
    def execute(cls,program,events):
        open_code=program['open_code']; close_code=program['close_code']
        mode=program['state_mode']; close_policy=program['close_policy']
        underflow=program['underflow_policy']; mismatch=program['mismatch_policy']
        final=program['final_policy']
        count=0; bag=set(); stack=[]; valid=True
        for raw in events:
            if not isinstance(raw,(list,tuple)) or len(raw)!=2:
                return False
            code,key=raw
            if code==open_code:
                if mode=='COUNT':
                    count+=1
                elif mode=='SET':
                    bag.add(key)
                elif mode=='STACK':
                    stack.append(key)
                else:
                    return False
                continue
            if code!=close_code:
                valid=False
                continue
            if mode=='COUNT':
                if count<=0:
                    if underflow=='REJECT': valid=False
                else:
                    count-=1
            elif mode=='SET':
                if key in bag:
                    bag.remove(key)
                elif underflow=='REJECT':
                    valid=False
            elif mode=='STACK':
                if not stack:
                    if underflow=='REJECT': valid=False
                elif close_policy=='ANY':
                    stack.pop()
                elif close_policy=='MATCH_KEY':
                    if stack[-1]==key:
                        stack.pop()
                    elif mismatch=='REJECT':
                        valid=False
                    elif mismatch=='IGNORE':
                        stack.pop()
                elif close_policy=='REMOVE_KEY':
                    if key in stack:
                        idx=len(stack)-1-stack[::-1].index(key)
                        stack.pop(idx)
                    elif mismatch=='REJECT':
                        valid=False
                else:
                    return False
        if final=='VALID_ONLY':
            return bool(valid)
        if mode=='COUNT':
            empty=(count==0)
        elif mode=='SET':
            empty=(len(bag)==0)
        else:
            empty=(len(stack)==0)
        return bool(valid and empty)

    @classmethod
    def accuracy(cls,program,examples):
        if not examples: return 0.0
        ok=0
        for row in examples:
            try: got=cls.execute(program,row['events'])
            except Exception: got=None
            ok += (got is bool(row['expected']))
        return ok/len(examples)

    @classmethod
    def synthesize(cls,examples):
        if not examples:
            raise ValueError('EMPTY_EXAMPLES')
        codes=sorted({str(e[0]) for row in examples for e in row['events']})
        if len(codes)<2:
            return {'status':'WITHHOLD','reason':'INSUFFICIENT_EVENT_CODES','train_accuracy':0.0}
        candidates=[]
        tested=0
        for open_code,close_code in itertools.permutations(codes,2):
            for mode in cls.STATE_MODES:
                for close_policy in cls.CLOSE_POLICIES:
                    for underflow in cls.FAILURE_POLICIES:
                        for mismatch in cls.FAILURE_POLICIES:
                            for final in cls.FINAL_POLICIES:
                                p={
                                  'schema':'yado.g2.generic_event_state_program.v1',
                                  'open_code':open_code,'close_code':close_code,
                                  'state_mode':mode,'close_policy':close_policy,
                                  'underflow_policy':underflow,'mismatch_policy':mismatch,
                                  'final_policy':final,'output':'BOOLEAN',
                                }
                                tested+=1
                                acc=cls.accuracy(p,examples)
                                if acc==1.0:
                                    # Prefer programs with the smallest generic state semantics;
                                    # ties are deterministic and not domain-labelled.
                                    complexity={
                                      'COUNT':1,'SET':2,'STACK':3
                                    }[mode]
                                    p['train_accuracy']=acc
                                    p['search_space_size']=tested
                                    p['program_digest']=_digest(p)
                                    candidates.append((complexity,_canon(p),p))
        if not candidates:
            return {'status':'WITHHOLD','reason':'NO_EXACT_EVENT_STATE_PROGRAM','train_accuracy':0.0,'search_space_size':tested}
        candidates.sort(key=lambda x:(x[0],x[1]))
        p=copy.deepcopy(candidates[0][2])
        p['search_space_size']=tested
        p['program_digest']=_digest({k:v for k,v in p.items() if k!='program_digest'})
        p['synthesized_operator_id']='GENE-SELF-SYNTHESIZED-EVENT-'+p['program_digest'][:16]
        p['novel_gene']=True
        return p

    @classmethod
    def ablations(cls,program):
        out=[]
        alternatives={
          'state_mode':[x for x in cls.STATE_MODES if x!=program['state_mode']],
          'close_policy':[x for x in cls.CLOSE_POLICIES if x!=program['close_policy']],
          'underflow_policy':[x for x in cls.FAILURE_POLICIES if x!=program['underflow_policy']],
          'mismatch_policy':[x for x in cls.FAILURE_POLICIES if x!=program['mismatch_policy']],
          'final_policy':[x for x in cls.FINAL_POLICIES if x!=program['final_policy']],
        }
        for field,vals in alternatives.items():
            for value in vals:
                p=copy.deepcopy(program)
                p[field]=value
                p.pop('synthesized_operator_id',None); p.pop('program_digest',None)
                p['program_digest']=_digest(p)
                out.append({'ablated_field':field,'ablated_value':value,'program':p})
        return out

    @classmethod
    def component(cls):
        x={
          'schema':'yado.g2.generic_event_state_meta_language.v1',
          'component_id':cls.COMPONENT_ID,
          'primitives':['EVENT_CODE','EVENT_KEY','COUNT_STATE','SET_STATE','SEQUENCE_STATE','OPEN_UPDATE','CLOSE_UPDATE','FINAL_PREDICATE'],
          'state_modes':list(cls.STATE_MODES),
          'close_policies':list(cls.CLOSE_POLICIES),
          'failure_policies':list(cls.FAILURE_POLICIES),
          'final_policies':list(cls.FINAL_POLICIES),
          'domain_specific_operator_names':False,
          'bounded_search':True,
          'semantic_boundary':'GENERIC BOUNDED EVENT/STATE META-LANGUAGE. IT SEARCHES STATE UPDATE COMPOSITIONS FROM IO EXAMPLES; IT DOES NOT RECEIVE A NESTING/STACK/PUSHDOWN TASK LABEL.'
        }
        x['component_digest']=_digest(x)
        return x

__all__=['GenericEventStateMetaLanguageV1']
