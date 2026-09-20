from __future__ import annotations
from dataclasses import dataclass
from fractions import Fraction
from itertools import combinations,product
from collections import defaultdict
import ast,copy,hashlib,json

from yado_budget_adaptive_compositional_logic_v2 import BudgetAdaptiveCompositionalLogicV2
from yado_work_budget_adaptive_contingent_planner_v2 import WorkBudgetAdaptiveContingentPlannerV2,ContingentStage
from yado_coverage_pruned_compositional_schema_router_v3 import CoveragePrunedCompositionalSchemaRouterV3
from yado_ambiguity_aware_program_repair_v11 import AmbiguityAwareProgramRepairV11

def _canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def _digest(o):return hashlib.sha256(_canon(o).encode()).hexdigest()

class LogicDNFGeneV1:
    GENE_ID='GENE-LOGIC-BOOLEAN-DNF-V1'
    MAX_FIELDS=8
    MAX_WIDTH=3
    MAX_RULES=32

    @classmethod
    def fit(cls,rows,max_width=None):
        if not rows:raise ValueError('EMPTY_ROWS')
        fields=sorted(rows[0]['input'])
        if len(fields)>cls.MAX_FIELDS:raise ValueError('FIELD_BUDGET')
        outputs=sorted({str(r['expected']) for r in rows})
        if len(outputs)!=2:raise ValueError('BINARY_OUTPUT_REQUIRED')
        for r in rows:
            if set(r['input'])!=set(fields):raise ValueError('SCHEMA_DRIFT')
            if any(not isinstance(r['input'][f],bool) for f in fields):raise ValueError('BOOLEAN_INPUT_REQUIRED')
        counts={o:sum(str(r['expected'])==o for r in rows) for o in outputs}
        default=sorted(outputs,key=lambda o:(-counts[o],o))[0]
        target=[o for o in outputs if o!=default][0]
        positives={i for i,r in enumerate(rows) if str(r['expected'])==target}
        width=min(int(max_width or cls.MAX_WIDTH),cls.MAX_WIDTH)
        candidates=[]
        atoms=[(f,v) for f in fields for v in (False,True)]
        for w in range(1,width+1):
            for combo in combinations(atoms,w):
                if len({a[0] for a in combo})!=w:continue
                covered={i for i,r in enumerate(rows) if all(r['input'][f] is v for f,v in combo)}
                if not covered or not (covered <= positives):continue
                candidates.append((combo,covered))
        uncovered=set(positives);rules=[]
        while uncovered and len(rules)<cls.MAX_RULES:
            scored=[]
            for combo,covered in candidates:
                gain=len(covered & uncovered)
                if gain:scored.append((-gain,len(combo),str(combo),combo,covered))
            if not scored:break
            scored.sort();_,_,_,combo,covered=scored[0]
            rules.append([{'field':f,'value':v} for f,v in combo]);uncovered-=covered
        if uncovered:return {'kind':'WITHHOLD','reason':'DNF_COVERAGE_GAP','fields':fields,'rules':[],'target':target,'default':default}
        return {'kind':'BOOLEAN_DNF_GENE_V1','fields':fields,'rules':rules,'target':target,'default':default}

    @staticmethod
    def predict(model,x):
        if model.get('kind')=='WITHHOLD':raise ValueError(model.get('reason','DNF_WITHHOLD'))
        for rule in model['rules']:
            if all(x.get(a['field']) is a['value'] for a in rule):return model['target']
        return model['default']

class LatencyAwarePlannerGeneV1(WorkBudgetAdaptiveContingentPlannerV2):
    GENE_ID='GENE-THINKING-LATENCY-AWARE-PLANNER-V1'
    @classmethod
    def _state_key(cls,seq,cost,conf,target):
        reaches=conf>=target
        latency=sum(max(0.0,float(x.latency)) for x in seq)
        ids=tuple(x.stage_id for x in seq)
        return (0,cost,latency,len(seq),-conf,ids) if reaches else (1,-conf,cost,latency,len(seq),ids)

class TripleTriggerRouterGeneV1(CoveragePrunedCompositionalSchemaRouterV3):
    GENE_ID='GENE-INTELLIGENCE-TRIPLE-TRIGGER-ROUTER-V1'
    MAX_TRIGGER_WIDTH=3

    @classmethod
    def fit(cls,cases,fallback_output,max_trigger_width=None):
        if not cases:raise ValueError('EMPTY_CASES')
        fields=sorted(set().union(*(set(z['input']) for z in cases)))
        if len(cases)*max(1,len(fields))>cls.MAX_FIELD_CELLS:
            return {'kind':'WITHHOLD','reason':'FIELD_WORK_BUDGET','fields':[],'outputs':[],'fallback_output':fallback_output,'triggers':{}}
        outputs=sorted(set().union(*(cls._outputs(z['expected']) for z in cases)))
        if fallback_output not in outputs:outputs=[fallback_output]+outputs
        outputs=sorted(set(outputs))
        if len(outputs)>cls.MAX_OUTPUTS:
            return {'kind':'WITHHOLD','reason':'OUTPUT_BUDGET','fields':fields,'outputs':[],'fallback_output':fallback_output,'triggers':{}}
        atoms=[]
        for f in fields:
            vals=[]
            for z in cases:
                v=z['input'].get(f)
                if isinstance(v,(bool,str,int,float)) and v not in vals:vals.append(v)
            if 1<len(vals)<=8:
                for v in vals:atoms.append((f,v))
        width=min(cls.MAX_TRIGGER_WIDTH,int(max_trigger_width or cls.MAX_TRIGGER_WIDTH))
        combos=[]
        for w in range(1,width+1):
            for combo in combinations(atoms,w):
                if len({a[0] for a in combo})==w:combos.append(combo)
                if len(combos)>cls.MAX_TRIGGER_CANDIDATES:
                    return {'kind':'WITHHOLD','reason':'TRIGGER_CANDIDATE_BUDGET','fields':fields,'outputs':outputs,'fallback_output':fallback_output,'triggers':{}}
        candidates=defaultdict(list)
        for combo in combos:
            covered={i for i,z in enumerate(cases) if all(a[0] in z['input'] and z['input'][a[0]]==a[1] for a in combo)}
            if len(covered)<cls.MIN_TRIGGER_SUPPORT:continue
            for out in outputs:
                if out==fallback_output:continue
                positives={i for i,z in enumerate(cases) if out in cls._outputs(z['expected'])}
                precision=len(covered & positives)/len(covered)
                if precision>=cls.MIN_TRIGGER_PRECISION:
                    candidates[out].append({
                      'atoms':[{'field':a[0],'value':a[1]} for a in combo],
                      'support':len(covered),'precision':precision,'covered_positive':covered & positives
                    })
        clean={}
        for out in outputs:
            if out==fallback_output:continue
            positives={i for i,z in enumerate(cases) if out in cls._outputs(z['expected'])}
            uncovered=set(positives);chosen=[]
            xs=sorted(candidates.get(out,[]),key=lambda r:(len(r['atoms']),-r['precision'],-r['support'],str(r['atoms'])))
            for r in xs:
                gain=len(r['covered_positive'] & uncovered)
                if gain<=0:continue
                chosen.append({'atoms':r['atoms'],'support':r['support'],'precision':r['precision'],'positive_gain':gain})
                uncovered-=r['covered_positive']
                if not uncovered or len(chosen)>=cls.MAX_TRIGGERS_PER_OUTPUT:break
            clean[out]=chosen
        return {
          'kind':'COVERAGE_PRUNED_COMPOSITIONAL_TRIGGER_ROUTER_GENE_V1',
          'fields':fields,'outputs':outputs,'fallback_output':fallback_output,'triggers':clean,
          'candidate_count':len(combos),'max_trigger_width':width
        }

class PolynomialReturnRepairGeneV1:
    GENE_ID='GENE-CODE-POLYNOMIAL-RETURN-SYNTHESIS-V1'
    MAX_DEGREE=3
    PARENT=AmbiguityAwareProgramRepairV11

    @staticmethod
    def _expr_from_model(model,arg_name):
        terms=[]
        for coeff,(i,j) in zip(model['coeff'],model['basis']):
            if j!=0 or coeff==0:continue
            if coeff.denominator!=1:raise ValueError('NON_INTEGER_COEFFICIENT')
            c=int(coeff)
            term=ast.Constant(1) if i==0 else ast.Name(id=arg_name,ctx=ast.Load())
            for _ in range(max(0,i-1)):
                term=ast.BinOp(left=term,op=ast.Mult(),right=ast.Name(id=arg_name,ctx=ast.Load()))
            if c!=1:
                term=ast.BinOp(left=ast.Constant(c),op=ast.Mult(),right=term)
            terms.append(term)
        if not terms:return ast.Constant(0)
        out=terms[0]
        for t in terms[1:]:out=ast.BinOp(left=out,op=ast.Add(),right=t)
        return out

    @classmethod
    def _fit_univariate(cls,examples,max_degree=None):
        pts=[(Fraction(args[0]),Fraction(expected)) for args,expected in examples]
        limit=cls.MAX_DEGREE if max_degree is None else min(cls.MAX_DEGREE,int(max_degree))
        for degree in range(limit+1):
            n=degree+1
            uniq=[]
            for x,y in pts:
                if all(x!=a for a,_ in uniq):uniq.append((x,y))
            if len(uniq)<n:continue
            A=[]
            for x,y in uniq[:n]:
                A.append([x**p for p in range(n)]+[y])
            for col in range(n):
                pivot=next((i for i in range(col,n) if A[i][col]!=0),None)
                if pivot is None:break
                A[col],A[pivot]=A[pivot],A[col]
                q=A[col][col];A[col]=[v/q for v in A[col]]
                for i in range(n):
                    if i==col:continue
                    q=A[i][col]
                    if q!=0:A[i]=[a-q*b for a,b in zip(A[i],A[col])]
            else:
                coeff=[A[i][-1] for i in range(n)]
                if all(sum(coeff[p]*(x**p) for p in range(n))==y for x,y in pts):
                    return {'kind':'EXACT_UNIVARIATE_POLYNOMIAL_GENE_V1','degree':degree,'coeff':coeff,'basis':[(p,0) for p in range(n)]}
        return {'kind':'WITHHOLD','reason':'NO_UNIVARIATE_POLYNOMIAL_WITHIN_GENE_BUDGET'}

    @classmethod
    def synthesize(cls,source,function_name,examples,max_degree=None):
        tree=ast.parse(source)
        fname=cls.PARENT.BASE._validate(tree)
        if fname!=function_name:raise ValueError('FUNCTION_NAME_MISMATCH')
        func=next(n for n in tree.body if isinstance(n,ast.FunctionDef))
        if len(func.args.args)!=1:return {'source':None,'reason':'UNIVARIATE_ONLY'}
        arg=func.args.args[0].arg
        model=cls._fit_univariate(examples,max_degree=max_degree)
        if model.get('kind')=='WITHHOLD':return {'source':None,'reason':model.get('reason'),'operator_gene':cls.GENE_ID}
        returns=[n for n in ast.walk(func) if isinstance(n,ast.Return) and n.value is not None]
        if len(returns)!=1:return {'source':None,'reason':'SINGLE_RETURN_REQUIRED','operator_gene':cls.GENE_ID}
        returns[0].value=cls._expr_from_model(model,arg)
        ast.fix_missing_locations(tree)
        cls.PARENT.BASE._validate(tree)
        out=ast.unparse(tree)+'\n'
        if not cls.PARENT._passes(out,function_name,examples):
            return {'source':None,'reason':'SYNTHESIZED_PROGRAM_FAILED_TRAIN','operator_gene':cls.GENE_ID}
        return {'source':out,'operator_gene':cls.GENE_ID,'model_kind':model['kind'],'degree':model['degree']}

class YADOEvolutionaryGenomeV1:
    COMPONENT_ID='CTRL-G2-EVOLUTIONARY-GENOME-V1'
    SCHEMA='yado.g2.evolutionary_genome.v1'

    def __init__(self,parent_snapshot,experience_sources=None):
        self.parent=copy.deepcopy(parent_snapshot)
        self.experience_sources=copy.deepcopy(experience_sources or [])

    @staticmethod
    def _gene(gene_id,expression,heritage,novel=False,mutation_reason=None):
        g={
          'gene_id':gene_id,'expression':expression,'heritage':heritage,
          'novel_gene':bool(novel),'mutation_reason':mutation_reason,
        }
        g['gene_digest']=_digest(g);return g

    @classmethod
    def parent_genome(cls,head_digest,component_digests,experience_digest=None):
        chromosomes={
          'LOGIC':cls._gene('ALG-G2-BUDGET-ADAPTIVE-COMPOSITIONAL-LOGIC-V2',{'mode':'CANONICAL_V2'},['G2'],False),
          'THINKING':cls._gene('ALG-G2-WORK-BUDGET-ADAPTIVE-CONTINGENT-PLANNER-V2',{'mode':'CANONICAL_V2'},['G2'],False),
          'INTELLIGENCE':cls._gene('ALG-G2-COVERAGE-PRUNED-COMPOSITIONAL-SCHEMA-ROUTER-V3',{'max_trigger_width':2},['G2'],False),
          'CODE':cls._gene('ALG-G2-AMBIGUITY-AWARE-PROGRAM-REPAIR-V11',{'mode':'CANONICAL_V11'},['G2'],False),
        }
        g={
          'schema':cls.SCHEMA,'genome_id':'G2-PARENT-GENOME-V1','generation':'G2_CANDIDATE_TRCG_V1',
          'parent_head_digest':head_digest,'component_digests':copy.deepcopy(component_digests),
          'chromosomes':chromosomes,'experience_digest':experience_digest,
          'promotion_state':'PARENT_CANONICAL_CAPABILITIES_SNAPSHOT',
        }
        g['genome_digest']=_digest(g);return g

    def observe_parent_deficits(self):
        expressed=self._express_genome(self.parent)
        scores,_,observations=self._measure_expressed_genome(expressed)
        return {
          'LOGIC':{
            'deficit':scores['LOGIC']<1.0,
            'signature':observations['logic_failure'] or ('INEXACT_ASYMMETRIC_BOOLEAN_TRANSFER' if scores['LOGIC']<1.0 else None),
            'suggestion':'SYNTHESIZE_BOOLEAN_DNF_GENE',
          },
          'THINKING':{
            'deficit':scores['THINKING']<1.0,
            'signature':'EQUAL_UTILITY_LATENCY_TIE' if scores['THINKING']<1.0 else None,
            'parent_action':observations['thinking_action'],
            'suggestion':'MUTATE_STATE_KEY_WITH_LATENCY',
          },
          'INTELLIGENCE':{
            'deficit':scores['INTELLIGENCE']<1.0,
            'signature':'ACTIVE_TRIGGER_CANNOT_EXPRESS_TRIPLE_CONJUNCTION' if scores['INTELLIGENCE']<1.0 else None,
            'parent_route':observations['intelligence_route'],
            'suggestion':'INCREMENT_TRIGGER_WIDTH',
          },
          'CODE':{
            'deficit':scores['CODE']<1.0,
            'signature':'PARENT_REPAIR_FAILS_QUADRATIC_FRESH_TRANSFER' if scores['CODE']<1.0 else None,
            'parent_holdout':scores['CODE'],
            'suggestion':'RECOMBINE_LOGIC_POLYNOMIAL_FIT_WITH_AST_RETURN_SYNTHESIS',
          },
        }

    def mutate(self,deficits):
        genes={}
        if deficits['LOGIC']['deficit']:
            genes['LOGIC']=self._gene(LogicDNFGeneV1.GENE_ID,{'max_width':3},[self.parent['chromosomes']['LOGIC']['gene_id']],True,deficits['LOGIC']['signature'])
        else:genes['LOGIC']=copy.deepcopy(self.parent['chromosomes']['LOGIC'])
        if deficits['THINKING']['deficit']:
            genes['THINKING']=self._gene(LatencyAwarePlannerGeneV1.GENE_ID,{'latency_tiebreak':True},[self.parent['chromosomes']['THINKING']['gene_id']],False,deficits['THINKING']['signature'])
        else:genes['THINKING']=copy.deepcopy(self.parent['chromosomes']['THINKING'])
        if deficits['INTELLIGENCE']['deficit']:
            genes['INTELLIGENCE']=self._gene(TripleTriggerRouterGeneV1.GENE_ID,{'max_trigger_width':3,'candidate_generator':'GENERAL_COMBINATIONS_UP_TO_WIDTH'},[self.parent['chromosomes']['INTELLIGENCE']['gene_id']],True,deficits['INTELLIGENCE']['signature'])
        else:genes['INTELLIGENCE']=copy.deepcopy(self.parent['chromosomes']['INTELLIGENCE'])
        if deficits['CODE']['deficit']:
            genes['CODE']=self._gene(PolynomialReturnRepairGeneV1.GENE_ID,{'max_degree':3},[
                self.parent['chromosomes']['CODE']['gene_id'],
                self.parent['chromosomes']['LOGIC']['gene_id'],
            ],True,deficits['CODE']['signature'])
        else:genes['CODE']=copy.deepcopy(self.parent['chromosomes']['CODE'])
        child={
          'schema':self.SCHEMA,'genome_id':'G2-CHILD-GENOME-SHADOW-V1',
          'generation':'G2_CANDIDATE_TRCG_V1','parent_genome_digest':self.parent['genome_digest'],
          'chromosomes':genes,'experience_sources':copy.deepcopy(self.experience_sources),
          'mutation_count':sum(genes[k]['gene_id']!=self.parent['chromosomes'][k]['gene_id'] for k in genes),
          'novel_gene_count':sum(bool(genes[k].get('novel_gene')) for k in genes),
          'promotion_state':'SHADOW_ONLY',
        }
        child['genome_digest']=_digest(child);return child

    @classmethod
    def _express_genome(cls,genome):
        """Resolve only implemented, integrity-bound chromosomes and settings."""
        organs={'LOGIC','THINKING','INTELLIGENCE','CODE'}
        if not isinstance(genome,dict) or genome.get('schema')!=cls.SCHEMA:
            raise ValueError('GENOME_FITNESS_SCHEMA')
        if genome.get('generation')!='G2_CANDIDATE_TRCG_V1':
            raise ValueError('GENOME_FITNESS_GENERATION')
        if genome.get('genome_digest')!=_digest({k:v for k,v in genome.items() if k!='genome_digest'}):
            raise ValueError('GENOME_FITNESS_DIGEST_MISMATCH')
        genes=genome.get('chromosomes')
        if not isinstance(genes,dict) or set(genes)!=organs:
            raise ValueError('GENOME_FITNESS_UNSUPPORTED_DIMENSIONS')
        registry={
          'LOGIC':{BudgetAdaptiveCompositionalLogicV2.COMPONENT_ID:BudgetAdaptiveCompositionalLogicV2,
                   LogicDNFGeneV1.GENE_ID:LogicDNFGeneV1},
          'THINKING':{WorkBudgetAdaptiveContingentPlannerV2.COMPONENT_ID:WorkBudgetAdaptiveContingentPlannerV2,
                      LatencyAwarePlannerGeneV1.GENE_ID:LatencyAwarePlannerGeneV1},
          'INTELLIGENCE':{CoveragePrunedCompositionalSchemaRouterV3.COMPONENT_ID:CoveragePrunedCompositionalSchemaRouterV3,
                          TripleTriggerRouterGeneV1.GENE_ID:TripleTriggerRouterGeneV1},
          'CODE':{AmbiguityAwareProgramRepairV11.COMPONENT_ID:AmbiguityAwareProgramRepairV11,
                  PolynomialReturnRepairGeneV1.GENE_ID:PolynomialReturnRepairGeneV1},
        }
        expressed={}
        for organ in sorted(organs):
            gene=genes[organ]
            if not isinstance(gene,dict) or not isinstance(gene.get('gene_id'),str):
                raise ValueError('GENOME_FITNESS_GENE_SCHEMA:'+organ)
            impl=registry[organ].get(gene['gene_id'])
            if impl is None:raise ValueError('GENOME_FITNESS_UNIMPLEMENTED_GENE:'+organ)
            if gene.get('gene_digest')!=_digest({k:v for k,v in gene.items() if k!='gene_digest'}):
                raise ValueError('GENOME_FITNESS_GENE_DIGEST_MISMATCH:'+organ)
            expr=gene.get('expression')
            if not isinstance(expr,dict):raise ValueError('GENOME_FITNESS_EXPRESSION:'+organ)
            if impl in (BudgetAdaptiveCompositionalLogicV2,WorkBudgetAdaptiveContingentPlannerV2):
                valid=expr=={'mode':'CANONICAL_V2'}
            elif impl is AmbiguityAwareProgramRepairV11:
                valid=expr=={'mode':'CANONICAL_V11'}
            elif impl is LatencyAwarePlannerGeneV1:
                valid=set(expr)=={'latency_tiebreak'} and expr['latency_tiebreak'] is True
            else:
                field,lower,upper={
                  LogicDNFGeneV1:('max_width',1,LogicDNFGeneV1.MAX_WIDTH),
                  CoveragePrunedCompositionalSchemaRouterV3:('max_trigger_width',1,CoveragePrunedCompositionalSchemaRouterV3.MAX_TRIGGER_WIDTH),
                  TripleTriggerRouterGeneV1:('max_trigger_width',1,TripleTriggerRouterGeneV1.MAX_TRIGGER_WIDTH),
                  PolynomialReturnRepairGeneV1:('max_degree',0,PolynomialReturnRepairGeneV1.MAX_DEGREE),
                }[impl]
                fields={field}
                if impl is TripleTriggerRouterGeneV1:fields.add('candidate_generator')
                valid=set(expr)==fields and type(expr.get(field)) is int and lower<=expr[field]<=upper
                if impl is TripleTriggerRouterGeneV1:
                    valid=valid and expr.get('candidate_generator')=='GENERAL_COMBINATIONS_UP_TO_WIDTH'
            if not valid:raise ValueError('GENOME_FITNESS_UNSUPPORTED_EXPRESSION:'+organ)
            expressed[organ]=(impl,copy.deepcopy(expr))
        return expressed

    @staticmethod
    def _measure_expressed_genome(expressed):
        """Apply the same bounded challenge and regression cases to either genome."""
        scores={};regression={};observations={}
        logic,logic_expr=expressed['LOGIC']
        def logic_accuracy(rows,holdout):
            try:
                if logic is BudgetAdaptiveCompositionalLogicV2:
                    model=logic.learn_symmetric_boolean(rows)
                    predict=logic.predict_symmetric_boolean
                else:
                    model=logic.fit(rows,max_width=logic_expr['max_width'])
                    predict=logic.predict
                return sum(predict(model,row['input'])==row['expected'] for row in holdout)/len(holdout),None
            except ValueError as exc:
                return 0.0,type(exc).__name__+':'+str(exc)
        train=[]
        for a,b,c in product((False,True),repeat=3):
            for _ in range(5):train.append({'input':{'a':a,'b':b,'c':c},'expected':'YES' if a and not b else 'NO'})
        hold=[{'input':{'a':a,'b':b,'c':c,'irrelevant':i%2==0},'expected':'YES' if a and not b else 'NO'}
              for i,(a,b,c) in enumerate(list(product((False,True),repeat=3))*8)]
        scores['LOGIC'],observations['logic_failure']=logic_accuracy(train,hold)
        sym=[{'input':{'a':a,'b':b},'expected':'EVEN' if a==b else 'ODD'}
             for a,b in product((False,True),repeat=2) for _ in range(4)]
        regression['LOGIC']=logic_accuracy(sym,sym)[0]==1.0

        thinking,_=expressed['THINKING']
        slow=ContingentStage('A_SLOW',1.0,.6,latency=9.0);fast=ContingentStage('Z_FAST',1.0,.6,latency=1.0)
        action=thinking.plan(.2,.8,2.0,[slow,fast]).action
        observations['thinking_action']=action
        scores['THINKING']=float(action=='Z_FAST')
        b1=ContingentStage('CHEAP',1.0,.7,latency=5);b2=ContingentStage('EXPENSIVE',2.0,.7,latency=1)
        regression['THINKING']=thinking.plan(.1,.7,3,[b1,b2]).action=='CHEAP'

        intelligence,intel_expr=expressed['INTELLIGENCE']
        cases=[]
        for a,b,c in product((False,True),repeat=3):
            for n in range(8):cases.append({'input':{'a':a,'b':b,'c':c,'noise':n%2},'expected':'SPECIAL' if a and b and c else 'BASE'})
        model=intelligence.fit(cases,'BASE',max_trigger_width=intel_expr['max_trigger_width'])
        route=intelligence.route(model,{'a':True,'b':True,'c':True,'noise':True})
        observations['intelligence_route']=route
        scores['INTELLIGENCE']=float('SPECIAL' in route)
        simple=[{'input':{'a':a,'b':b,'noise':n%2},'expected':'SPECIAL' if a and b else 'BASE'}
                for a,b in product((False,True),repeat=2) for n in range(8)]
        simple_model=intelligence.fit(simple,'BASE',max_trigger_width=intel_expr['max_trigger_width'])
        regression['INTELLIGENCE']=all(
            intelligence.route(simple_model,{'a':a,'b':b,'noise':n%2})==('SPECIAL' if a and b else 'BASE',)
            for a,b in product((False,True),repeat=2) for n in range(4))

        code,code_expr=expressed['CODE']
        def code_accuracy(source,function_name,train,holdout,budget):
            if code is AmbiguityAwareProgramRepairV11:
                candidate=code.repair(source,function_name,train,max_candidates=budget)
            else:
                candidate=code.synthesize(source,function_name,train,max_degree=code_expr['max_degree'])
            if not candidate.get('source'):return 0.0
            return sum(AmbiguityAwareProgramRepairV11.execute(candidate['source'],function_name,args)==y
                       for args,y in holdout)/len(holdout)
        tr=[((x,),x*x+1) for x in (-3,-2,-1,0,1,2,3)]
        hold=[((x,),x*x+1) for x in (4,5,6,-4,-5,-6)]
        scores['CODE']=code_accuracy('def f(x):\n    return x\n','f',tr,hold,12000)
        baseline=[((x,),x+2) for x in range(5)]
        regression['CODE']=code_accuracy('def g(x):\n    return x + 1\n','g',baseline,baseline,4000)==1.0
        return scores,regression,observations

    @classmethod
    def evaluate(cls,parent,child):
        # Unknown additions require an implemented evaluator, never a score
        # based on metadata alone. Validate both before executing either one.
        parent_impl=cls._express_genome(parent)
        child_impl=cls._express_genome(child)
        parent_score,parent_regression,_=cls._measure_expressed_genome(parent_impl)
        child_score,child_regression,_=cls._measure_expressed_genome(child_impl)
        score={'parent':parent_score,'child':child_score,
               'regression':{k:parent_regression[k] and child_regression[k] for k in parent_regression},
               'evaluated_genomes':{'parent':parent['genome_digest'],'child':child['genome_digest']}}
        score['parent_mean']=sum(score['parent'].values())/4
        score['child_mean']=sum(score['child'].values())/4
        score['fitness_gain']=score['child_mean']-score['parent_mean']
        score['all_regressions_pass']=all(score['regression'].values())
        return score

    def evolve_once(self):
        deficits=self.observe_parent_deficits()
        child=self.mutate(deficits)
        fitness=self.evaluate(self.parent,child)
        selected='CHILD' if fitness['fitness_gain']>0 and fitness['all_regressions_pass'] and min(fitness['child'].values())>=1.0 else 'PARENT'
        result={
          'schema':'yado.g2.evolutionary_genome.evolution_run.v1',
          'controller_id':self.COMPONENT_ID,
          'parent':self.parent,'deficits':deficits,'child':child,'fitness':fitness,
          'selection':selected,
          'promotion_authorized':False,
          'selection_semantics':'CHILD MAY WIN SHADOW FITNESS BUT REQUIRES SEPARATE CANONICAL ADMISSION.',
          'architecture_mutation':False,'generation_transition':False,'g3_genesis_performed':False,
        }
        result['run_digest']=_digest(result);return result

    @classmethod
    def component(cls):
        x={
          'schema':'yado.g2.evolutionary_genome.controller.v1','component_id':cls.COMPONENT_ID,
          'chromosomes':['LOGIC','THINKING','INTELLIGENCE','CODE'],
          'operations':['OBSERVE_DEFICIT','MUTATE','RECOMBINE','EXPRESS','FITNESS','SELECT'],
          'novel_gene_synthesis':True,'automatic_canonical_promotion':False,
          'fresh_gate_required_for_promotion':True,'rollback_parent_preserved':True,
          'architecture_mutation':False,'canonical_active':False,
          'semantic_boundary':'BOUNDED SAME-G2 EVOLUTIONARY SUBSTRATE. CHILD GENOMES ARE SHADOW UNTIL SEPARATE CANONICAL ADMISSION.'
        }
        x['component_digest']=_digest(x);return x

__all__=[
 'YADOEvolutionaryGenomeV1','LogicDNFGeneV1','LatencyAwarePlannerGeneV1',
 'TripleTriggerRouterGeneV1','PolynomialReturnRepairGeneV1'
]
