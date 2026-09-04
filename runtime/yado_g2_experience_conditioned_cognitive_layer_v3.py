from __future__ import annotations
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
from typing import Any,Mapping
import hashlib,json,sys

ROOT=Path(__file__).resolve().parent
PKG=ROOT/'yado_rc8_v36'
if str(PKG) not in sys.path: sys.path.insert(0,str(PKG))

from yado_core_v2_1 import RulePredicate,RuleSpec,RuleProgram,BoundedRuleSandbox

def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o): return hashlib.sha256(canon(o).encode()).hexdigest()

class G2ExperienceConditionedCognitiveLayerV3:
    COMPONENT_ID='RUNTIME-G2-EXPERIENCE-CONDITIONED-COGNITIVE-LAYER-V3'

    def __init__(self,artifact:Mapping[str,Any]):
        self.artifact=deepcopy(dict(artifact))
        if self.artifact.get('component_id')!=self.COMPONENT_ID:
            raise ValueError('COGNITIVE_LAYER_COMPONENT_ID_MISMATCH')
        self.logic=self._program(self.artifact['organ_genes']['LOGIC']['program'])
        self.thinking=self._program(self.artifact['organ_genes']['THINKING']['program'])
        self.intelligence=deepcopy(self.artifact['organ_genes']['INTELLIGENCE']['model'])
        self.arbiter=self._program(self.artifact['guard_gene']['program'])
        self._validate()

    @staticmethod
    def _program(raw):
        rules=[]
        for r in raw.get('rules') or []:
            preds=[RulePredicate(**p) for p in r.get('predicates') or []]
            rules.append(RuleSpec(predicates=preds,output=r.get('output'),support=int(r.get('support',0)),confidence=float(r.get('confidence',0))))
        p=RuleProgram(
            program_id=str(raw['program_id']),
            target_capability=str(raw['target_capability']),
            target_organ=str(raw['target_organ']),
            rules=rules,
            default_output=raw.get('default_output'),
            source_digest=str(raw['source_digest']),
            training_count=int(raw.get('training_count',0)),
            status=str(raw.get('status','SHADOW')),
        )
        BoundedRuleSandbox.validate(p)
        return p

    def _validate(self):
        if self.logic.target_organ!='LOGIC': raise ValueError('LOGIC_GENE_BINDING_INVALID')
        if self.thinking.target_organ!='THINKING': raise ValueError('THINKING_GENE_BINDING_INVALID')
        if self.arbiter.target_organ!='CONSCIOUS_WORKSPACE': raise ValueError('ARBITER_GENE_BINDING_INVALID')
        if self.intelligence.get('kind')!='COVERAGE_PRUNED_COMPOSITIONAL_TRIGGER_ROUTER_V3':
            raise ValueError('INTELLIGENCE_MODEL_KIND_INVALID')
        if self.arbiter.default_output!='WITHHOLD': raise ValueError('ARBITER_MUST_FAIL_CLOSED')

    @staticmethod
    def _rule_outputs(program,payload):
        outs=[]
        for r in program.rules:
            if all(BoundedRuleSandbox._match(p,payload) for p in r.predicates):
                if r.output not in outs: outs.append(r.output)
        return outs

    @staticmethod
    def _router_outputs(model,payload):
        outs=[]
        fallback=model.get('fallback_output')
        for out in model.get('outputs') or []:
            if out==fallback: continue
            for r in model.get('triggers',{}).get(out,[]) or []:
                if all(a.get('field') in payload and payload.get(a.get('field'))==a.get('value') for a in r.get('atoms') or []):
                    outs.append(out);break
        return sorted(set(outs),key=str)

    @staticmethod
    def _cardinality(outs):
        n=len({canon(x) for x in outs})
        return 'ZERO' if n==0 else ('ONE' if n==1 else 'MULTI')

    def _arbitrate(self,organ,outs,payload):
        features={
            'route_cardinality':self._cardinality(outs),
            'state_known':bool(payload.get('state_known',True)),
            'organ':str(organ),
        }
        gate=BoundedRuleSandbox.execute(self.arbiter,features)
        if gate=='PASS_THROUGH' and features['state_known'] and len({canon(x) for x in outs})==1:
            return {'decision':outs[0],'gate':gate,'route_cardinality':'ONE','matched_outputs':deepcopy(outs),'guard_features':features}
        return {'decision':'WITHHOLD','gate':gate,'route_cardinality':features['route_cardinality'],'matched_outputs':deepcopy(outs),'guard_features':features}

    def decide_logic(self,payload):
        return self._arbitrate('LOGIC',self._rule_outputs(self.logic,dict(payload)),dict(payload))

    def decide_thinking(self,payload):
        return self._arbitrate('THINKING',self._rule_outputs(self.thinking,dict(payload)),dict(payload))

    def decide_intelligence(self,payload):
        return self._arbitrate('INTELLIGENCE',self._router_outputs(self.intelligence,dict(payload)),dict(payload))

    def decide(self,organ,payload):
        organ=str(organ).upper()
        if organ=='LOGIC': return self.decide_logic(payload)
        if organ=='THINKING': return self.decide_thinking(payload)
        if organ=='INTELLIGENCE': return self.decide_intelligence(payload)
        return {'decision':'WITHHOLD','gate':'WITHHOLD','route_cardinality':'ZERO','matched_outputs':[],'guard_features':{'route_cardinality':'ZERO','state_known':bool(dict(payload).get('state_known',True)),'organ':organ}}

    def snapshot(self):
        return {
          'schema':'yado.g2.experience_conditioned_cognitive_layer.snapshot.v3',
          'component_id':self.COMPONENT_ID,
          'status':self.artifact.get('status'),
          'cognitive_gene_id':self.artifact.get('cognitive_gene_id'),
          'guard_gene_id':self.artifact.get('guard_gene_id'),
          'organ_gene_ids':{
            k:self.artifact.get('organ_genes',{}).get(k,{}).get('gene_id')
            for k in ('LOGIC','THINKING','INTELLIGENCE')
          },
          'fresh_gate_receipt_sha256':self.artifact.get('fresh_gate_receipt_sha256'),
          'rollback_parent_capabilities':deepcopy(self.artifact.get('rollback_parent_capabilities')),
          'automatic_canonical_promotion':False,
          'semantic_boundary':'BOUNDED EXPERIENCE-CONDITIONED CONTROL LAYER WITH LEARNED FAIL-CLOSED CONFLICT ARBITRATION; NOT GENERAL INTELLIGENCE OR CONSCIOUSNESS.'
        }

    @classmethod
    def component(cls,artifact=None):
        x={
          'schema':'yado.g2.experience_conditioned_cognitive_layer.component.v3',
          'component_id':cls.COMPONENT_ID,
          'family':'EXPERIENCE_CONDITIONED_LTI_WITH_LEARNED_CONFLICT_ARBITRATION',
          'organs':['LOGIC','THINKING','INTELLIGENCE','CONSCIOUS_WORKSPACE'],
          'fail_closed':True,
          'automatic_canonical_promotion':False,
        }
        if artifact:
            x['cognitive_gene_id']=artifact.get('cognitive_gene_id')
            x['guard_gene_id']=artifact.get('guard_gene_id')
            x['artifact_digest']=artifact.get('canonical_component_digest')
        x['component_digest']=digest(x)
        return x

__all__=['G2ExperienceConditionedCognitiveLayerV3']
