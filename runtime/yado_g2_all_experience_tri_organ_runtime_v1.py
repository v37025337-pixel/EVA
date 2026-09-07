from __future__ import annotations

from copy import deepcopy
from typing import Any

from yado_generic_relational_meta_language_v1 import GenericRelationalMetaLanguageV1
from yado_generic_event_state_meta_language_v1 import GenericEventStateMetaLanguageV1

CAP_LOGIC='ALG-G2-ALL-EXPERIENCE-RELATIONAL-CAUSAL-LOGIC-V1'
CAP_THINKING='ALG-G2-ALL-EXPERIENCE-CAUSAL-EVENT-THINKING-V1'
CAP_INTELLIGENCE='ALG-G2-ALL-EXPERIENCE-CAUSAL-GENE-PORTFOLIO-INTELLIGENCE-V1'

class G2AllExperienceTriOrganRuntimeV1:
    """Bounded additive runtime for the admitted all-experience tri-organ genome.

    This runtime does not replace the canonical V2/V2/V3 parents. It exposes the
    self-synthesized relation/event mechanisms through explicit contracts and
    fails closed for unsupported contracts.
    """

    def __init__(self,artifact:dict[str,Any]):
        self.artifact=deepcopy(artifact)
        if self.artifact.get('status')!='CANONICAL_ACTIVE':
            raise ValueError('TRI_ORGAN_ARTIFACT_NOT_CANONICAL_ACTIVE')
        genes=self.artifact.get('genes') or {}
        for organ in ('LOGIC','THINKING','INTELLIGENCE'):
            if organ not in genes:
                raise ValueError('MISSING_TRI_ORGAN_GENE:'+organ)
        self.genes=genes
        self.logic_program=deepcopy(genes['LOGIC']['operator_program'])
        self.thinking_program=deepcopy(genes['THINKING']['operator_program'])
        self.contract_routes=deepcopy(self.artifact.get('contract_routes') or {})
        required={
          'RELATION_START_TO_STATE':CAP_LOGIC,
          'EVENT_SEQUENCE_TO_BOOLEAN':CAP_THINKING,
        }
        if self.contract_routes!=required:
            raise ValueError('TRI_ORGAN_CONTRACT_ROUTE_MISMATCH')

    def logic(self,relation,start)->dict[str,Any]:
        result=GenericRelationalMetaLanguageV1.execute(self.logic_program,relation,start)
        return {
          'status':'PASS_TRI_ORGAN_LOGIC',
          'component_id':CAP_LOGIC,
          'gene_id':self.genes['LOGIC']['gene_id'],
          'mechanism_type':self.genes['LOGIC']['mechanism_type'],
          'contract':'RELATION_START_TO_STATE',
          'result':result,
          'rollback_parent':self.artifact['rollback_parents']['LOGIC'],
          'canonical_promotion_authorized':False,
        }

    def thinking(self,events)->dict[str,Any]:
        result=GenericEventStateMetaLanguageV1.execute(self.thinking_program,events)
        return {
          'status':'PASS_TRI_ORGAN_THINKING',
          'component_id':CAP_THINKING,
          'gene_id':self.genes['THINKING']['gene_id'],
          'mechanism_type':self.genes['THINKING']['mechanism_type'],
          'contract':'EVENT_SEQUENCE_TO_BOOLEAN',
          'result':result,
          'rollback_parent':self.artifact['rollback_parents']['THINKING'],
          'canonical_promotion_authorized':False,
        }

    def intelligence(self,task:dict[str,Any])->dict[str,Any]:
        contract=str(task.get('input_contract') or '')
        selected=self.contract_routes.get(contract)
        if selected==CAP_LOGIC:
            organ=self.logic(task.get('relation',()),task.get('start'))
        elif selected==CAP_THINKING:
            organ=self.thinking(task.get('events',()))
        else:
            return {
              'status':'WITHHOLD_UNSUPPORTED_CONTRACT',
              'component_id':CAP_INTELLIGENCE,
              'gene_id':self.genes['INTELLIGENCE']['gene_id'],
              'input_contract':contract,
              'selected_component':None,
              'supported_contracts':sorted(self.contract_routes),
              'rollback_parent':self.artifact['rollback_parents']['INTELLIGENCE'],
              'canonical_promotion_authorized':False,
            }
        return {
          'status':'PASS_TRI_ORGAN_INTELLIGENCE_ROUTE',
          'component_id':CAP_INTELLIGENCE,
          'gene_id':self.genes['INTELLIGENCE']['gene_id'],
          'mechanism_type':self.genes['INTELLIGENCE']['mechanism_type'],
          'input_contract':contract,
          'selected_component':selected,
          'selected_gene_id':organ['gene_id'],
          'organ_result':organ,
          'result':organ['result'],
          'rollback_parent':self.artifact['rollback_parents']['INTELLIGENCE'],
          'canonical_promotion_authorized':False,
        }

    def snapshot(self)->dict[str,Any]:
        return {
          'schema':'yado.g2.all_experience_tri_organ.runtime_snapshot.v1',
          'status':'CANONICAL_ACTIVE',
          'genome_id':self.artifact.get('genome_id'),
          'components':deepcopy(self.artifact.get('components')),
          'contract_routes':deepcopy(self.contract_routes),
          'rollback_parents':deepcopy(self.artifact.get('rollback_parents')),
          'v4_preserved':self.artifact.get('v4_preserved') is True,
          'v7_preserved':self.artifact.get('v7_preserved') is True,
          'automatic_canonical_promotion':False,
        }

__all__=[
 'G2AllExperienceTriOrganRuntimeV1',
 'CAP_LOGIC','CAP_THINKING','CAP_INTELLIGENCE'
]
