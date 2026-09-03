from __future__ import annotations
import copy,hashlib,json
from yado_evolutionary_genome_v1 import YADOEvolutionaryGenomeV1
from yado_generic_relational_meta_language_v1 import GenericRelationalMetaLanguageV1

def _canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def _digest(o):return hashlib.sha256(_canon(o).encode()).hexdigest()

class YADOEvolutionaryGenomeV2(YADOEvolutionaryGenomeV1):
    COMPONENT_ID='CTRL-G2-EVOLUTIONARY-GENOME-V2'

    def invent_operator_from_examples(self,train_examples,stall_signal,parent_gene_ids):
        if not isinstance(stall_signal,dict) or stall_signal.get('mechanism_change_required') is not True:
            raise RuntimeError('TEMPORAL_STALL_SIGNAL_REQUIRED')
        if int(stall_signal.get('no_progress_ticks',0))<20:
            raise RuntimeError('STALL_THRESHOLD_NOT_REACHED')
        program=GenericRelationalMetaLanguageV1.synthesize(train_examples)
        if float(program.get('train_accuracy',0.0))<1.0:
            return {'status':'WITHHOLD','reason':'NO_EXACT_OPERATOR_WITHIN_META_LANGUAGE','program':program}
        gid=program['synthesized_operator_id']
        if gid in set(parent_gene_ids):raise RuntimeError('SYNTHESIZED_GENE_COLLIDES_WITH_PARENT')
        gene={
          'schema':'yado.g2.self_synthesized_operator_gene.v1',
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
          'meta_language_component':GenericRelationalMetaLanguageV1.COMPONENT_ID,
          'operator_program':program,
          'execution_mode':'BOUNDED_META_LANGUAGE_INTERPRETER',
          'promotion_state':'SHADOW_ONLY',
        }
        gene['gene_digest']=_digest(gene)
        return {'status':'SELF_SYNTHESIZED_SHADOW_GENE','gene':gene}

    @classmethod
    def component(cls):
        x={
          'schema':'yado.g2.evolutionary_genome.controller.v2',
          'component_id':cls.COMPONENT_ID,
          'parent_component':'CTRL-G2-EVOLUTIONARY-GENOME-V1',
          'chromosomes':['LOGIC','THINKING','INTELLIGENCE','CODE'],
          'novel_operator_invention':True,
          'operator_invention_requires_temporal_stall':True,
          'meta_language':GenericRelationalMetaLanguageV1.component(),
          'automatic_canonical_promotion':False,
          'fresh_gate_required_for_promotion':True,
          'canonical_active':False,
          'architecture_mutation':False,
          'semantic_boundary':'SHADOW SUCCESSOR OF GENOME V1. IT MAY INVENT A NEW EXECUTABLE GENE BY SEARCHING GENERIC META-LANGUAGE COMPOSITIONS AFTER A TEMPORAL STALL, BUT CANNOT PROMOTE IT.'
        }
        x['component_digest']=_digest(x);return x

__all__=['YADOEvolutionaryGenomeV2']
