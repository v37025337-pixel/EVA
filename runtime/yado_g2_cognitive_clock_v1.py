from __future__ import annotations
from collections import deque
from datetime import datetime,timezone
import copy,hashlib,json

def _canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def _digest(o):return hashlib.sha256(_canon(o).encode()).hexdigest()

class G2CognitiveClockV1:
    COMPONENT_ID='RUNTIME-G2-COGNITIVE-TEMPORAL-KERNEL-V1'
    MAX_TICKS=1024
    MAX_STREAMS=256
    MAX_ENTITIES=512
    DEFAULT_STALL_THRESHOLD=20

    def __init__(self,state=None):
        self.tick_id=0
        self.records=deque(maxlen=self.MAX_TICKS)
        self.streams={}
        self.entities={}
        if state:self.restore_state(state)

    @staticmethod
    def _bounded_projection(value,depth=0):
        if depth>3:return '<DEPTH_LIMIT>'
        if value is None or isinstance(value,(bool,int,float,str)):
            s=value
            if isinstance(s,str) and len(s)>512:return s[:512]+'<TRUNCATED>'
            return s
        if isinstance(value,dict):
            out={}
            for k in sorted(value,key=str)[:32]:
                if str(k) in {'body_text','source','raw_text','content'}:
                    v=value[k]
                    out[str(k)+'_sha256']=hashlib.sha256(str(v).encode()).hexdigest()
                    continue
                out[str(k)]=G2CognitiveClockV1._bounded_projection(value[k],depth+1)
            return out
        if isinstance(value,(list,tuple,set)):
            return [G2CognitiveClockV1._bounded_projection(x,depth+1) for x in list(value)[:32]]
        return str(value)[:512]

    @staticmethod
    def _wall_time():
        return datetime.now(timezone.utc).isoformat()

    def _stream(self,stream_id):
        sid=str(stream_id or 'GLOBAL')
        if sid not in self.streams:
            if len(self.streams)>=self.MAX_STREAMS:
                victim=sorted(self.streams.items(),key=lambda kv:(kv[1].get('last_tick',0),kv[0]))[0][0]
                del self.streams[victim]
            self.streams[sid]={
              'episode_tick':0,'last_tick':None,'last_progress_digest':None,
              'no_progress_ticks':0,'last_state_digest':None,'last_result_digest':None,
            }
        return sid,self.streams[sid]

    def _touch_entity(self,entity_id,entity_type,tick_id):
        eid=str(entity_id)
        if not eid:return
        if eid not in self.entities:
            if len(self.entities)>=self.MAX_ENTITIES:
                victim=sorted(self.entities.items(),key=lambda kv:(kv[1].get('tick_last_used',0),kv[0]))[0][0]
                del self.entities[victim]
            self.entities[eid]={
              'entity_id':eid,'entity_type':str(entity_type or 'ENTITY'),
              'tick_created':int(tick_id),'tick_last_used':int(tick_id),'use_count':1,
            }
        else:
            self.entities[eid]['tick_last_used']=int(tick_id)
            self.entities[eid]['use_count']=int(self.entities[eid].get('use_count',0))+1

    def begin_tick(self,stream_id,action,state=None,cause=None,prediction=None,entities=None,parent_tick=None):
        sid,s=self._stream(stream_id)
        self.tick_id+=1
        tid=self.tick_id
        s['episode_tick']+=1
        predecessor=s.get('last_tick')
        projected_state=self._bounded_projection(state or {})
        rec={
          'schema':'yado.g2.cognitive_tick.v1',
          'tick_id':tid,'episode_tick':s['episode_tick'],'stream_id':sid,
          'predecessor_tick':predecessor,'parent_tick':parent_tick,
          'action':str(action),
          'cause':self._bounded_projection(cause),
          'prediction':self._bounded_projection(prediction),
          'state_digest':_digest(projected_state),
          'state_projection':projected_state,
          'wall_time_started':self._wall_time(),
          'status':'OPEN',
        }
        s['last_tick']=tid
        s['last_state_digest']=rec['state_digest']
        self._touch_entity('STREAM:'+sid,'STREAM',tid)
        self._touch_entity('ACTION:'+str(action),'ACTION',tid)
        for x in entities or []:
            if isinstance(x,dict):self._touch_entity(x.get('entity_id',x.get('id','')),x.get('entity_type',x.get('type','ENTITY')),tid)
            else:self._touch_entity(x,'ENTITY',tid)
        self.records.append(rec)
        return copy.deepcopy(rec)

    def finish_tick(self,tick_id,observed_result=None,progress_token=None,next_state=None):
        target=None
        for r in reversed(self.records):
            if r.get('tick_id')==int(tick_id):
                target=r;break
        if target is None:raise KeyError('UNKNOWN_TICK:'+str(tick_id))
        if target.get('status')!='OPEN':raise RuntimeError('TICK_ALREADY_CLOSED:'+str(tick_id))
        sid=target['stream_id'];s=self.streams[sid]
        observed=self._bounded_projection(observed_result)
        next_projection=self._bounded_projection(next_state if next_state is not None else observed_result)
        result_digest=_digest(observed)
        progress_projection=self._bounded_projection(progress_token if progress_token is not None else next_projection)
        progress_digest=_digest(progress_projection)
        if s.get('last_progress_digest')==progress_digest:
            s['no_progress_ticks']=int(s.get('no_progress_ticks',0))+1
        else:
            s['no_progress_ticks']=0
        s['last_progress_digest']=progress_digest
        s['last_result_digest']=result_digest
        target.update({
          'observed_result':observed,
          'observed_result_digest':result_digest,
          'next_state_digest':_digest(next_projection),
          'progress_digest':progress_digest,
          'no_progress_ticks':s['no_progress_ticks'],
          'mechanism_change_required':s['no_progress_ticks']>=self.DEFAULT_STALL_THRESHOLD,
          'wall_time_finished':self._wall_time(),
          'status':'CLOSED',
        })
        target['tick_digest']=_digest({k:v for k,v in target.items() if k!='tick_digest'})
        return copy.deepcopy(target)

    def entity_age(self,entity_id,at_tick=None):
        e=self.entities.get(str(entity_id))
        if not e:return None
        now=int(self.tick_id if at_tick is None else at_tick)
        return {
          **copy.deepcopy(e),
          'age_ticks':max(0,now-int(e['tick_created'])),
          'idle_ticks':max(0,now-int(e['tick_last_used'])),
        }

    def stream_state(self,stream_id):
        sid,s=self._stream(stream_id)
        x=copy.deepcopy(s)
        x['stream_id']=sid
        x['mechanism_change_required']=x['no_progress_ticks']>=self.DEFAULT_STALL_THRESHOLD
        return x

    def causal_chain(self,stream_id,limit=32):
        sid=str(stream_id or 'GLOBAL')
        xs=[copy.deepcopy(r) for r in self.records if r.get('stream_id')==sid]
        xs=xs[-max(1,min(int(limit),128)):]
        return xs

    def export_state(self):
        state={
          'schema':'yado.g2.cognitive_clock.state.v1',
          'tick_id':self.tick_id,
          'streams':copy.deepcopy(self.streams),
          'entities':copy.deepcopy(self.entities),
          'records':[copy.deepcopy(x) for x in self.records],
        }
        state['state_digest']=_digest({k:v for k,v in state.items() if k!='state_digest'})
        return state

    def restore_state(self,state):
        s=copy.deepcopy(state)
        expected=s.pop('state_digest',None)
        if expected and _digest(s)!=expected:raise ValueError('TEMPORAL_STATE_DIGEST_MISMATCH')
        if s.get('schema')!='yado.g2.cognitive_clock.state.v1':raise ValueError('TEMPORAL_STATE_SCHEMA')
        self.tick_id=int(s.get('tick_id',0))
        self.streams=copy.deepcopy(s.get('streams',{}))
        self.entities=copy.deepcopy(s.get('entities',{}))
        self.records=deque(copy.deepcopy(s.get('records',[]))[-self.MAX_TICKS:],maxlen=self.MAX_TICKS)
        if any(int(r.get('tick_id',0))>self.tick_id for r in self.records):raise ValueError('TEMPORAL_STATE_TICK_REGRESSION')

    def snapshot(self):
        return {
          'component_id':self.COMPONENT_ID,
          'tick_id':self.tick_id,
          'record_count':len(self.records),
          'stream_count':len(self.streams),
          'entity_count':len(self.entities),
          'open_tick_count':sum(1 for r in self.records if r.get('status')=='OPEN'),
          'last_tick_digest':next((r.get('tick_digest') for r in reversed(self.records) if r.get('status')=='CLOSED'),None),
        }

    @classmethod
    def component(cls):
        x={
          'schema':'yado.g2.cognitive_temporal_kernel.v1',
          'component_id':cls.COMPONENT_ID,
          'logical_tick':True,'episode_time':True,'causal_time':True,'wall_time':True,
          'monotonic_tick':True,'predecessor_tick':True,'entity_age':True,
          'no_progress_ticks':True,'stall_threshold':cls.DEFAULT_STALL_THRESHOLD,
          'bounded_tick_records':cls.MAX_TICKS,'bounded_streams':cls.MAX_STREAMS,'bounded_entities':cls.MAX_ENTITIES,
          'wall_time_not_used_for_causal_ordering':True,
          'canonical_active':False,'architecture_mutation':False,
          'semantic_boundary':'LOGICAL TEMPORAL CONTINUITY FOR COGNITIVE EXECUTION. WALL TIME IS EXTERNAL SYNCHRONIZATION METADATA; CAUSAL ORDER IS DEFINED BY MONOTONIC LOGICAL TICKS.'
        }
        x['component_digest']=_digest(x);return x

__all__=['G2CognitiveClockV1']
