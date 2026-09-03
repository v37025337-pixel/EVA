from __future__ import annotations
from pathlib import Path
import copy,hashlib,json

from yado_g2_autonomous_gene_portfolio_controller_v1 import YADOAutonomousGenePortfolioControllerV1
from yado_generic_relational_meta_language_v1 import GenericRelationalMetaLanguageV1
from yado_generic_event_state_meta_language_v1 import GenericEventStateMetaLanguageV1
from yado_generic_weighted_state_meta_language_v1 import GenericWeightedStateMetaLanguageV1

def _canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def _digest(o): return hashlib.sha256(_canon(o).encode()).hexdigest()

class YADOAdaptiveEvolutionControllerV1:
    COMPONENT_ID='CTRL-G2-ADAPTIVE-EVOLUTION-V1'
    WEIGHTED_CONTRACT='WEIGHTED_RELATION_SOURCE_TO_COST_MAP'

    def __init__(self,repo_root:Path):
        self.repo_root=Path(repo_root)
        self.portfolio_controller=YADOAutonomousGenePortfolioControllerV1(self.repo_root)
        self.events=[]

    def build_existing_portfolio(self,selection_tasks):
        p=self.portfolio_controller.select_portfolio(selection_tasks)
        self.events.append({
          'event':'EXISTING_PORTFOLIO_BUILT',
          'selected_gene_count':p.get('selected_gene_count',0),
          'selected_gene_digests':sorted(x['gene']['gene_digest'] for x in p.get('selected_genes',[])),
        })
        return p

    @staticmethod
    def _score_gene(gene,task_group):
        comp=gene.get('meta_language_component')
        if comp in (
            GenericRelationalMetaLanguageV1.COMPONENT_ID,
            GenericEventStateMetaLanguageV1.COMPONENT_ID,
        ):
            expected_contract=YADOAutonomousGenePortfolioControllerV1._contract_for_component(comp)
            if task_group.get('input_contract')!=expected_contract:
                return None
            item={'schema':'tmp','selected_genes':[{'gene':gene}]}
            return YADOAutonomousGenePortfolioControllerV1.evaluate_portfolio(item,task_group)['best_score']
        if comp==GenericWeightedStateMetaLanguageV1.COMPONENT_ID and task_group.get('input_contract')==YADOAdaptiveEvolutionControllerV1.WEIGHTED_CONTRACT:
            cases=task_group.get('cases',[])
            if not cases: return 0.0
            ok=0
            for c in cases:
                try: got=GenericWeightedStateMetaLanguageV1.execute(gene.get('operator_program',{}),c['relation'],c['start'])
                except Exception: got=None
                ok += (got==c['expected'])
            return ok/len(cases)
        return None

    def attempt_reuse(self,portfolio,task_group):
        rows=[]
        for item in portfolio.get('selected_genes',[]):
            gene=item.get('gene',{})
            s=self._score_gene(gene,task_group)
            if s is not None:
                rows.append({'gene_id':gene.get('gene_id'),'gene_digest':gene.get('gene_digest'),'score':s})
        rows.sort(key=lambda r:(-r['score'],r['gene_digest'] or ''))
        best=rows[0]['score'] if rows else 0.0
        verdict='REUSE_SUFFICIENT' if best==1.0 else 'PORTFOLIO_INSUFFICIENT'
        event={'event':'REUSE_ATTEMPT','task_id':task_group.get('task_id'),'compatible_gene_count':len(rows),'best_score':best,'verdict':verdict}
        self.events.append(event)
        return event|{'rows':rows}

    def invent_weighted_gene(self,train_examples,stall_signal,parent_gene_ids):
        if not isinstance(stall_signal,dict) or stall_signal.get('mechanism_change_required') is not True:
            raise RuntimeError('TEMPORAL_STALL_SIGNAL_REQUIRED')
        if int(stall_signal.get('no_progress_ticks',0))<20:
            raise RuntimeError('STALL_THRESHOLD_NOT_REACHED')
        p=GenericWeightedStateMetaLanguageV1.synthesize(train_examples)
        if float(p.get('train_accuracy',0.0))<1.0:
            self.events.append({'event':'INVENTION_WITHHELD','reason':p.get('reason')})
            return {'status':'WITHHOLD','program':p}
        gid=p['synthesized_operator_id']
        if gid in set(parent_gene_ids):
            raise RuntimeError('SYNTHESIZED_GENE_COLLIDES_WITH_PARENT')
        gene={
          'schema':'yado.g2.self_synthesized_weighted_state_gene.v1',
          'gene_id':gid,'novel_gene':True,
          'gene_scope':['LOGIC','THINKING','INTELLIGENCE','CODE'],
          'heritage':sorted(set(str(x) for x in parent_gene_ids)),
          'trigger':{
            'source':'TEMPORAL_STALL_SIGNAL',
            'tick_id':stall_signal.get('tick_id'),
            'no_progress_ticks':stall_signal.get('no_progress_ticks'),
            'deficit_id':stall_signal.get('deficit_id'),
          },
          'meta_language_component':GenericWeightedStateMetaLanguageV1.COMPONENT_ID,
          'operator_program':p,
          'execution_mode':'BOUNDED_META_LANGUAGE_INTERPRETER',
          'promotion_state':'SHADOW_ONLY',
        }
        gene['gene_digest']=_digest(gene)
        self.events.append({'event':'NOVEL_GENE_INVENTED','gene_id':gid,'gene_digest':gene['gene_digest']})
        return {'status':'SELF_SYNTHESIZED_SHADOW_GENE','gene':gene}

    def expand_portfolio(self,portfolio,gene,selected_for_task):
        child=copy.deepcopy(portfolio)
        child.pop('portfolio_digest',None)
        if any(x['gene'].get('gene_digest')==gene.get('gene_digest') for x in child.get('selected_genes',[])):
            raise RuntimeError('GENE_ALREADY_IN_PORTFOLIO')
        child.setdefault('selected_genes',[]).append({
          'gene':copy.deepcopy(gene),
          'source_path':'CURRENT_ADAPTIVE_CYCLE',
          'source_receipt':None,
          'selected_for_tasks':[selected_for_task],
        })
        child['selected_genes']=sorted(child['selected_genes'],key=lambda x:x['gene'].get('gene_digest',''))
        child['selected_gene_count']=len(child['selected_genes'])
        child['schema']='yado.g2.adaptive_shadow_gene_portfolio.v1'
        child['controller_id']=self.COMPONENT_ID
        child['selection_policy']='REUSE_FIRST_THEN_TEMPORAL_STALL_INVENTION_THEN_FRESH_CAUSAL_GATE'
        child['promotion_state']='SHADOW_ONLY'
        child['automatic_canonical_promotion']=False
        child['portfolio_digest']=_digest(child)
        self.events.append({'event':'PORTFOLIO_EXPANDED','selected_gene_count':child['selected_gene_count'],'added_gene_digest':gene.get('gene_digest')})
        return child

    def evaluate_portfolio(self,portfolio,task_group):
        rows=[]
        for item in portfolio.get('selected_genes',[]):
            g=item.get('gene',{})
            s=self._score_gene(g,task_group)
            if s is not None:
                rows.append({'gene_id':g.get('gene_id'),'gene_digest':g.get('gene_digest'),'score':s})
        rows.sort(key=lambda r:(-r['score'],r['gene_digest'] or ''))
        return {'best_score':rows[0]['score'] if rows else 0.0,'rows':rows}

    @staticmethod
    def inherit_portfolio(parent,label):
        child={
          'schema':'yado.g2.adaptive_shadow_gene_portfolio.v1',
          'controller_id':parent['controller_id'],
          'shadow_generation':label,
          'lineage_parent_portfolio_digest':parent['portfolio_digest'],
          'selection_policy':parent['selection_policy'],
          'selected_genes':copy.deepcopy(parent['selected_genes']),
          'selected_gene_count':parent['selected_gene_count'],
          'promotion_state':'SHADOW_ONLY',
          'automatic_canonical_promotion':False,
        }
        child['portfolio_digest']=_digest(child)
        return child

    @classmethod
    def component(cls):
        x={
          'schema':'yado.g2.adaptive_evolution_controller.v1',
          'component_id':cls.COMPONENT_ID,
          'control_flow':['DISCOVER_AND_BUILD_EXISTING_PORTFOLIO','ATTEMPT_REUSE','DETECT_INSUFFICICIENCY','REQUIRE_TEMPORAL_STALL','INVENT_BOUNDED_GENERIC_OPERATOR','FRESH_CAUSAL_GATE','EXPAND_SHADOW_PORTFOLIO','INHERIT'],
          'gene_id_specific_rules':False,
          'automatic_canonical_promotion':False,
          'semantic_boundary':'BOUNDED SHADOW ADAPTIVE CONTROLLER. IT MUST ATTEMPT REUSE FIRST; ONLY A FAILED PORTFOLIO PLUS TEMPORAL STALL MAY OPEN A GENERIC WEIGHTED-STATE INVENTION PATH. IT CANNOT CANONICALLY PROMOTE.'
        }
        x['component_digest']=_digest(x);return x

__all__=['YADOAdaptiveEvolutionControllerV1']
