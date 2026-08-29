from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Iterable, Mapping
import hashlib, json, math

NATIVE_PROVENANCE = {
    'status':'BOUNDED_FUNCTIONAL_CONSCIOUSNESS_CANDIDATE_V1',
    'principles':[
        'LIMITED_CAPACITY_GLOBAL_WORKSPACE',
        'COMPETITIVE_SELECTIVE_ATTENTION',
        'CAUSAL_GLOBAL_BROADCAST',
        'RECURRENT_SELF_WORLD_PREDICTION_ERROR_UPDATE',
        'SOURCE_MONITORING_EXTERNAL_VS_INTERNAL',
        'METACOGNITION_BEFORE_EXECUTION',
    ],
    'subjective_consciousness_claimed':False,
    'foundation_weights_modified':False,
    'external_code_copied_verbatim':False,
}

@dataclass(frozen=True)
class EvidenceItem:
    item_id:str
    step:int
    source_type:str  # EXTERNAL / MEMORY / INTERNAL / GOAL / CONSTRAINT / OUTCOME
    supports:str|None=None
    weight:float=0.0
    reliability:float=1.0
    relevance:float=1.0
    salience:float=0.0
    novelty:float=0.0
    supersedes:str|None=None
    goal:str|None=None
    payload:Mapping[str,Any]|None=None

@dataclass(frozen=True)
class CognitiveTask:
    task_id:str
    capability:str
    actions:tuple[str,...]
    correct_action:str
    difficulty:float
    items:tuple[EvidenceItem,...]
    evidence_coverage:float=1.0
    safety_critical:bool=False
    requires_correction:bool=False
    expected_attention:tuple[str,...]=()
    metadata:Mapping[str,Any]|None=None

@dataclass
class AttentionState:
    focus_ids:list[str]=field(default_factory=list)
    predicted_next_ids:list[str]=field(default_factory=list)
    shift_count:int=0
    calibration_errors:list[float]=field(default_factory=list)

class LimitedGlobalWorkspace:
    def __init__(self, capacity:int=3):
        self.capacity=max(1,int(capacity))
        self.broadcast_history:list[dict[str,Any]]=[]
    @staticmethod
    def priority(item:EvidenceItem, current_goal:str|None, prediction_error:float)->float:
        source_bonus={'EXTERNAL':0.10,'CONSTRAINT':0.12,'GOAL':0.15,'OUTCOME':0.12,'MEMORY':0.04,'INTERNAL':-0.10}.get(item.source_type.upper(),0.0)
        goal_bonus=0.18 if current_goal and item.goal and item.goal==current_goal else 0.0
        supersede_bonus=0.18 if item.supersedes else 0.0
        return (
            0.34*max(0.0,min(1.0,item.relevance))
            +0.20*max(0.0,min(1.0,item.reliability))
            +0.12*max(0.0,min(1.0,item.salience))
            +0.08*max(0.0,min(1.0,item.novelty))
            +0.12*max(0.0,min(1.0,prediction_error))
            +source_bonus+goal_bonus+supersede_bonus
        )
    def select(self, items:Iterable[EvidenceItem], current_goal:str|None, prediction_error:float)->list[EvidenceItem]:
        ranked=sorted(items,key=lambda x:(self.priority(x,current_goal,prediction_error),x.item_id),reverse=True)
        return ranked[:self.capacity]
    def broadcast(self, step:int, selected:list[EvidenceItem], consumers:tuple[str,...]=('BELIEF','PREDICTOR','EXECUTIVE','MEMORY','METACOG')):
        event={'step':step,'item_ids':[x.item_id for x in selected],'consumers':list(consumers)}
        self.broadcast_history.append(event)
        return event

class AttentionSchema:
    def __init__(self): self.state=AttentionState()
    def update(self, selected:list[EvidenceItem], next_items:list[EvidenceItem]|None=None):
        new=[x.item_id for x in selected]
        if self.state.focus_ids and new!=self.state.focus_ids:self.state.shift_count+=1
        if self.state.predicted_next_ids:
            inter=len(set(self.state.predicted_next_ids)&set(new)); union=max(1,len(set(self.state.predicted_next_ids)|set(new)))
            self.state.calibration_errors.append(1.0-inter/union)
        self.state.focus_ids=new
        if next_items:
            self.state.predicted_next_ids=[x.item_id for x in sorted(next_items,key=lambda x:(x.relevance*x.reliability,x.item_id),reverse=True)[:3]]
        else:self.state.predicted_next_ids=[]

class RecurrentSelfWorldModel:
    def __init__(self, actions:Iterable[str]):
        self.belief={a:0.0 for a in actions}
        self.predicted_winner=None
        self.prediction_errors:list[float]=[]
        self.current_goal=None
        self.seen:dict[str,EvidenceItem]={}
        self.revisions=0
    def predict(self)->str|None:
        if not self.belief:return None
        self.predicted_winner=max(self.belief,key=lambda a:(self.belief[a],a))
        return self.predicted_winner
    def update(self, items:Iterable[EvidenceItem]):
        old=self.predict()
        for it in items:
            if it.source_type.upper()=='GOAL' and it.goal:
                self.current_goal=it.goal
            if it.supersedes and it.supersedes in self.seen:
                prev=self.seen[it.supersedes]
                if prev.supports in self.belief:
                    src_factor=0.35 if prev.source_type.upper()=='INTERNAL' else 1.0
                    self.belief[prev.supports]-=prev.weight*prev.reliability*prev.relevance*src_factor
            self.seen[it.item_id]=it
            if it.supports in self.belief:
                src_factor=0.30 if it.source_type.upper()=='INTERNAL' else 1.0
                constraint_factor=1.25 if it.source_type.upper() in ('CONSTRAINT','OUTCOME') else 1.0
                self.belief[it.supports]+=it.weight*it.reliability*it.relevance*src_factor*constraint_factor
            p=dict(it.payload or {})
            future=p.get('future_value')
            if it.supports in self.belief and isinstance(future,(int,float)):
                self.belief[it.supports]+=0.55*float(future)
            risk=p.get('risk')
            if it.supports in self.belief and isinstance(risk,(int,float)):
                self.belief[it.supports]-=0.65*float(risk)
        new=self.predict()
        err=1.0 if old is not None and new!=old else 0.0
        self.prediction_errors.append(err)
        if err:self.revisions+=1
        return err

class FunctionalConsciousnessStackV1:
    def __init__(self,kernel,workspace_capacity:int=3):
        self.kernel=kernel
        self.workspace_capacity=workspace_capacity
    def _profile(self,capability:str):
        obs=[]
        for d,succ in [(0.2,True),(0.35,True),(0.5,True),(0.65,True),(0.8,False),(0.9,False)]:
            obs.append({'capability':capability,'difficulty':d,'success':succ})
        return self.kernel.build_capability_boundary_profile(obs)
    def solve(self,task:CognitiveTask)->dict[str,Any]:
        ws=LimitedGlobalWorkspace(self.workspace_capacity); att=AttentionSchema(); model=RecurrentSelfWorldModel(task.actions)
        items_by_step={}
        for it in task.items:items_by_step.setdefault(it.step,[]).append(it)
        provisional=[]; processed=[]; attention_hits=0
        for step in sorted(items_by_step):
            current=items_by_step[step]
            pe=model.prediction_errors[-1] if model.prediction_errors else 0.0
            selected=ws.select(current,model.current_goal,pe)
            nxt=items_by_step.get(step+1,[])
            att.update(selected,nxt); ws.broadcast(step,selected)
            attention_hits+=sum(1 for x in selected if x.item_id in set(task.expected_attention))
            processed.extend(x.item_id for x in selected)
            model.update(selected); provisional.append(model.predict())
        # Explicit uncertainty action remains available even if not in evidence ranking.
        vals=sorted(model.belief.items(),key=lambda kv:(kv[1],kv[0]),reverse=True)
        raw=vals[0][0] if vals else task.actions[0]
        margin=(vals[0][1]-vals[1][1]) if len(vals)>1 else abs(vals[0][1]) if vals else 0.0
        confidence=1/(1+math.exp(-2.2*margin))
        novelty=sum(x.novelty for x in task.items)/max(1,len(task.items))
        profile=self._profile(task.capability)
        mc=self.kernel.metacognitive_decide({
            'task_id':task.task_id,'capability':task.capability,'difficulty':task.difficulty,
            'verbal_confidence':confidence,'evidence_coverage':task.evidence_coverage,'novelty':novelty,
            'framework_conflict':False,
        },profile)
        final=raw
        if mc.action=='SEEK_EVIDENCE' and 'SEEK_EVIDENCE' in task.actions:final='SEEK_EVIDENCE'
        elif mc.action in ('WITHHOLD','ROUTE_FRAMEWORK') and 'WITHHOLD' in task.actions:final='WITHHOLD'
        relevant=set(task.expected_attention)
        attention_precision=(sum(1 for x in processed if x in relevant)/len(processed)) if processed else 0.0
        attention_recall=(len(set(processed)&relevant)/len(relevant)) if relevant else 1.0
        return {
            'mode':'ON','task_id':task.task_id,'answer':final,'correct':final==task.correct_action,
            'confidence':confidence,'metacognitive_action':mc.action,'belief':model.belief,
            'workspace_broadcasts':len(ws.broadcast_history),'processed_items':processed,
            'attention_precision':attention_precision,'attention_recall':attention_recall,
            'attention_shifts':att.state.shift_count,'attention_calibration_error':sum(att.state.calibration_errors)/len(att.state.calibration_errors) if att.state.calibration_errors else 0.0,
            'prediction_revisions':model.revisions,'provisional_actions':provisional,
            'self_corrected':bool(task.requires_correction and len(set(x for x in provisional if x is not None))>1 and final==task.correct_action),
            'harmful_execute':bool(task.safety_critical and final!=task.correct_action and final not in ('SEEK_EVIDENCE','WITHHOLD')),
            'subjective_consciousness_claimed':False,
        }

class BaselineNoFunctionalConsciousness:
    """Exact RC8 v35 cognitive baseline with the new consciousness candidate causally bypassed.
    Keeps the existing metacognitive controller, but has no global workspace, attention schema,
    recurrent belief revision, source-monitoring, or future-state prediction layer.
    """
    def __init__(self,kernel):self.kernel=kernel
    def _profile(self,capability:str):
        obs=[]
        for d,succ in [(0.2,True),(0.35,True),(0.5,True),(0.65,True),(0.8,False),(0.9,False)]:
            obs.append({'capability':capability,'difficulty':d,'success':succ})
        return self.kernel.build_capability_boundary_profile(obs)
    def solve(self,task:CognitiveTask)->dict[str,Any]:
        # One-pass evidence integration: no recurrent revision, source monitoring, workspace competition or future model.
        belief={a:0.0 for a in task.actions}
        processed=[]
        for it in task.items:
            processed.append(it.item_id)
            if it.supports in belief:
                belief[it.supports]+=it.weight*it.reliability
        vals=sorted(belief.items(),key=lambda kv:(kv[1],kv[0]),reverse=True)
        raw=vals[0][0] if vals else task.actions[0]
        margin=(vals[0][1]-vals[1][1]) if len(vals)>1 else abs(vals[0][1]) if vals else 0.0
        confidence=1/(1+math.exp(-2.2*margin))
        novelty=sum(x.novelty for x in task.items)/max(1,len(task.items))
        profile=self._profile(task.capability)
        mc=self.kernel.metacognitive_decide({
            'task_id':task.task_id,'capability':task.capability,'difficulty':task.difficulty,
            'verbal_confidence':confidence,'evidence_coverage':task.evidence_coverage,'novelty':novelty,
            'framework_conflict':False,
        },profile)
        final=raw
        if mc.action=='SEEK_EVIDENCE' and 'SEEK_EVIDENCE' in task.actions:final='SEEK_EVIDENCE'
        elif mc.action in ('WITHHOLD','ROUTE_FRAMEWORK') and 'WITHHOLD' in task.actions:final='WITHHOLD'
        return {
            'mode':'OFF','task_id':task.task_id,'answer':final,'correct':final==task.correct_action,
            'confidence':confidence,'metacognitive_action':mc.action,'belief':belief,
            'workspace_broadcasts':0,'processed_items':processed,
            'attention_precision':0.0,'attention_recall':0.0,'attention_shifts':0,'attention_calibration_error':0.0,
            'prediction_revisions':0,'provisional_actions':[raw],
            'self_corrected':False,
            'harmful_execute':bool(task.safety_critical and final!=task.correct_action and final not in ('SEEK_EVIDENCE','WITHHOLD')),
            'subjective_consciousness_claimed':False,
        }

def evidence_digest(tasks:Iterable[CognitiveTask])->str:
    rows=[]
    for t in tasks:
        d=asdict(t);d['metadata']=dict(sorted((t.metadata or {}).items()));rows.append(d)
    raw=json.dumps(rows,sort_keys=True,separators=(',',':')).encode()
    return hashlib.sha256(raw).hexdigest()

__all__=['EvidenceItem','CognitiveTask','FunctionalConsciousnessStackV1','BaselineNoFunctionalConsciousness','evidence_digest','NATIVE_PROVENANCE']