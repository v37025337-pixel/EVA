from __future__ import annotations
from copy import deepcopy
from typing import Any,Mapping
from yado_g2_experience_conditioned_cognitive_layer_v4 import G2ExperienceConditionedCognitiveLayerV4
from yado_organ_runtime_native_v1 import tree_predict

class G2ExperienceConditionedCognitiveLayerV5:
    COMPONENT_ID='RUNTIME-G2-EXPERIENCE-CONDITIONED-COGNITIVE-LAYER-V5'
    TASK_ID='LIVE_RESOURCE_EVIDENCE'

    def __init__(self,artifact:Mapping[str,Any]):
        self.artifact=deepcopy(dict(artifact))
        if self.artifact.get('component_id')!=self.COMPONENT_ID:
            raise ValueError('COGNITIVE_LAYER_V5_COMPONENT_ID_MISMATCH')
        parent=self.artifact.get('parent_v4')
        if not isinstance(parent,dict):
            raise ValueError('COGNITIVE_LAYER_V5_PARENT_V4_MISSING')
        self.parent=G2ExperienceConditionedCognitiveLayerV4(parent)
        self.gene=deepcopy(self.artifact.get('live_resource_evidence_gene') or {})
        self.claims=deepcopy(self.gene.get('claims') or {})
        self.model=deepcopy(self.gene.get('conflict_model') or {})
        if self.artifact.get('automatic_canonical_promotion') is not False:
            raise ValueError('COGNITIVE_LAYER_V5_AUTO_PROMOTION_FORBIDDEN')
        if not self.claims or not self.model:
            raise ValueError('COGNITIVE_LAYER_V5_EVIDENCE_GENE_MISSING')

    @staticmethod
    def _features(bundle:Mapping[str,Any])->dict[str,float]:
        vals=list(bundle.get('values') or [])
        distinct=len({str(x.get('value')) for x in vals})
        observed=[float(x.get('observed_at') or 0) for x in vals]
        verified=[bool(x.get('verified_hash')) for x in vals]
        newest=max(observed) if observed else 0.0
        oldest=min(observed) if observed else 0.0
        newest_verified=any(bool(x.get('verified_hash')) and float(x.get('observed_at') or 0)==newest for x in vals)
        return {
          'source_count':float(len(vals)),
          'distinct_value_count':float(distinct),
          'agreement':1.0 if len(vals)>=2 and distinct==1 else 0.0,
          'conflict':1.0 if distinct>=2 else 0.0,
          'freshness_gap_positive':1.0 if newest>oldest else 0.0,
          'newest_verified':1.0 if newest_verified else 0.0,
          'all_verified':1.0 if vals and all(verified) else 0.0,
        }

    def evidence_query(self,source_id:str,path:str)->dict[str,Any]:
        key=str(source_id)+'|'+str(path)
        row=self.claims.get(key)
        if not isinstance(row,dict):
            return {'decision':'SEEK_MORE','answer':None,'source':'LIVE_RESOURCE_EVIDENCE_V1','known':False}
        return {
          'decision':'ANSWER','answer':deepcopy(row.get('value')),'source':'LIVE_RESOURCE_EVIDENCE_V1',
          'known':True,'source_id':source_id,'path':path,'source_sha256':row.get('source_sha256')
        }

    def evidence_resolve(self,bundle:Mapping[str,Any])->dict[str,Any]:
        x=self._features(bundle)
        decision=tree_predict(self.model,x)
        vals=list(bundle.get('values') or [])
        answer=None
        if decision=='ACCEPT' and vals:
            answer=deepcopy(vals[0].get('value'))
        elif decision=='PREFER_NEWER' and vals:
            answer=deepcopy(max(vals,key=lambda z:(float(z.get('observed_at') or 0),str(z.get('source_id') or ''))).get('value'))
        return {'decision':decision,'answer':answer,'features':x,'source':'LIVE_RESOURCE_EVIDENCE_V1'}

    def decide(self,organ,payload):
        p=deepcopy(dict(payload or {}))
        if str(p.get('task_id') or '')==self.TASK_ID:
            mode=str(p.get('mode') or 'QUERY').upper()
            if mode=='QUERY':
                q=self.evidence_query(str(p.get('source_id') or ''),str(p.get('path') or ''))
                return {'decision':q['decision'],'gate':'SPECIALIST_PASS_THROUGH' if q['known'] else 'WITHHOLD',
                        'route_cardinality':'ONE' if q['known'] else 'ZERO','matched_outputs':[q['answer']] if q['known'] else [],
                        'guard_features':{'organ':str(organ).upper(),'task_id':self.TASK_ID,'state_known':q['known']},
                        'answer':q['answer'],'source':q['source']}
            r=self.evidence_resolve(p.get('bundle') or {})
            return {'decision':r['decision'],'gate':'SPECIALIST_PASS_THROUGH' if r['decision']!='WITHHOLD' else 'WITHHOLD',
                    'route_cardinality':'ONE' if r['decision']!='WITHHOLD' else 'ZERO','matched_outputs':[r['answer']] if r['answer'] is not None else [],
                    'guard_features':{'organ':str(organ).upper(),'task_id':self.TASK_ID,'state_known':True},
                    'answer':r['answer'],'features':r['features'],'source':r['source']}
        return self.parent.decide(organ,p)

    def compose(self,signals):
        return self.parent.compose(signals)

    def snapshot(self):
        s=self.parent.snapshot()
        return {
          'schema':'yado.g2.experience_conditioned_cognitive_layer.snapshot.v5',
          'component_id':self.COMPONENT_ID,'status':self.artifact.get('status'),
          'parent_component':self.artifact.get('parent_component'),
          'parent_snapshot':s,
          'live_resource_evidence_gene_id':self.gene.get('gene_id'),
          'claim_count':len(self.claims),
          'live_source_count':self.gene.get('live_source_count'),
          'conflict_family':self.gene.get('conflict_family'),
          'automatic_canonical_promotion':False,
          'semantic_boundary':'V5 ADDS BOUNDED LIVE STRUCTURED-EVIDENCE QUERY AND CONFLICT RESOLUTION TO THE SINGLE COGNITIVE LAYER. V4 REMAINS THE FAIL-CLOSED PARENT. THIS IS OPERATIONAL EVIDENCE COMPREHENSION, NOT SUBJECTIVE CONSCIOUSNESS.'
        }

__all__=['G2ExperienceConditionedCognitiveLayerV5']
