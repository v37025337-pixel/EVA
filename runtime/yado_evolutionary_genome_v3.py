from __future__ import annotations
import hashlib,json
from yado_evolutionary_genome_v2 import YADOEvolutionaryGenomeV2
from yado_generic_event_state_meta_language_v1 import GenericEventStateMetaLanguageV1

def _canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def _digest(o): return hashlib.sha256(_canon(o).encode()).hexdigest()

class YADOEvolutionaryGenomeV3(YADOEvolutionaryGenomeV2):
    COMPONENT_ID='CTRL-G2-EVOLUTIONARY-GENOME-V3'

    def invent_event_state_operator_from_examples(self,train_examples,stall_signal,parent_gene_ids):
        if not isinstance(stall_signal,dict) or stall_signal.get('mechanism_change_required') is not True:
            raise RuntimeError('TEMPORAL_STALL_SIGNAL_REQUIRED')
        if int(stall_signal.get('no_progress_ticks',0))<20:
            raise RuntimeError('STALL_THRESHOLD_NOT_REACHED')
        program=GenericEventStateMetaLanguageV1.synthesize(train_examples)
        if float(program.get('train_accuracy',0.0))<1.0:
            return {'status':'WITHHOLD','reason':'NO_EXACT_OPERATOR_WITHIN_EVENT_STATE_META_LANGUAGE','program':program}
        gid=program['synthesized_operator_id']
        if gid in set(parent_gene_ids):
            raise RuntimeError('SYNTHESIZED_GENE_COLLIDES_WITH_PARENT')
        gene={
          'schema':'yado.g2.self_synthesized_event_state_gene.v1',
          'gene_id':gid,
          'novel_gene':True,
          'gene_scope':['LOGIC','THINKING','INTELLIGENCE','CODE'],
          'heritage':sorted(set(str(x) for x in parent_gene_ids)),
          'trigger':{
            'source':'TEMPORAL_STALL_SIGNAL',
            'tick_id':stall_signal.get('tick_id'),
            'no_progress_ticks':stall_signal.get('no_progress_ticks'),
            'deficit_id':stall_signal.get('deficit_id'),
          },
          'meta_language_component':GenericEventStateMetaLanguageV1.COMPONENT_ID,
          'operator_program':program,
          'execution_mode':'BOUNDED_META_LANGUAGE_INTERPRETER',
          'promotion_state':'SHADOW_ONLY',
        }
        gene['gene_digest']=_digest(gene)
        return {'status':'SELF_SYNTHESIZED_SHADOW_GENE','gene':gene}

    @classmethod
    def component(cls):
        x={
          'schema':'yado.g2.evolutionary_genome.controller.v3',
          'component_id':cls.COMPONENT_ID,
          'parent_component':'CTRL-G2-EVOLUTIONARY-GENOME-V2',
          'chromosomes':['LOGIC','THINKING','INTELLIGENCE','CODE'],
          'event_state_operator_invention':True,
          'operator_invention_requires_temporal_stall':True,
          'meta_language':GenericEventStateMetaLanguageV1.component(),
          'automatic_canonical_promotion':False,
          'fresh_gate_required_for_promotion':True,
          'canonical_active':False,
          'architecture_mutation':False,
          'semantic_boundary':'SHADOW SUCCESSOR USED ONLY FOR A SECOND BLIND INVENTION TEST. IT SEARCHES GENERIC EVENT/STATE COMPOSITIONS AFTER A TEMPORAL STALL AND CANNOT PROMOTE ITS GENE.'
        }
        x['component_digest']=_digest(x)
        return x

__all__=['YADOEvolutionaryGenomeV3']
