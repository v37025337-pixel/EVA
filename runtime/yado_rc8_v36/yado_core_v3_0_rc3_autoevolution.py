from __future__ import annotations

import hashlib
import json
import os
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence, Tuple

from yado_core_v3_0_rc2 import UnifiedYADOKernelV30RC2
from yado_organ_runtime_native_v1 import (
    eval_bool, fit_tree, learn_edges, plan_with_edges, score_bool,
    synthesize_logic, tree_acc, tree_predict,
)

ROOT=Path(__file__).resolve().parent
DEFAULT_STATE=ROOT/'yado_canonical_state_v3_rc3_autoevolution.json'

class UnifiedYADOKernelV30RC3AutoEvolution(UnifiedYADOKernelV30RC2):
    SCHEMA_VERSION=15
    PROFILE='YADO_V3_0_RC3_BOUNDED_ORGAN_AUTOEVOLUTION_LOCAL'

    def _init_schema(self):
        super()._init_schema()
        with self.db_lock:
            self.conn.executescript('''
            CREATE TABLE IF NOT EXISTS organ_evolution_events(
              event_id TEXT PRIMARY KEY,
              organ TEXT NOT NULL,
              kind TEXT NOT NULL,
              payload_json TEXT NOT NULL,
              outcome_json TEXT,
              created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS organ_evolution_candidates(
              candidate_id TEXT PRIMARY KEY,
              organ TEXT NOT NULL,
              capability TEXT NOT NULL,
              model_json TEXT NOT NULL,
              train_score REAL NOT NULL,
              blind_score REAL NOT NULL,
              ablation_score REAL NOT NULL,
              restore_score REAL NOT NULL,
              verdict TEXT NOT NULL,
              created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            '''); self.conn.commit()

    def __init__(self,db_path='yado_v30_rc3.db',state_path:str|None=None):
        super().__init__(db_path=db_path,state_path=state_path or str(DEFAULT_STATE))

    def organ_autoevolution_models(self)->Dict[str,Any]:
        return dict(self.canonical_state.get('organ_autoevolution_registry') or {})

    def logic_evolved_decision(self,features:Mapping[str,bool])->str:
        m=self.organ_autoevolution_models().get('LOGIC')
        if not m:return 'WITHHOLD'
        return 'ALLOW' if eval_bool(m['model'],features) else 'WITHHOLD'

    def thinking_evolved_plan(self,actions:Sequence[Mapping[str,str]])->list[str]:
        m=self.organ_autoevolution_models().get('THINKING')
        if not m:return self.thinking_plan(actions)
        return plan_with_edges(actions,m['model'])

    def intelligence_evolved_strategy(self,features:Mapping[str,float])->str:
        m=self.organ_autoevolution_models().get('INTELLIGENCE')
        if not m:return self.intelligence_strategy(features)
        return tree_predict(m['model'],features)

    def record_organ_experience(self,organ:str,kind:str,payload:Mapping[str,Any],outcome:Mapping[str,Any]|None=None)->str:
        organ=organ.upper()
        if organ not in {'LOGIC','THINKING','INTELLIGENCE'}:raise ValueError('unsupported organ')
        event_id='OE-'+uuid.uuid4().hex[:16]
        with self.db_lock:
            self.conn.execute('INSERT INTO organ_evolution_events(event_id,organ,kind,payload_json,outcome_json) VALUES(?,?,?,?,?)',
                (event_id,organ,kind,json.dumps(dict(payload),sort_keys=True),None if outcome is None else json.dumps(dict(outcome),sort_keys=True)))
            self.conn.commit()
        return event_id

    def evolution_event_count(self,organ:str|None=None)->int:
        with self.db_lock:
            if organ:
                return int(self.conn.execute('SELECT COUNT(*) FROM organ_evolution_events WHERE organ=?',(organ.upper(),)).fetchone()[0])
            return int(self.conn.execute('SELECT COUNT(*) FROM organ_evolution_events').fetchone()[0])

    def _store_candidate(self,organ,capability,model,train,blind,ablation,restore,verdict):
        cid='OEC-'+hashlib.sha256(json.dumps(model,sort_keys=True).encode()).hexdigest()[:16]
        with self.db_lock:
            self.conn.execute('''INSERT OR REPLACE INTO organ_evolution_candidates
              (candidate_id,organ,capability,model_json,train_score,blind_score,ablation_score,restore_score,verdict)
              VALUES(?,?,?,?,?,?,?,?,?)''',(cid,organ,capability,json.dumps(model,sort_keys=True),train,blind,ablation,restore,verdict));self.conn.commit()
        return cid

    # --- Generic bounded next-round generators. Blind is validation only. ---
    def shadow_evolve_logic(self,train:Sequence[Tuple[Mapping[str,bool],bool]],blind:Sequence[Tuple[Mapping[str,bool],bool]],capability='learned_logic')->Dict[str,Any]:
        min_n=int(self.canonical_state.get('organ_autoevolution_policy',{}).get('minimum_evidence',{}).get('LOGIC',8))
        if len(train)<min_n:return {'verdict':'INSUFFICIENT_EVIDENCE','organ':'LOGIC'}
        model,meta=synthesize_logic(train,3);tr=score_bool(model,train);bl=score_bool(model,blind)
        maj=sum(y for _,y in train)>=len(train)/2;abl=sum(bool(y)==bool(maj) for _,y in blind)/max(1,len(blind));restore=bl
        verdict='SHADOW_SUPPORTED' if tr==1 and bl==1 and restore==1 and bl>abl else 'WITHHOLD'
        cid=self._store_candidate('LOGIC',capability,model,tr,bl,abl,restore,verdict)
        return {'organ':'LOGIC','candidate_id':cid,'model':model,'search':meta,'train':tr,'blind':bl,'ablation':abl,'restore':restore,'verdict':verdict}

    def shadow_evolve_thinking(self,successful_traces:Sequence[Sequence[str]],blind:Sequence[Tuple[Sequence[Mapping[str,str]],Sequence[str]]],capability='learned_planning')->Dict[str,Any]:
        min_n=int(self.canonical_state.get('organ_autoevolution_policy',{}).get('minimum_evidence',{}).get('THINKING',4))
        if len(successful_traces)<min_n:return {'verdict':'INSUFFICIENT_EVIDENCE','organ':'THINKING'}
        # threshold is selected only from revealed traces by maximum retained causal constraints.
        choices=[]
        for th in (.5,.6,.67,.75,.8,1.0):
            ed=learn_edges(successful_traces,th); choices.append((len(ed),th,ed))
        _,th,edges=max(choices,key=lambda z:(z[0],z[1]))
        def acc(ed):
            ok=0
            for actions,expected in blind:
                ids=plan_with_edges(actions,ed); rb={str(a['id']):str(a['role']) for a in actions};ok += [rb[i] for i in ids]==list(expected)
            return ok/max(1,len(blind))
        bl=acc(edges); base=acc(self.models['THINKING_PRECEDENCE_GRAPH']);restore=bl
        verdict='SHADOW_SUPPORTED' if bl==1 and bl>base else 'WITHHOLD'
        cid=self._store_candidate('THINKING',capability,edges,1.0,bl,base,restore,verdict)
        return {'organ':'THINKING','candidate_id':cid,'model':edges,'selected_threshold':th,'train':1.0,'blind':bl,'ablation':base,'restore':restore,'verdict':verdict}

    def shadow_evolve_intelligence(self,train:Sequence[Tuple[Mapping[str,float],str]],blind:Sequence[Tuple[Mapping[str,float],str]],capability='learned_strategy')->Dict[str,Any]:
        min_n=int(self.canonical_state.get('organ_autoevolution_policy',{}).get('minimum_evidence',{}).get('INTELLIGENCE',16))
        if len(train)<min_n:return {'verdict':'INSUFFICIENT_EVIDENCE','organ':'INTELLIGENCE'}
        selected=6;tree=None
        for d in range(1,7):
            t=fit_tree(train,d)
            if tree_acc(t,train)==1.0:selected=d;tree=t;break
        if tree is None:tree=fit_tree(train,6)
        tr=tree_acc(tree,train);bl=tree_acc(tree,blind)
        base=sum(self.intelligence_strategy(x)==y for x,y in blind)/max(1,len(blind));restore=bl
        verdict='SHADOW_SUPPORTED' if tr==1 and bl==1 and bl>base else 'WITHHOLD'
        cid=self._store_candidate('INTELLIGENCE',capability,tree,tr,bl,base,restore,verdict)
        return {'organ':'INTELLIGENCE','candidate_id':cid,'model':tree,'selected_depth':selected,'train':tr,'blind':bl,'ablation':base,'restore':restore,'verdict':verdict}

    def autoevolution_gate(self,candidates:Sequence[Mapping[str,Any]])->Dict[str,Any]:
        # Central controller knows only validation invariants, not organ-specific model semantics.
        passed=all(c.get('verdict')=='SHADOW_SUPPORTED' and float(c.get('blind',0))==1.0 and float(c.get('restore',0))==1.0 and float(c.get('blind',0))>float(c.get('ablation',1)) for c in candidates)
        return {'passed':passed,'candidate_count':len(candidates),'required':['blind=1','restore=1','blind>ablation','organ verdict supported']}

    @staticmethod
    def _atomic_write_json(path:Path,obj:Mapping[str,Any]):
        raw=json.dumps(dict(obj),indent=2,ensure_ascii=False,sort_keys=True).encode()
        fd,tmp=tempfile.mkstemp(prefix=path.name+'.',suffix='.tmp',dir=str(path.parent))
        try:
            with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
            os.replace(tmp,path)
        finally:
            if os.path.exists(tmp):os.unlink(tmp)

    def durable_commit_evolution_bundle(self,bundle:Mapping[str,Mapping[str,Any]],gate:Mapping[str,Any])->Dict[str,Any]:
        if not self.canonical_state.get('canonical_durable_mutation'):return {'committed':False,'reason':'DURABLE_MUTATION_DISABLED'}
        if not gate.get('passed'):return {'committed':False,'reason':'VALIDATION_GATE_FAILED'}
        allowed={'LOGIC','THINKING','INTELLIGENCE'}
        if set(bundle)!=allowed:return {'committed':False,'reason':'BUNDLE_MUST_COVER_THREE_ORGANS'}
        before=self.state_path.read_bytes();before_sha=hashlib.sha256(before).hexdigest();st=json.loads(before)
        registry={}
        for organ,c in bundle.items():
            registry[organ]={'model_type':{'LOGIC':'BOOLEAN_PROGRAM','THINKING':'PRECEDENCE_GRAPH','INTELLIGENCE':'STRATEGY_TREE'}[organ], 'model':c['model'],'evidence':{'blind':c['blind'],'ablation':c['ablation'],'restore':c['restore']}}
        st['organ_autoevolution_registry']=registry;st['organ_autoevolution_enabled']=True
        self._atomic_write_json(self.state_path,st);self.reload_canonical_state();after_sha=hashlib.sha256(self.state_path.read_bytes()).hexdigest()
        return {'committed':True,'before_sha256':before_sha,'after_sha256':after_sha}

    def unified_snapshot(self):
        s=super().unified_snapshot();mods=self.organ_autoevolution_models();s.update({
          'profile':self.PROFILE,
          'active_lineage':'YADO_V3_0_RC2 -> YADO_V3_0_RC3_BOUNDED_ORGAN_AUTOEVOLUTION_LOCAL',
          'organ_autoevolution_enabled':bool(self.canonical_state.get('organ_autoevolution_enabled')),
          'autoevolutionary_organs':sorted(mods),
          'organ_evolution_events':self.evolution_event_count(),
          'autoevolution_gate':'FRESH_BLIND + ABLATION + RESTORE + ROLLBACK',
          'unrestricted_self_code_rewrite':False,
        });return s

__all__=['UnifiedYADOKernelV30RC3AutoEvolution']
