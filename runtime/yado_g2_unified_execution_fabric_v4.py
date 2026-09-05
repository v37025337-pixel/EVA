from __future__ import annotations

from pathlib import Path
import copy,hashlib,json,os

from yado_g2_unified_execution_fabric_v3 import G2UnifiedExecutionFabricV3

def _canon_v4(o):
    return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)

def _digest_v4(o):
    return hashlib.sha256(_canon_v4(o).encode()).hexdigest()

class G2UnifiedExecutionFabricV4(G2UnifiedExecutionFabricV3):
    COMPONENT_ID='RUNTIME-G2-UNIFIED-EXECUTION-FABRIC-V4'
    CHECKPOINT_SCHEMA='yado.g2.cognitive_continuity_checkpoint.v1'
    RECURRENT_SCHEMA='yado.g2.recurrent_memory.state.v1'

    def __init__(self,base_runtime,api_state=None,temporal_state=None,continuity_state=None,checkpoint_path=None):
        self._checkpoint_path=Path(checkpoint_path) if checkpoint_path else None
        loaded=None
        if continuity_state is not None and temporal_state is not None:
            raise ValueError('CONTINUITY_AND_TEMPORAL_STATE_ARE_MUTUALLY_EXCLUSIVE')
        if continuity_state is not None:
            loaded=self._validate_continuity_state(continuity_state)
        elif self._checkpoint_path is not None and self._checkpoint_path.exists():
            loaded=self._validate_continuity_state(self.load_continuity_checkpoint(self._checkpoint_path))
        temporal=loaded['temporal_state'] if loaded is not None else temporal_state
        super().__init__(base_runtime,api_state=api_state,temporal_state=temporal)
        self._restored_checkpoint_digest=None
        if loaded is not None:
            self._restore_recurrent_state(loaded['recurrent_memory_state'])
            self._validate_cross_layer(loaded)
            self._restored_checkpoint_digest=loaded.get('checkpoint_digest')

    @staticmethod
    def _episode_payload(e):
        return {k:v for k,v in e.items() if k!='episode_digest'}

    @classmethod
    def _export_recurrent_state(cls,base):
        episodes=[copy.deepcopy(x) for x in base.episodes]
        state={
          'schema':cls.RECURRENT_SCHEMA,
          'sequence':int(getattr(base,'sequence',0)),
          'stream_attempts':copy.deepcopy(getattr(base,'stream_attempts',{})),
          'episodes':episodes,
          'max_episodes':int(getattr(base,'MAX_EPISODES',128)),
          'max_attempted_per_stream':int(getattr(base,'MAX_ATTEMPTED_PER_STREAM',32)),
        }
        state['memory_state_digest']=_digest_v4({k:v for k,v in state.items() if k!='memory_state_digest'})
        return state

    @classmethod
    def _validate_recurrent_state(cls,state):
        s=copy.deepcopy(state)
        expected=s.pop('memory_state_digest',None)
        if not expected or _digest_v4(s)!=expected:
            raise ValueError('RECURRENT_MEMORY_STATE_DIGEST_MISMATCH')
        if s.get('schema')!=cls.RECURRENT_SCHEMA:
            raise ValueError('RECURRENT_MEMORY_STATE_SCHEMA')
        sequence=int(s.get('sequence',0))
        if sequence<0:
            raise ValueError('RECURRENT_MEMORY_NEGATIVE_SEQUENCE')
        episodes=list(s.get('episodes') or [])
        last_seq=0
        for e in episodes:
            if not isinstance(e,dict):
                raise ValueError('RECURRENT_MEMORY_EPISODE_TYPE')
            seq=int(e.get('sequence',0))
            if seq<=last_seq:
                raise ValueError('RECURRENT_MEMORY_EPISODE_SEQUENCE_ORDER')
            last_seq=seq
            ed=e.get('episode_digest')
            if not ed or _digest_v4(cls._episode_payload(e))!=ed:
                raise ValueError('RECURRENT_MEMORY_EPISODE_DIGEST_MISMATCH')
        if last_seq>sequence:
            raise ValueError('RECURRENT_MEMORY_SEQUENCE_REGRESSION')
        attempts=s.get('stream_attempts') or {}
        if not isinstance(attempts,dict):
            raise ValueError('RECURRENT_MEMORY_STREAM_ATTEMPTS_TYPE')
        max_attempts=int(s.get('max_attempted_per_stream',32))
        for sid,xs in attempts.items():
            if not isinstance(xs,list) or len(xs)>max_attempts:
                raise ValueError('RECURRENT_MEMORY_STREAM_ATTEMPTS_BOUNDS:'+str(sid))
            if len(xs)!=len(set(map(str,xs))):
                raise ValueError('RECURRENT_MEMORY_DUPLICATE_ATTEMPT:'+str(sid))
        return state

    def _restore_recurrent_state(self,state):
        self._validate_recurrent_state(state)
        s=copy.deepcopy(state)
        episodes=list(s.get('episodes') or [])
        self.base.sequence=int(s.get('sequence',0))
        self.base.stream_attempts=copy.deepcopy(s.get('stream_attempts') or {})
        self.base.episodes.clear()
        for e in episodes[-int(getattr(self.base,'MAX_EPISODES',128)):]:
            self.base.episodes.append(copy.deepcopy(e))

    @classmethod
    def _validate_continuity_state(cls,state):
        s=copy.deepcopy(state)
        expected=s.pop('checkpoint_digest',None)
        if not expected or _digest_v4(s)!=expected:
            raise ValueError('COGNITIVE_CONTINUITY_CHECKPOINT_DIGEST_MISMATCH')
        if s.get('schema')!=cls.CHECKPOINT_SCHEMA:
            raise ValueError('COGNITIVE_CONTINUITY_CHECKPOINT_SCHEMA')
        if not isinstance(s.get('temporal_state'),dict) or not isinstance(s.get('recurrent_memory_state'),dict):
            raise ValueError('COGNITIVE_CONTINUITY_CHECKPOINT_SECTIONS')
        cls._validate_recurrent_state(s['recurrent_memory_state'])
        return state

    def _validate_cross_layer(self,state):
        temporal=state['temporal_state']
        recurrent=state['recurrent_memory_state']
        records={int(r.get('tick_id',0)):r for r in temporal.get('records',[]) if isinstance(r,dict)}
        for e in recurrent.get('episodes',[]):
            if e.get('kind')!='TEMPORAL_TRANSITION':
                continue
            tid=int(e.get('tick_id',0))
            r=records.get(tid)
            if r is None:
                raise ValueError('CONTINUITY_TEMPORAL_TRANSITION_TICK_MISSING:'+str(tid))
            if e.get('tick_digest')!=r.get('tick_digest'):
                raise ValueError('CONTINUITY_TEMPORAL_TRANSITION_DIGEST_MISMATCH:'+str(tid))
        cross=state.get('cross_layer') or {}
        if int(cross.get('temporal_tick_id',-1))!=int(temporal.get('tick_id',-2)):
            raise ValueError('CONTINUITY_CROSS_LAYER_TICK_MISMATCH')
        if int(cross.get('recurrent_sequence',-1))!=int(recurrent.get('sequence',-2)):
            raise ValueError('CONTINUITY_CROSS_LAYER_SEQUENCE_MISMATCH')

    def export_continuity_state(self):
        if self.clock.snapshot().get('open_tick_count')!=0:
            raise RuntimeError('CANNOT_CHECKPOINT_WITH_OPEN_TICKS')
        temporal=self.export_temporal_state()
        recurrent=self._export_recurrent_state(self.base)
        state={
          'schema':self.CHECKPOINT_SCHEMA,
          'component_id':self.COMPONENT_ID,
          'temporal_state':temporal,
          'recurrent_memory_state':recurrent,
          'cross_layer':{
            'temporal_tick_id':int(temporal.get('tick_id',0)),
            'recurrent_sequence':int(recurrent.get('sequence',0)),
            'last_temporal_tick_digest':next((r.get('tick_digest') for r in reversed(temporal.get('records',[])) if r.get('status')=='CLOSED'),None),
            'last_episode_digest':recurrent.get('episodes',[])[-1].get('episode_digest') if recurrent.get('episodes') else None,
          },
          'persistence_mode':'ATOMIC_LOCAL_FILE_OPTIONAL_AUTO_CHECKPOINT',
          'automatic_canonical_promotion':False,
        }
        state['checkpoint_digest']=_digest_v4({k:v for k,v in state.items() if k!='checkpoint_digest'})
        self._validate_cross_layer(state)
        return state

    @staticmethod
    def load_continuity_checkpoint(path):
        return json.loads(Path(path).read_text(encoding='utf-8'))

    def save_continuity_checkpoint(self,path=None):
        p=Path(path) if path is not None else self._checkpoint_path
        if p is None:
            raise ValueError('CHECKPOINT_PATH_REQUIRED')
        state=self.export_continuity_state()
        p.parent.mkdir(parents=True,exist_ok=True)
        tmp=p.with_name(p.name+'.tmp')
        raw=json.dumps(state,indent=2,sort_keys=True,default=str)+'\n'
        with tmp.open('w',encoding='utf-8') as f:
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp,p)
        try:
            dfd=os.open(str(p.parent),os.O_RDONLY)
            try:os.fsync(dfd)
            finally:os.close(dfd)
        except Exception:
            pass
        return copy.deepcopy(state)

    def _auto_checkpoint(self):
        if self._checkpoint_path is not None and not self._tick_stack:
            self.save_continuity_checkpoint(self._checkpoint_path)

    def execute_capability(self,selected,task,ablated_memory=False):
        try:
            return super().execute_capability(selected,task,ablated_memory=ablated_memory)
        finally:
            self._auto_checkpoint()

    def record_outcome(self,stream_id,stage_id,observed_gain):
        try:
            return super().record_outcome(stream_id,stage_id,observed_gain)
        finally:
            self._auto_checkpoint()

    def continuity_snapshot(self):
        return {
          'component_id':self.COMPONENT_ID,
          'checkpoint_path':str(self._checkpoint_path) if self._checkpoint_path is not None else None,
          'restored_checkpoint_digest':self._restored_checkpoint_digest,
          'temporal':self.clock.snapshot(),
          'memory':self.memory_snapshot(),
        }

    @classmethod
    def component(cls):
        parent=G2UnifiedExecutionFabricV3.component()
        x={
          'schema':'yado.g2.unified_execution_fabric.v4',
          'component_id':cls.COMPONENT_ID,
          'parent_component':G2UnifiedExecutionFabricV3.COMPONENT_ID,
          'architecture_family':'TYPED_RECURRENT_CAPABILITY_GRAPH',
          'dispatches':parent.get('dispatches',[]),
          'continuity':{
            'unified_temporal_and_recurrent_checkpoint':True,
            'atomic_local_file_persistence':True,
            'optional_auto_checkpoint_after_top_level_state_change':True,
            'restart_restores_stage_outcomes':True,
            'restart_restores_attempted_stages':True,
            'restart_restores_temporal_predecessor':True,
            'cross_layer_digest_validation':True,
            'fail_closed_on_checkpoint_tamper':True,
          },
          'network_execution':parent.get('network_execution'),
          'canonical_active':False,
          'architecture_mutation':False,
          'automatic_canonical_promotion':False,
          'semantic_boundary':'SHADOW SUCCESSOR OF FABRIC V3. IT PERSISTS LOGICAL TIME AND RECURRENT EXECUTION MEMORY AS ONE ATOMIC CHECKPOINT SO RESTART DOES NOT ERASE STAGE OUTCOMES OR ATTEMPT HISTORY. LOCAL CHECKPOINT DURABILITY IS NOT DISTRIBUTED CONSENSUS.'
        }
        x['component_digest']=_digest_v4(x)
        return x

__all__=['G2UnifiedExecutionFabricV4']
