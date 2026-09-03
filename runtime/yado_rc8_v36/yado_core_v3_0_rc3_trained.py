from __future__ import annotations
import json
from pathlib import Path
from typing import Any,Mapping,Sequence
from yado_core_v3_0_rc3_autoevolution import UnifiedYADOKernelV30RC3AutoEvolution
from yado_organ_runtime_native_v1 import eval_bool,plan_with_edges,tree_predict

ROOT=Path(__file__).resolve().parent
DEFAULT_TRAINED_STATE=ROOT/'yado_canonical_state_v3_rc3_trained.json'


def _jaccard(a,b):
    a,b=set(map(str,a)),set(map(str,b));return len(a&b)/max(1,len(a|b))

def _choose(bank,signature):
    return max(bank,key=lambda e:(_jaccard(signature,e.get('signature',[])),len(set(map(str,signature))&set(map(str,e.get('signature',[])))),-len(e.get('signature',[])),str(e.get('capability',''))))

class UnifiedYADOKernelV30RC3Trained(UnifiedYADOKernelV30RC3AutoEvolution):
    PROFILE='YADO_V3_0_RC3_TRAINED_ORGAN_SKILL_BANK_LOCAL'
    SCHEMA_VERSION=16
    def __init__(self,db_path='yado_v30_rc3_trained.db',state_path:str|None=None):
        super().__init__(db_path=db_path,state_path=state_path or str(DEFAULT_TRAINED_STATE))
    def organ_skill_banks(self):return dict(self.canonical_state.get('organ_skill_banks') or {})
    def _bank(self,organ):return list(self.organ_skill_banks().get(organ,[]))
    def logic_evolved_decision(self,features:Mapping[str,bool])->str:
        b=self._bank('LOGIC')
        if not b:return super().logic_evolved_decision(features)
        e=_choose(b,features.keys());return 'ALLOW' if eval_bool(e['model'],features) else 'WITHHOLD'
    def thinking_evolved_plan(self,actions:Sequence[Mapping[str,str]])->list[str]:
        b=self._bank('THINKING')
        if not b:return super().thinking_evolved_plan(actions)
        roles=[str(a['role']) for a in actions];e=_choose(b,roles);return plan_with_edges(actions,e['model'])
    def intelligence_evolved_strategy(self,features:Mapping[str,float])->str:
        b=self._bank('INTELLIGENCE')
        if not b:return super().intelligence_evolved_strategy(features)
        e=_choose(b,features.keys());return tree_predict(e['model'],features)
    def unified_snapshot(self):
        s=super().unified_snapshot();banks=self.organ_skill_banks();s.update({'profile':self.PROFILE,'trained_skill_bank_enabled':bool(banks),'trained_skill_counts':{k:len(v) for k,v in banks.items()},'training_retention_gate':self.canonical_state.get('training_retention_gate')});return s

__all__=['UnifiedYADOKernelV30RC3Trained']
