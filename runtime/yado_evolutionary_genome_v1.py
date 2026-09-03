from __future__ import annotations
from dataclasses import dataclass
from fractions import Fraction
from itertools import combinations,product
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
    def _fit_univariate(cls,examples):
        pts=[(Fraction(args[0]),Fraction(expected)) for args,expected in examples]
        for degree in range(cls.MAX_DEGREE+1):
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
    def synthesize(cls,source,function_name,examples):
        tree=ast.parse(source)
        fname=cls.PARENT.BASE._validate(tree)
        if fname!=function_name:raise ValueError('FUNCTION_NAME_MISMATCH')
        func=next(n for n in tree.body if isinstance(n,ast.FunctionDef))
        if len(func.args.args)!=1:return {'source':None,'reason':'UNIVARIATE_ONLY'}
        arg=func.args.args[0].arg
        model=cls._fit_univariate(examples)
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
        deficits={}

        logic_rows=[]
        for a,b,c in product((False,True),repeat=3):
            for _ in range(4):
                logic_rows.append({'input':{'a':a,'b':b,'c':c},'expected':'YES' if a and not b else 'NO'})
        try:
            BudgetAdaptiveCompositionalLogicV2.learn_symmetric_boolean(logic_rows)
            deficits['LOGIC']={'deficit':False}
        except Exception as e:
            deficits['LOGIC']={'deficit':True,'signature':type(e).__name__+':'+str(e),'suggestion':'SYNTHESIZE_BOOLEAN_DNF_GENE'}

        slow=ContingentStage('A_SLOW',1.0,.6,latency=9.0)
        fast=ContingentStage('Z_FAST',1.0,.6,latency=1.0)
        pp=WorkBudgetAdaptiveContingentPlannerV2.plan(.2,.8,2.0,[slow,fast])
        deficits['THINKING']={'deficit':pp.action!='Z_FAST','signature':'EQUAL_UTILITY_LATENCY_TIE' if pp.action!='Z_FAST' else None,'parent_action':pp.action,'suggestion':'MUTATE_STATE_KEY_WITH_LATENCY'}

        train=[]
        for a,b,c in product((False,True),repeat=3):
            for r in range(6):
                train.append({'input':{'a':a,'b':b,'c':c,'noise':r%2},'expected':'SPECIAL' if a and b and c else 'BASE'})
        pm=CoveragePrunedCompositionalSchemaRouterV3.fit(train,'BASE')
        pr=CoveragePrunedCompositionalSchemaRouterV3.route(pm,{'a':True,'b':True,'c':True,'noise':True})
        deficits['INTELLIGENCE']={'deficit':'SPECIAL' not in pr,'signature':'TRIGGER_WIDTH_2_CANNOT_EXPRESS_TRIPLE_CONJUNCTION','parent_route':pr,'suggestion':'INCREMENT_TRIGGER_WIDTH'}

        source='def f(x):\n    return x\n'
        train_code=[((x,),x*x+1) for x in (-3,-2,-1,0,1,2,3)]
        parent_repair=AmbiguityAwareProgramRepairV11.repair(source,'f',train_code,max_candidates=12000)
        hold=[((x,),x*x+1) for x in (4,5,-4,-5)]
        parent_hold=0.0
        if parent_repair.get('source'):
            parent_hold=sum(AmbiguityAwareProgramRepairV11.execute(parent_repair['source'],'f',args)==y for args,y in hold)/len(hold)
        deficits['CODE']={'deficit':parent_hold<1.0,'signature':'PARENT_REPAIR_FAILS_QUADRATIC_FRESH_TRANSFER','parent_holdout':parent_hold,'suggestion':'RECOMBINE_LOGIC_POLYNOMIAL_FIT_WITH_AST_RETURN_SYNTHESIS'}
        return deficits

    def mutate(self,deficits):
        genes={}
        if deficits['LOGIC']['deficit']:
            genes['LOGIC']=self._gene(LogicDNFGeneV1.GENE_ID,{'max_width':3},[self.parent['chromosomes']['LOGIC']['gene_id']],True,deficits['LOGIC']['signature'])
        else:genes['LOGIC']=copy.deepcopy(self.parent['chromosomes']['LOGIC'])
        if deficits['THINKING']['deficit']:
            genes['THINKING']=self._gene(LatencyAwarePlannerGeneV1.GENE_ID,{'latency_tiebreak':True},[self.parent['chromosomes']['THINKING']['gene_id']],False,deficits['THINKING']['signature'])
        else:genes['THINKING']=copy.deepcopy(self.parent['chromosomes']['THINKING'])
        if deficits['INTELLIGENCE']['deficit']:
            genes['INTELLIGENCE']=self._gene(TripleTriggerRouterGeneV1.GENE_ID,{'max_trigger_width':3},[self.parent['chromosomes']['INTELLIGENCE']['gene_id']],False,deficits['INTELLIGENCE']['signature'])
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

    @staticmethod
    def evaluate(parent,child):
        score={'parent':{},'child':{},'regression':{}}

        # LOGIC: asymmetric boolean rule; child must discover a bounded DNF gene.
        train=[]
        for a,b,c in product((False,True),repeat=3):
            for _ in range(5):train.append({'input':{'a':a,'b':b,'c':c},'expected':'YES' if a and not b else 'NO'})
        try:
            pm=BudgetAdaptiveCompositionalLogicV2.learn_symmetric_boolean(train)
            pacc=sum(BudgetAdaptiveCompositionalLogicV2.predict_symmetric_boolean(pm,{'a':a,'b':b,'c':c})==('YES' if a and not b else 'NO') for a,b,c in product((False,True),repeat=3))/8
        except Exception:pacc=0.0
        cm=LogicDNFGeneV1.fit(train,max_width=3)
        fresh=[{'a':a,'b':b,'c':c,'irrelevant':i%2==0} for i,(a,b,c) in enumerate(list(product((False,True),repeat=3))*8)]
        cacc=sum(LogicDNFGeneV1.predict(cm,x)==('YES' if x['a'] and not x['b'] else 'NO') for x in fresh)/len(fresh)
        score['parent']['LOGIC']=pacc;score['child']['LOGIC']=cacc

        # THINKING: equal utility, lower latency is strictly preferable.
        slow=ContingentStage('A_SLOW',1.0,.6,latency=9.0);fast=ContingentStage('Z_FAST',1.0,.6,latency=1.0)
        pp=WorkBudgetAdaptiveContingentPlannerV2.plan(.2,.8,2.0,[slow,fast])
        cp=LatencyAwarePlannerGeneV1.plan(.2,.8,2.0,[slow,fast])
        score['parent']['THINKING']=1.0 if pp.action=='Z_FAST' else 0.0
        score['child']['THINKING']=1.0 if cp.action=='Z_FAST' else 0.0
        # baseline where cost determines winner must remain identical.
        b1=ContingentStage('CHEAP',1.0,.7,latency=5);b2=ContingentStage('EXPENSIVE',2.0,.7,latency=1)
        score['regression']['THINKING']=WorkBudgetAdaptiveContingentPlannerV2.plan(.1,.7,3,[b1,b2]).action==LatencyAwarePlannerGeneV1.plan(.1,.7,3,[b1,b2]).action

        # INTELLIGENCE: triple conjunction cannot be represented by width2.
        cases=[]
        for a,b,c in product((False,True),repeat=3):
            for n in range(8):cases.append({'input':{'a':a,'b':b,'c':c,'noise':n%2},'expected':'SPECIAL' if a and b and c else 'BASE'})
        pm=CoveragePrunedCompositionalSchemaRouterV3.fit(cases,'BASE')
        cm=TripleTriggerRouterGeneV1.fit(cases,'BASE')
        p=CoveragePrunedCompositionalSchemaRouterV3.route(pm,{'a':True,'b':True,'c':True,'noise':False})
        q=TripleTriggerRouterGeneV1.route(cm,{'a':True,'b':True,'c':True,'noise':True})
        score['parent']['INTELLIGENCE']=1.0 if 'SPECIAL' in p else 0.0
        score['child']['INTELLIGENCE']=1.0 if 'SPECIAL' in q else 0.0
        simple=[]
        for a,b in product((False,True),repeat=2):
            for n in range(8):simple.append({'input':{'a':a,'b':b,'noise':n%2},'expected':'SPECIAL' if a and b else 'BASE'})
        psm=CoveragePrunedCompositionalSchemaRouterV3.fit(simple,'BASE')
        csm=TripleTriggerRouterGeneV1.fit(simple,'BASE')
        score['regression']['INTELLIGENCE']=all(CoveragePrunedCompositionalSchemaRouterV3.route(psm,x)==TripleTriggerRouterGeneV1.route(csm,x) for x in [{'a':a,'b':b,'noise':n%2} for a,b in product((False,True),repeat=2) for n in range(4)])

        # CODE: parent may overfit training; novel gene must transfer quadratically.
        src='def f(x):\n    return x\n'
        tr=[((x,),x*x+1) for x in (-3,-2,-1,0,1,2,3)]
        hold=[((x,),x*x+1) for x in (4,5,6,-4,-5,-6)]
        pr=AmbiguityAwareProgramRepairV11.repair(src,'f',tr,max_candidates=12000)
        pacc=0.0
        if pr.get('source'):
            pacc=sum(AmbiguityAwareProgramRepairV11.execute(pr['source'],'f',args)==y for args,y in hold)/len(hold)
        cr=PolynomialReturnRepairGeneV1.synthesize(src,'f',tr)
        cacc=0.0
        if cr.get('source'):
            cacc=sum(AmbiguityAwareProgramRepairV11.execute(cr['source'],'f',args)==y for args,y in hold)/len(hold)
        score['parent']['CODE']=pacc;score['child']['CODE']=cacc
        # baseline offset repair remains handled by inherited V11.
        baseline=[((x,),x+2) for x in range(5)]
        br=AmbiguityAwareProgramRepairV11.repair('def g(x):\n    return x + 1\n','g',baseline,max_candidates=4000)
        score['regression']['CODE']=bool(br.get('source')) and all(AmbiguityAwareProgramRepairV11.execute(br['source'],'g',args)==y for args,y in baseline)

        # LOGIC regression: canonical symmetric problem remains solved by inherited parent path.
        sym=[]
        for a,b in product((False,True),repeat=2):
            for _ in range(4):sym.append({'input':{'a':a,'b':b},'expected':'EVEN' if a==b else 'ODD'})
        sm=BudgetAdaptiveCompositionalLogicV2.learn_symmetric_boolean(sym)
        score['regression']['LOGIC']=all(BudgetAdaptiveCompositionalLogicV2.predict_symmetric_boolean(sm,{'a':a,'b':b})==('EVEN' if a==b else 'ODD') for a,b in product((False,True),repeat=2))

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
