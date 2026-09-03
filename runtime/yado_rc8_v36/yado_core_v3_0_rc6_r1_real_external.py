from __future__ import annotations
import json, re, math, fnmatch
from collections import Counter
from pathlib import Path
from typing import Mapping, Sequence
from yado_core_v3_0_rc6_meta_grammar import UnifiedYADOKernelV30RC6MetaGrammar
from yado_evolution_runtime_native_v1 import bounded_enum, fit_bool_tree, acc_logic_model

ROOT=Path(__file__).resolve().parent
DEFAULT_STATE=ROOT/'yado_canonical_state_v3_rc6_r1_real_external.json'

class UnifiedYADOKernelV30RC6R1RealExternal(UnifiedYADOKernelV30RC6MetaGrammar):
    PROFILE='YADO_V3_0_RC6_R1_REAL_EXTERNAL_TRAINED_LOCAL'
    SCHEMA_VERSION=20
    def __init__(self, db_path='yado_v30_rc6_r1_real_external.db', state_path=None):
        super().__init__(db_path=db_path,state_path=state_path or str(DEFAULT_STATE))

    def real_external_registry(self):
        return dict(self.canonical_state.get('real_external_training_registry') or {})

    def post_failure_logic_refit(self, revealed_cases, fresh_cases=None):
        """Refit only existing durable LOGIC algorithms after a verified external failure.
        Selection uses revealed cases only: exactness first, then minimal complexity.
        fresh_cases is evaluated only after selection.
        """
        rows=[]
        for a in self.canonical_state['organ_evolution_algorithm_bank']['LOGIC']:
            fam=a['family']
            if fam=='ENUM_BOOLEAN':
                model,meta=bounded_enum(revealed_cases,int(a.get('max_depth',3)),float(a.get('refit_timeout_s',4.0)))
                train=0.0 if model is None else acc_logic_model(fam,model,revealed_cases)
            elif fam=='BOOL_DECISION_TREE':
                model=fit_bool_tree(revealed_cases,int(a['max_depth']));meta={}
                train=acc_logic_model(fam,model,revealed_cases)
            else:
                continue
            complexity=(0 if fam=='ENUM_BOOLEAN' else int(a.get('max_depth',99)))
            rows.append({'algorithm':a,'model':model,'revealed_exact':train,'complexity':complexity,'meta':meta})
        exact=[r for r in rows if r['revealed_exact']>=1.0]
        if not exact:
            return {'status':'WITHHOLD_NO_EXACT_REVEALED_MODEL','candidates':rows,'fresh_blind':None}
        # Preserve existing families; choose the least complex exact candidate. Do not inspect fresh.
        sel=min(exact,key=lambda r:(r['complexity'], r['algorithm']['family']!='BOOL_DECISION_TREE'))
        fresh=None
        if fresh_cases is not None:
            fresh=acc_logic_model(sel['algorithm']['family'],sel['model'],fresh_cases)
        return {'status':'SELECTED_EXISTING_ALGORITHM_AFTER_EXTERNAL_FAILURE','selected_algorithm':sel['algorithm'],
                'revealed_exact':sel['revealed_exact'],'fresh_blind':fresh,'fresh_used_for_selection':False}

    @staticmethod
    def dependency_closure(graph:Mapping[str,Sequence[str]], target:str):
        seen=set(); stack=list(graph.get(target,()))
        while stack:
            x=stack.pop()
            if x in seen: continue
            seen.add(x); stack.extend(graph.get(x,()))
        return sorted(seen)

    @staticmethod
    def _grams(text,n):
        s=' '+re.sub(r'[^a-z0-9]+',' ',text.lower())+' '
        return Counter(s[i:i+n] for i in range(max(0,len(s)-n+1)))
    @staticmethod
    def _cos(a,b):
        dot=sum(v*b.get(k,0) for k,v in a.items())
        na=math.sqrt(sum(v*v for v in a.values())); nb=math.sqrt(sum(v*v for v in b.values()))
        return dot/(na*nb) if na and nb else 0.0

    def route_external_text(self, text:str):
        cfg=self.real_external_registry().get('INTELLIGENCE',{})
        n=int(cfg.get('ngram_n',3)); threshold=float(cfg.get('defer_margin',1.0))
        profiles=cfg.get('centroid_profiles') or {}
        g=self._grams(text,n)
        scores={name:self._cos(g,self._grams(profile,n)) for name,profile in profiles.items()}
        if len(scores)<2: return {'action':'SEEK_MORE_EVIDENCE','scores':scores,'margin':0.0}
        ranked=sorted(scores.items(),key=lambda z:(z[1],z[0]),reverse=True)
        margin=ranked[0][1]-ranked[1][1]
        return {'action':'USE_ROUTE' if margin>=threshold else 'SEEK_MORE_EVIDENCE',
                'route':ranked[0][0] if margin>=threshold else None,'top_candidate':ranked[0][0],
                'margin':margin,'threshold':threshold,'scores':scores}

    def unified_snapshot(self):
        s=super().unified_snapshot(); s.update({'profile':self.PROFILE,'real_external_training':self.real_external_registry()}); return s

__all__=['UnifiedYADOKernelV30RC6R1RealExternal']
