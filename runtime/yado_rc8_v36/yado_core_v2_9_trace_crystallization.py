from __future__ import annotations

import hashlib
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Mapping

from yado_core_v2_8_meta_grammar import UnifiedYADOKernelV28MetaGrammar
from yado_transition_runtime_native_v1 import (
    AtomicTransitionSynthesizer,
    TransitionProgram,
    load_skill_library_from_report,
    search_with_skill_library,
)
from yado_meta_grammar_genesis_cycle1 import LowLevelCoordinateSynthesizer

ROOT=Path(__file__).resolve().parent


class UnifiedYADOKernelV29TraceCrystallization(UnifiedYADOKernelV28MetaGrammar):
    """V2.9 shadow runtime: failure-driven generic transition atoms + skill crystallization.

    Coordinate meta-grammar remains available for structural/index tasks. If it cannot
    express the task, V2.9 falls through to a generic atomic transition interpreter.
    Verified transition programs are reused from the crystallized skill library before
    full atomic search.
    """
    SCHEMA_VERSION=11
    PROFILE='YADO_V2_9_TRACE_CRYSTALLIZATION_SHADOW'

    def __init__(self, db_path: str='yado_v29_trace_crystallization_shadow.db'):
        super().__init__(db_path=db_path)
        report=ROOT/'yado_trace_crystallization_cycle3_report.json'
        self.transition_skill_library = load_skill_library_from_report(str(report)) if report.exists() else None

    def _bootstrap_domain_evidence(self)->None:
        super()._bootstrap_domain_evidence()
        resources=[
            ('external:github:lsdefine/GenericAgent','GenericAgent external research evidence: minimal atomic tools and verified path crystallization into reusable skills.',{
                'provider':'github_host_mediated','status':'ACTIVE_VERIFIED','authority':False,'repo':'lsdefine/GenericAgent','readme_sha':'afb47923b537fd328e704a2562230f95aabfe2a6'
            },['external_evidence','skill_crystallization','self_development']),
            ('internal:yado:trace-crystallization','YADO bounded trace crystallization developmental report.',{
                'provider':'internal_developmental_registry','status':'ACTIVE_VERIFIED','authority':False,'source_path':str(ROOT/'yado_trace_crystallization_cycle3_report.json')
            },['trace_crystallization','mechanism_genesis','developmental_evidence'])
        ]
        for rid,text,meta,tags in resources:
            if self.get_resource(rid,include_text=False) is None:
                self.add_resource(rid,text,metadata=meta,tags=tags)

    def _execute_genesis(self,payload:Mapping[str,Any],ablated:bool)->Dict[str,Any]:
        # Domain-mechanism ablation means revert to the previous V2.8 mechanism path.
        prior = super()._execute_genesis(payload, ablated=ablated)
        if ablated:
            return prior
        # Preserve V2.8 when it already solves the task; V2.9 is an expansion, not replacement.
        if float(prior.get('candidate',0.0)) >= 0.999999 and prior.get('output_correct'):
            return prior

        train=self._decode_cases(payload['train']); blind=self._decode_cases(payload['blind'])
        live_input=payload['live_input']; expected_live=payload['expected_live']
        baseline=float(prior.get('candidate',0.0))
        syn=AtomicTransitionSynthesizer()
        best=None; lib_n=0; full_n=0; mode='FULL_ATOMIC_TRANSITION_SEARCH'
        if self.transition_skill_library is not None:
            best,lib_n,_=search_with_skill_library(self.transition_skill_library,train)
            if best is not None and syn.score(best,train)['exact']==1.0:
                mode='CRYSTALLIZED_SKILL_INSTANTIATION'
            else:
                best=None
        if best is None:
            best,full_n,_=syn.search(train)
        if best is None:
            return {
                'mechanism':'TRACE_CRYSTALLIZATION','baseline':baseline,'candidate':0.0,'ablation':baseline,'restore':0.0,
                'live_output':None,'expected_live':expected_live,'output_correct':False,
                'details':{'search_mode':mode,'library_candidates':lib_n,'full_candidates':full_n}
            }
        frozen=TransitionProgram(**asdict(best))
        cand=float(syn.score(frozen,blind)['exact']); restore=float(syn.score(frozen,blind)['exact'])
        try: live=syn.execute(frozen,live_input)
        except Exception: live=None
        return {
            'mechanism':'TRACE_CRYSTALLIZATION','baseline':baseline,'candidate':cand,'ablation':baseline,'restore':restore,
            'live_output':live,'expected_live':expected_live,'output_correct':live==expected_live,
            'details':{
                'search_mode':mode,'library_candidates':lib_n,'full_candidates':full_n,
                'derived_program':asdict(frozen),'program_digest':frozen.digest,
                'external_lesson_source':'lsdefine/GenericAgent',
                'genericagent_code_imported':False,'genericagent_code_executed':False,
                'host_supplied_coordinate_algebra_active_for_this_solution':False,
                'host_supplied_named_task_family_list':False,
                'host_supplied_generic_expression_atoms':True,
                'skill_crystallization_library_active':True,
            }
        }

__all__=['UnifiedYADOKernelV29TraceCrystallization']
