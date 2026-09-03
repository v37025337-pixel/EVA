from __future__ import annotations
from pathlib import Path
import copy,hashlib,json

from yado_generic_relational_meta_language_v1 import GenericRelationalMetaLanguageV1
from yado_generic_event_state_meta_language_v1 import GenericEventStateMetaLanguageV1

def _canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def _digest(o): return hashlib.sha256(_canon(o).encode()).hexdigest()

class YADOAutonomousGenePortfolioControllerV1:
    COMPONENT_ID='CTRL-G2-AUTONOMOUS-GENE-PORTFOLIO-V1'
    ADAPTERS={
      GenericRelationalMetaLanguageV1.COMPONENT_ID:GenericRelationalMetaLanguageV1,
      GenericEventStateMetaLanguageV1.COMPONENT_ID:GenericEventStateMetaLanguageV1,
    }

    def __init__(self,repo_root:Path):
        self.repo_root=Path(repo_root)

    def discover_shadow_genes(self):
        root=self.repo_root/'candidates'/'kernel-self-generated'
        genes={}
        for p in sorted(root.glob('*.json')):
            try:
                doc=json.loads(p.read_text(encoding='utf-8'))
            except Exception:
                continue
            gene=doc.get('invented',{}).get('gene')
            if not isinstance(gene,dict):
                continue
            if gene.get('novel_gene') is not True or gene.get('promotion_state')!='SHADOW_ONLY':
                continue
            gid=gene.get('gene_id'); gd=gene.get('gene_digest')
            if not gid or not gd:
                continue
            genes[gd]={'gene':copy.deepcopy(gene),'source_path':str(p.relative_to(self.repo_root)),'source_receipt':doc.get('receipt_sha256')}
        return [genes[k] for k in sorted(genes)]

    @staticmethod
    def _contract_for_component(component_id):
        if component_id==GenericRelationalMetaLanguageV1.COMPONENT_ID:
            return 'RELATION_START_TO_STATE'
        if component_id==GenericEventStateMetaLanguageV1.COMPONENT_ID:
            return 'EVENT_SEQUENCE_TO_BOOLEAN'
        return None

    @classmethod
    def _accuracy(cls,gene,task_group):
        comp=gene.get('meta_language_component')
        adapter=cls.ADAPTERS.get(comp)
        if adapter is None:
            return None
        contract=cls._contract_for_component(comp)
        if task_group.get('input_contract')!=contract:
            return None
        program=gene.get('operator_program',{})
        cases=task_group.get('cases',[])
        if not program or not cases:
            return 0.0
        ok=0
        for c in cases:
            try:
                if contract=='RELATION_START_TO_STATE':
                    got=adapter.execute(program,c['relation'],c['start'])
                    expected=c['expected']
                    ok += (got==expected)
                elif contract=='EVENT_SEQUENCE_TO_BOOLEAN':
                    got=adapter.execute(program,c['events'])
                    expected=bool(c['expected'])
                    ok += (got is expected)
            except Exception:
                pass
        return ok/len(cases)

    @classmethod
    def _best_ablation_accuracy(cls,gene,task_group):
        comp=gene.get('meta_language_component')
        adapter=cls.ADAPTERS.get(comp)
        if adapter is None:
            return None
        contract=cls._contract_for_component(comp)
        if task_group.get('input_contract')!=contract:
            return None
        p=gene.get('operator_program',{})
        vals=[]
        try:
            abs_=adapter.ablations(p)
        except Exception:
            abs_=[]
        for a in abs_:
            g=copy.deepcopy(gene)
            g['operator_program']=a['program']
            s=cls._accuracy(g,task_group)
            if s is not None:
                vals.append(s)
        return max(vals,default=0.0)

    def select_portfolio(self,task_groups):
        discovered=self.discover_shadow_genes()
        score_matrix={}
        selected_by_task={}
        for task in task_groups:
            tid=task['task_id']
            rows=[]
            for item in discovered:
                gene=item['gene']
                score=self._accuracy(gene,task)
                if score is None:
                    continue
                ab=self._best_ablation_accuracy(gene,task)
                causal_gap=score-(ab if ab is not None else score)
                rows.append({
                  'gene_id':gene['gene_id'],'gene_digest':gene['gene_digest'],
                  'source_path':item['source_path'],'score':score,
                  'best_ablation_accuracy':ab,'causal_gap':causal_gap,
                })
            rows.sort(key=lambda r:(-r['score'],-r['causal_gap'],r['gene_digest']))
            score_matrix[tid]=rows
            winner=next((r for r in rows if r['score']==1.0 and r['best_ablation_accuracy']<1.0),None)
            if winner is not None:
                selected_by_task[tid]=winner

        selected_digests=sorted({x['gene_digest'] for x in selected_by_task.values()})
        selected=[]
        by_digest={x['gene']['gene_digest']:x for x in discovered}
        for gd in selected_digests:
            item=by_digest[gd]
            selected.append({
              'gene':copy.deepcopy(item['gene']),
              'source_path':item['source_path'],
              'source_receipt':item['source_receipt'],
              'selected_for_tasks':sorted([tid for tid,w in selected_by_task.items() if w['gene_digest']==gd]),
            })

        successor={
          'schema':'yado.g2.autonomous_shadow_gene_portfolio.v1',
          'controller_id':self.COMPONENT_ID,
          'selection_policy':'FRESH_EXACT_AND_CAUSAL_ABLATION',
          'selected_genes':selected,
          'selected_gene_count':len(selected),
          'selected_by_task':selected_by_task,
          'score_matrix':score_matrix,
          'promotion_state':'SHADOW_ONLY',
          'automatic_canonical_promotion':False,
        }
        successor['portfolio_digest']=_digest(successor)
        return successor

    @classmethod
    def evaluate_portfolio(cls,portfolio,task_group):
        rows=[]
        for item in portfolio.get('selected_genes',[]):
            gene=item.get('gene',{})
            s=cls._accuracy(gene,task_group)
            if s is not None:
                rows.append({'gene_id':gene.get('gene_id'),'gene_digest':gene.get('gene_digest'),'score':s})
        rows.sort(key=lambda r:(-r['score'],r['gene_digest'] or ''))
        return {'best_score':rows[0]['score'] if rows else 0.0,'rows':rows}

    @staticmethod
    def inherit_portfolio(parent,label):
        child={
          'schema':'yado.g2.autonomous_shadow_gene_portfolio.v1',
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
          'schema':'yado.g2.autonomous_gene_portfolio_controller.v1',
          'component_id':cls.COMPONENT_ID,
          'gene_discovery':'SCAN_SELF_GENERATED_EVIDENCE',
          'selection_basis':['FRESH_EXACT_FITNESS','STRUCTURAL_ABLATION_CAUSALITY'],
          'gene_id_specific_rules':False,
          'resynthesis_during_selection':False,
          'automatic_canonical_promotion':False,
          'semantic_boundary':'BOUNDED SHADOW PORTFOLIO CONTROLLER. IT DISCOVERS SELF-SYNTHESIZED GENES FROM EVIDENCE, SELECTS BY FRESH FITNESS AND CAUSAL ABLATION, AND BUILDS A SHADOW SUCCESSOR WITHOUT GENE-ID-SPECIFIC RULES OR RE-SYNTHESIS.'
        }
        x['component_digest']=_digest(x)
        return x

__all__=['YADOAutonomousGenePortfolioControllerV1']
