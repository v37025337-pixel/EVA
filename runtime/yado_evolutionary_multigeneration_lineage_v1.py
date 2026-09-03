from __future__ import annotations
from pathlib import Path
from fractions import Fraction
from itertools import combinations,product,permutations
from collections import defaultdict
import ast,copy,hashlib,json,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_ambiguity_aware_program_repair_v11 import AmbiguityAwareProgramRepairV11

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()

class BooleanDNFLineageGene:
    @staticmethod
    def fit(rows,max_width,max_fields=8,max_rules=64):
        if not rows:raise ValueError('EMPTY_ROWS')
        fields=sorted(rows[0]['input'])
        if len(fields)>max_fields:raise ValueError('FIELD_BUDGET')
        outputs=sorted({str(r['expected']) for r in rows})
        if len(outputs)!=2:raise ValueError('BINARY_OUTPUT_REQUIRED')
        for r in rows:
            if set(r['input'])!=set(fields):raise ValueError('SCHEMA_DRIFT')
            if any(not isinstance(r['input'][f],bool) for f in fields):raise ValueError('BOOLEAN_INPUT_REQUIRED')
        counts={o:sum(str(r['expected'])==o for r in rows) for o in outputs}
        default=sorted(outputs,key=lambda o:(-counts[o],o))[0]
        target=[o for o in outputs if o!=default][0]
        positives={i for i,r in enumerate(rows) if str(r['expected'])==target}
        atoms=[(f,v) for f in fields for v in (False,True)]
        candidates=[]
        for w in range(1,int(max_width)+1):
            for combo in combinations(atoms,w):
                if len({a[0] for a in combo})!=w:continue
                covered={i for i,r in enumerate(rows) if all(r['input'][f] is v for f,v in combo)}
                if covered and covered<=positives:candidates.append((combo,covered))
        uncovered=set(positives);rules=[]
        while uncovered and len(rules)<max_rules:
            scored=[]
            for combo,covered in candidates:
                gain=len(covered & uncovered)
                if gain:scored.append((-gain,len(combo),str(combo),combo,covered))
            if not scored:break
            scored.sort();_,_,_,combo,covered=scored[0]
            rules.append([{'field':f,'value':v} for f,v in combo]);uncovered-=covered
        if uncovered:return {'kind':'WITHHOLD','reason':'DNF_WIDTH_OR_RULE_BUDGET','max_width':max_width}
        return {'kind':'BOOLEAN_DNF_LINEAGE_GENE','fields':fields,'rules':rules,'target':target,'default':default,'max_width':max_width}

    @staticmethod
    def predict(model,x):
        if model.get('kind')=='WITHHOLD':raise ValueError(model.get('reason','DNF_WITHHOLD'))
        for rule in model['rules']:
            if all(x.get(a['field']) is a['value'] for a in rule):return model['target']
        return model['default']

class TriggerRouterLineageGene:
    MAX_TRIGGER_CANDIDATES=4096
    MIN_SUPPORT=4
    MIN_PRECISION=.995
    MAX_RULES=48

    @staticmethod
    def _outs(y):
        if isinstance(y,str):return {y}
        if isinstance(y,(list,tuple,set)):return {str(x) for x in y}
        raise ValueError('UNSUPPORTED_OUTPUT')

    @classmethod
    def fit(cls,cases,fallback,max_width):
        fields=sorted(set().union(*(set(z['input']) for z in cases)))
        outputs=sorted(set().union(*(cls._outs(z['expected']) for z in cases))|{fallback})
        atoms=[]
        for f in fields:
            vals=[]
            for z in cases:
                v=z['input'].get(f)
                if isinstance(v,(bool,str,int,float)) and v not in vals:vals.append(v)
            if 1<len(vals)<=8:
                for v in vals:atoms.append((f,v))
        combos=[]
        for w in range(1,int(max_width)+1):
            for combo in combinations(atoms,w):
                if len({a[0] for a in combo})!=w:continue
                combos.append(combo)
                if len(combos)>cls.MAX_TRIGGER_CANDIDATES:
                    return {'kind':'WITHHOLD','reason':'TRIGGER_CANDIDATE_BUDGET'}
        candidates=defaultdict(list)
        for combo in combos:
            covered={i for i,z in enumerate(cases) if all(z['input'].get(f)==v for f,v in combo)}
            if len(covered)<cls.MIN_SUPPORT:continue
            for out in outputs:
                if out==fallback:continue
                pos={i for i,z in enumerate(cases) if out in cls._outs(z['expected'])}
                precision=len(covered&pos)/len(covered)
                if precision>=cls.MIN_PRECISION:
                    candidates[out].append((combo,covered&pos,len(covered),precision))
        clean={}
        for out in outputs:
            if out==fallback:continue
            pos={i for i,z in enumerate(cases) if out in cls._outs(z['expected'])}
            uncovered=set(pos);rules=[]
            xs=sorted(candidates.get(out,[]),key=lambda z:(len(z[0]),-z[3],-z[2],str(z[0])))
            for combo,cov,support,precision in xs:
                gain=len(cov&uncovered)
                if gain<=0:continue
                rules.append({'atoms':[{'field':f,'value':v} for f,v in combo],'support':support,'precision':precision})
                uncovered-=cov
                if not uncovered or len(rules)>=cls.MAX_RULES:break
            clean[out]=rules
        return {'kind':'TRIGGER_ROUTER_LINEAGE_GENE','fields':fields,'outputs':outputs,'fallback':fallback,'triggers':clean,'max_width':max_width}

    @classmethod
    def route(cls,model,x):
        if model.get('kind')=='WITHHOLD':raise ValueError(model.get('reason','ROUTER_WITHHOLD'))
        selected=[]
        for out in model['outputs']:
            if out==model['fallback']:continue
            for rule in model['triggers'].get(out,[]):
                if all(x.get(a['field'])==a['value'] for a in rule['atoms']):
                    selected.append(out);break
        return tuple(sorted(selected)) if selected else (model['fallback'],)

class PlannerLineageGene:
    MAX_STAGES=8
    MAX_PERMUTATIONS=20000

    @classmethod
    def plan(cls,current,target,budget,stages,objectives):
        xs=[dict(x) for x in stages]
        if len(xs)>cls.MAX_STAGES:return {'action':'WITHHOLD','sequence':[],'reason':'STAGE_BUDGET'}
        candidates=[];tried=0
        for k in range(1,len(xs)+1):
            for seq in permutations(xs,k):
                tried+=1
                if tried>cls.MAX_PERMUTATIONS:return {'action':'WITHHOLD','sequence':[],'reason':'SEARCH_BUDGET'}
                cost=sum(max(0.0,float(s.get('cost',0))) for s in seq)
                if cost>float(budget)+1e-12:continue
                conf=min(1.0,max(0.0,float(current))+sum(max(0.0,float(s.get('expected_gain',0))) for s in seq))
                if conf<float(target):continue
                ids=tuple(str(s['stage_id']) for s in seq)
                key=[cost]
                if 'uncertainty' in objectives:key.append(sum(max(0.0,float(s.get('uncertainty',0))) for s in seq))
                if 'risk' in objectives:key.append(sum(max(0.0,float(s.get('risk',0))) for s in seq))
                if 'latency' in objectives:key.append(sum(max(0.0,float(s.get('latency',1))) for s in seq))
                key.extend([len(seq),-conf,ids])
                candidates.append((tuple(key),seq,conf,cost))
        if not candidates:return {'action':'WITHHOLD','sequence':[],'reason':'NO_FEASIBLE_PLAN'}
        candidates.sort(key=lambda z:z[0]);_,seq,conf,cost=candidates[0]
        return {'action':seq[0]['stage_id'],'sequence':[s['stage_id'] for s in seq],'expected_confidence':conf,'total_cost':cost,'objectives':list(objectives)}

class PolynomialCodeLineageGene:
    PARENT=AmbiguityAwareProgramRepairV11
    @classmethod
    def fit(cls,examples,max_degree):
        pts=[(Fraction(args[0]),Fraction(expected)) for args,expected in examples]
        uniq=[]
        for x,y in pts:
            if all(x!=a for a,_ in uniq):uniq.append((x,y))
        for degree in range(int(max_degree)+1):
            n=degree+1
            if len(uniq)<n:continue
            A=[[x**p for p in range(n)]+[y] for x,y in uniq[:n]]
            ok=True
            for col in range(n):
                pivot=next((i for i in range(col,n) if A[i][col]!=0),None)
                if pivot is None:ok=False;break
                A[col],A[pivot]=A[pivot],A[col]
                q=A[col][col];A[col]=[v/q for v in A[col]]
                for i in range(n):
                    if i==col:continue
                    q=A[i][col]
                    if q!=0:A[i]=[a-q*b for a,b in zip(A[i],A[col])]
            if not ok:continue
            coeff=[A[i][-1] for i in range(n)]
            if all(sum(coeff[p]*(x**p) for p in range(n))==y for x,y in pts):
                return {'kind':'EXACT_UNIVARIATE_POLYNOMIAL_LINEAGE','degree':degree,'coeff':coeff}
        return {'kind':'WITHHOLD','reason':'DEGREE_BUDGET','max_degree':max_degree}

    @staticmethod
    def _expr(coeff,arg):
        terms=[]
        for p,c in enumerate(coeff):
            if c==0:continue
            if c.denominator!=1:raise ValueError('NON_INTEGER_COEFF')
            ci=int(c)
            if p==0:term=ast.Constant(ci)
            else:
                term=ast.Name(id=arg,ctx=ast.Load())
                for _ in range(p-1):term=ast.BinOp(left=term,op=ast.Mult(),right=ast.Name(id=arg,ctx=ast.Load()))
                if ci!=1:term=ast.BinOp(left=ast.Constant(ci),op=ast.Mult(),right=term)
            terms.append(term)
        if not terms:return ast.Constant(0)
        out=terms[0]
        for t in terms[1:]:out=ast.BinOp(left=out,op=ast.Add(),right=t)
        return out

    @classmethod
    def synthesize(cls,source,function_name,examples,max_degree):
        tree=ast.parse(source);fname=cls.PARENT.BASE._validate(tree)
        if fname!=function_name:raise ValueError('FUNCTION_NAME_MISMATCH')
        func=next(n for n in tree.body if isinstance(n,ast.FunctionDef))
        if len(func.args.args)!=1:return {'source':None,'reason':'UNIVARIATE_ONLY'}
        model=cls.fit(examples,max_degree)
        if model.get('kind')=='WITHHOLD':return {'source':None,'reason':model['reason']}
        returns=[n for n in ast.walk(func) if isinstance(n,ast.Return) and n.value is not None]
        if len(returns)!=1:return {'source':None,'reason':'SINGLE_RETURN_REQUIRED'}
        returns[0].value=cls._expr(model['coeff'],func.args.args[0].arg)
        ast.fix_missing_locations(tree);cls.PARENT.BASE._validate(tree)
        out=ast.unparse(tree)+'\n'
        if not cls.PARENT._passes(out,function_name,examples):return {'source':None,'reason':'TRAIN_FAIL'}
        return {'source':out,'degree':model['degree']}

class YADOEvolutionaryMultiGenerationLineageV1:
    COMPONENT_ID='CTRL-G2-EVOLUTIONARY-MULTIGENERATION-LINEAGE-V1'

    def __init__(self,core):
        self.core=core

    @staticmethod
    def _gene(chromosome,gene_id,expression,parent_gene_digest,reason):
        g={'chromosome':chromosome,'gene_id':gene_id,'expression':copy.deepcopy(expression),'parent_gene_digest':parent_gene_digest,'mutation_reason':reason,'shadow_only':True}
        g['gene_digest']=digest(g);return g

    def seed(self):
        base=self.core.evolve_cognitive_code_genome()
        if base.get('selection')!='CHILD' or base.get('promotion_authorized') is not False:
            raise RuntimeError('CANONICAL_CONTROLLER_DID_NOT_PRODUCE_VALID_SHADOW_SEED')
        c=base['child']['chromosomes']
        genes={
          'LOGIC':self._gene('LOGIC','GENE-LOGIC-DNF-W3-LINEAGE-SEED',{'max_width':3},c['LOGIC']['gene_digest'],'INHERIT_SELECTED_SHADOW_CHILD'),
          'THINKING':self._gene('THINKING','GENE-THINKING-LATENCY-LINEAGE-SEED',{'objectives':['latency']},c['THINKING']['gene_digest'],'INHERIT_SELECTED_SHADOW_CHILD'),
          'INTELLIGENCE':self._gene('INTELLIGENCE','GENE-INTELLIGENCE-TRIGGER-W3-LINEAGE-SEED',{'max_trigger_width':3},c['INTELLIGENCE']['gene_digest'],'INHERIT_SELECTED_SHADOW_CHILD'),
          'CODE':self._gene('CODE','GENE-CODE-POLY-D3-LINEAGE-SEED',{'max_degree':3},c['CODE']['gene_digest'],'INHERIT_SELECTED_SHADOW_CHILD'),
        }
        g={
          'schema':'yado.g2.evolutionary_multigeneration.genome.v1','shadow_generation':'S1',
          'parent_canonical_head_digest':self.core.head['canonical_head_digest'],
          'source_shadow_child_digest':base['child']['genome_digest'],'chromosomes':genes,
          'fitness_history':[],'promotion_state':'SHADOW_ONLY'
        }
        g['genome_digest']=digest(g);return g,base

    @staticmethod
    def curriculum(index):
        if index==1:
            return {
              'id':'S1_INHERITED_BASELINE',
              'logic_width':3,'intelligence_width':3,'code_degree':3,
              'thinking_required_objective':'latency',
              'code_fn':lambda x:x**3+x+1,
            }
        if index==2:
            return {
              'id':'S2_FRESH_ESCALATION',
              'logic_width':4,'intelligence_width':4,'code_degree':4,
              'thinking_required_objective':'risk',
              'code_fn':lambda x:x**4+x+1,
            }
        if index==3:
            return {
              'id':'S3_FRESH_ESCALATION',
              'logic_width':5,'intelligence_width':5,'code_degree':5,
              'thinking_required_objective':'uncertainty',
              'code_fn':lambda x:x**5-2*x+3,
            }
        raise ValueError('UNSUPPORTED_SHADOW_GENERATION')

    @classmethod
    def _logic_score(cls,genome,curr):
        width=int(genome['chromosomes']['LOGIC']['expression']['max_width'])
        n=curr['logic_width'];names=[chr(ord('a')+i) for i in range(n)]
        rows=[]
        for bits in product((False,True),repeat=n):
            x=dict(zip(names,bits));y='YES' if all(bits) else 'NO'
            for _ in range(5):rows.append({'input':x,'expected':y})
        try:m=BooleanDNFLineageGene.fit(rows,width)
        except Exception:return 0.0
        hold=[]
        for bits in product((False,True),repeat=n):
            x=dict(zip(names,bits));x['unseen_noise']=sum(bits)%2==0;hold.append((x,'YES' if all(bits) else 'NO'))
        try:return sum(BooleanDNFLineageGene.predict(m,x)==y for x,y in hold)/len(hold)
        except Exception:return 0.0

    @classmethod
    def _thinking_score(cls,genome,curr):
        obj=list(genome['chromosomes']['THINKING']['expression'].get('objectives',[]))
        need=curr['thinking_required_objective']
        if need=='latency':
            stages=[
              {'stage_id':'A_SLOW','cost':1,'expected_gain':.7,'latency':9,'risk':0,'uncertainty':0},
              {'stage_id':'Z_FAST','cost':1,'expected_gain':.7,'latency':1,'risk':0,'uncertainty':0},
            ];want='Z_FAST'
        elif need=='risk':
            stages=[
              {'stage_id':'A_RISKY','cost':1,'expected_gain':.7,'latency':1,'risk':.9,'uncertainty':0},
              {'stage_id':'Z_SAFE','cost':1,'expected_gain':.7,'latency':1,'risk':.1,'uncertainty':0},
            ];want='Z_SAFE'
        else:
            stages=[
              {'stage_id':'A_UNCERTAIN','cost':1,'expected_gain':.7,'latency':1,'risk':.1,'uncertainty':.9},
              {'stage_id':'Z_STABLE','cost':1,'expected_gain':.7,'latency':1,'risk':.1,'uncertainty':.1},
            ];want='Z_STABLE'
        r=PlannerLineageGene.plan(.1,.7,2,stages,obj)
        return 1.0 if r.get('action')==want else 0.0

    @classmethod
    def _intelligence_score(cls,genome,curr):
        width=int(genome['chromosomes']['INTELLIGENCE']['expression']['max_trigger_width'])
        n=curr['intelligence_width'];names=[chr(ord('a')+i) for i in range(n)]
        cases=[]
        for bits in product((False,True),repeat=n):
            for k in range(8):
                x=dict(zip(names,bits));x['noise']=bool(k%2)
                cases.append({'input':x,'expected':'SPECIAL' if all(bits) else 'BASE'})
        try:m=TriggerRouterLineageGene.fit(cases,'BASE',width)
        except Exception:return 0.0
        hold=[]
        for bits in product((False,True),repeat=n):
            x=dict(zip(names,bits));x['noise']=True;x['unseen_noise2']='H'
            hold.append((x,'SPECIAL' if all(bits) else 'BASE'))
        try:return sum((('SPECIAL' in TriggerRouterLineageGene.route(m,x))==(y=='SPECIAL')) for x,y in hold)/len(hold)
        except Exception:return 0.0

    @classmethod
    def _code_score(cls,genome,curr):
        degree=int(genome['chromosomes']['CODE']['expression']['max_degree'])
        fn=curr['code_fn'];src='def f(x):\n    return x\n'
        train=[((x,),fn(x)) for x in range(-3,4)]
        out=PolynomialCodeLineageGene.synthesize(src,'f',train,degree)
        if not out.get('source'):return 0.0
        hold=[((x,),fn(x)) for x in (-7,-6,-5,4,5,6,7)]
        try:return sum(AmbiguityAwareProgramRepairV11.execute(out['source'],'f',args)==y for args,y in hold)/len(hold)
        except Exception:return 0.0

    @classmethod
    def evaluate(cls,genome,curr):
        return {
          'LOGIC':cls._logic_score(genome,curr),
          'THINKING':cls._thinking_score(genome,curr),
          'INTELLIGENCE':cls._intelligence_score(genome,curr),
          'CODE':cls._code_score(genome,curr),
        }

    @classmethod
    def mutate_from_deficits(cls,parent,curr,parent_score):
        genes=copy.deepcopy(parent['chromosomes']);mutations=[]
        if parent_score['LOGIC']<1:
            old=genes['LOGIC'];w=curr['logic_width']
            genes['LOGIC']=cls._gene('LOGIC',f'GENE-LOGIC-DNF-W{w}-LINEAGE-V1',{'max_width':w},old['gene_digest'],f'DNF_WIDTH_DEFICIT_REQUIRED_{w}')
            mutations.append('LOGIC')
        if parent_score['THINKING']<1:
            old=genes['THINKING'];obj=list(old['expression'].get('objectives',[]));need=curr['thinking_required_objective']
            if need not in obj:obj=[need]+obj
            genes['THINKING']=cls._gene('THINKING',f'GENE-THINKING-{need.upper()}-AWARE-LINEAGE-V1',{'objectives':obj},old['gene_digest'],f'PLANNER_{need.upper()}_TIE_DEFICIT')
            mutations.append('THINKING')
        if parent_score['INTELLIGENCE']<1:
            old=genes['INTELLIGENCE'];w=curr['intelligence_width']
            genes['INTELLIGENCE']=cls._gene('INTELLIGENCE',f'GENE-INTELLIGENCE-TRIGGER-W{w}-LINEAGE-V1',{'max_trigger_width':w},old['gene_digest'],f'TRIGGER_WIDTH_DEFICIT_REQUIRED_{w}')
            mutations.append('INTELLIGENCE')
        if parent_score['CODE']<1:
            old=genes['CODE'];d=curr['code_degree']
            genes['CODE']=cls._gene('CODE',f'GENE-CODE-POLY-D{d}-LINEAGE-V1',{'max_degree':d},old['gene_digest'],f'POLYNOMIAL_DEGREE_DEFICIT_REQUIRED_{d}')
            mutations.append('CODE')
        child={
          'schema':'yado.g2.evolutionary_multigeneration.genome.v1',
          'shadow_generation':'S'+str(int(parent['shadow_generation'][1:])+1),
          'lineage_parent_genome_digest':parent['genome_digest'],
          'parent_canonical_head_digest':parent['parent_canonical_head_digest'],
          'source_shadow_child_digest':parent.get('source_shadow_child_digest'),
          'chromosomes':genes,
          'fitness_history':copy.deepcopy(parent.get('fitness_history',[])),
          'mutation_count':len(mutations),'mutated_chromosomes':mutations,
          'promotion_state':'SHADOW_ONLY',
        }
        child['genome_digest']=digest(child);return child

    @classmethod
    def cumulative_regression(cls,genome,curricula):
        rows={}
        for c in curricula:
            s=cls.evaluate(genome,c);rows[c['id']]=s
        return rows,all(all(v>=1.0 for v in s.values()) for s in rows.values())

    def run(self):
        seed,seed_evolution=self.seed()
        base_curr=self.curriculum(1)
        base_score=self.evaluate(seed,base_curr)
        base_pass=all(v>=1.0 for v in base_score.values())
        lineage=[{'generation':'S1','genome':seed,'seed_source':seed_evolution['child']['genome_digest'],'selection':'SEED_FROM_CANONICAL_CONTROLLER' if base_pass else 'WITHHOLD_SEED','baseline_fitness':base_score}]
        parent=seed;prior=[base_curr] if base_pass else []
        for idx in (2,3):
            curr=self.curriculum(idx)
            pscore=self.evaluate(parent,curr)
            child=self.mutate_from_deficits(parent,curr,pscore)
            cscore=self.evaluate(child,curr)
            regression_rows,reg_ok=self.cumulative_regression(child,prior+[curr])
            pmean=sum(pscore.values())/4;cmean=sum(cscore.values())/4
            selected='CHILD' if cmean>pmean and min(cscore.values())>=1.0 and reg_ok else 'PARENT'
            event={
              'generation':'S'+str(idx),'curriculum_id':curr['id'],
              'parent_genome_digest':parent['genome_digest'],'child_genome_digest':child['genome_digest'],
              'parent_fitness':pscore,'child_fitness':cscore,'fitness_gain':cmean-pmean,
              'cumulative_regression':regression_rows,'cumulative_regression_pass':reg_ok,
              'mutation_count':child['mutation_count'],'mutated_chromosomes':child['mutated_chromosomes'],
              'selection':selected,'promotion_authorized':False,
            }
            event['event_digest']=digest(event)
            child['fitness_history']=copy.deepcopy(parent.get('fitness_history',[]))+[event['event_digest']]
            child['genome_digest']=digest({k:v for k,v in child.items() if k!='genome_digest'})
            event['child_genome_digest']=child['genome_digest'];event['event_digest']=digest({k:v for k,v in event.items() if k!='event_digest'})
            lineage.append({'generation':'S'+str(idx),'genome':child,'event':event,'selection':selected})
            if selected!='CHILD':break
            parent=child;prior.append(curr)
        success=base_pass and len(lineage)==3 and all(x.get('selection') in {'SEED_FROM_CANONICAL_CONTROLLER','CHILD'} for x in lineage)
        report={
          'schema':'yado.g2.evolutionary_multigeneration_lineage.v1',
          'status':'PASS_SHADOW_G2_MULTIGENERATION_EVOLUTION_V1' if success else 'WITHHOLD_G2_MULTIGENERATION_EVOLUTION_V1',
          'controller_id':self.COMPONENT_ID,
          'canonical_head_digest':self.core.head['canonical_head_digest'],
          'formal_generation':self.core.head.get('generation_id'),
          'frontier':self.core.head.get('current_frontier'),
          'lineage':lineage,
          'final_shadow_genome_digest':parent['genome_digest'],
          'shadow_generation_count':len(lineage),
          'automatic_canonical_promotion':False,
          'canonical_mutation':False,'architecture_mutation':False,'generation_transition':False,'g3_genesis_performed':False,
          'semantic_boundary':'S1/S2/S3 ARE INTERNAL SHADOW LINEAGE LABELS, NOT FORMAL YADO GENERATIONS. EACH WINNING CHILD BECOMES THE NEXT SHADOW PARENT ONLY AFTER POSITIVE FRESH FITNESS AND CUMULATIVE REGRESSION PASS.'
        }
        report['receipt_sha256']=digest(report);return report

def main():
    core=UnifiedYADOCoreV1(REPO)
    report=YADOEvolutionaryMultiGenerationLineageV1(core).run()
    out=REPO/'candidates/kernel-self-generated/g2-evolutionary-multigeneration-lineage-v1.json'
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
    summary={
      'status':report['status'],'shadow_generation_count':report['shadow_generation_count'],
      'final_shadow_genome_digest':report['final_shadow_genome_digest'],
      'events':[{
        'generation':x['generation'],
        'selection':x.get('selection'),
        'parent_fitness':x.get('event',{}).get('parent_fitness'),
        'child_fitness':x.get('event',{}).get('child_fitness'),
        'fitness_gain':x.get('event',{}).get('fitness_gain'),
        'cumulative_regression_pass':x.get('event',{}).get('cumulative_regression_pass'),
        'mutated_chromosomes':x.get('event',{}).get('mutated_chromosomes'),
      } for x in report['lineage']],
      'receipt_sha256':report['receipt_sha256'],
    }
    print(json.dumps(summary,indent=2,sort_keys=True))
    if report['status']!='PASS_SHADOW_G2_MULTIGENERATION_EVOLUTION_V1':raise SystemExit(2)

if __name__=='__main__':main()
