from __future__ import annotations
import json
from pathlib import Path
from yado_core_v3_0_rc5_algorithm_genesis import UnifiedYADOKernelV30RC5AlgorithmGenesis
import yado_meta_grammar_runtime_native_v1 as mg
ROOT=Path(__file__).resolve().parent
DEFAULT_STATE=ROOT/'yado_canonical_state_v3_rc6_meta_grammar.json'
class UnifiedYADOKernelV30RC6MetaGrammar(UnifiedYADOKernelV30RC5AlgorithmGenesis):
    PROFILE='YADO_V3_0_RC6_BOUNDED_SELF_EXPANDING_META_GRAMMAR_LOCAL'
    SCHEMA_VERSION=19
    def __init__(self,db_path='yado_v30_rc6_meta_grammar.db',state_path=None):
        super().__init__(db_path=db_path,state_path=state_path or str(DEFAULT_STATE))
    def meta_grammar_extension_registry(self):return list(self.canonical_state.get('meta_grammar_extension_registry') or [])
    def _operator(self,predicate_kind):
        for op in self.meta_grammar_extension_registry():
            if op.get('program_template',{}).get('op')=='IF_PREDICATE' and predicate_kind in op.get('predicate_program_types',[]):return op
        raise RuntimeError(f'no durable meta-grammar operator for {predicate_kind}')
    def synthesize_logic_with_extended_meta_grammar(self,fit,val,revealed,blind):
        self._operator('BOOL_TABLE');return mg.synth_logic_predicate(fit,val,revealed,blind,self.canonical_state['organ_evolution_algorithm_bank']['LOGIC'])
    def synthesize_thinking_with_extended_meta_grammar(self,fit,val,revealed,blind):
        self._operator('LINEAR_THRESHOLD');return mg.synth_thinking_predicate(fit,val,revealed,blind,self.canonical_state['organ_evolution_algorithm_bank']['THINKING'])
    def synthesize_intelligence_with_extended_meta_grammar(self,fit,val,revealed,blind):
        self._operator('LINEAR_THRESHOLD');return mg.synth_intel_predicate(fit,val,revealed,blind,self.canonical_state['organ_evolution_algorithm_bank']['INTELLIGENCE'])
    def meta_grammar_snapshot(self):
        return {'enabled':bool(self.canonical_state.get('meta_grammar_self_extension_enabled')),'operators':[x.get('meta_grammar_operator_id') for x in self.meta_grammar_extension_registry()],'policy':self.canonical_state.get('meta_grammar_extension_policy')}
    def unified_snapshot(self):
        s=super().unified_snapshot();s.update({'profile':self.PROFILE,'meta_grammar_extension':self.meta_grammar_snapshot()});return s
__all__=['UnifiedYADOKernelV30RC6MetaGrammar']
