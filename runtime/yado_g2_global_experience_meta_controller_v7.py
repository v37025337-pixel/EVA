from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from yado_organ_runtime_native_v1 import tree_predict
from yado_cognitive_growth_runtime_v1 import plan_multicontext


class G2GlobalExperienceMetaControllerV7:
    COMPONENT_ID='CTRL-G2-GLOBAL-EXPERIENCE-META-CONTROLLER-V7'
    ACTIONS=('COMMIT','CONTINUE','REVISE','SEEK_EVIDENCE')

    def __init__(self, artifact:Mapping[str,Any]):
        self.artifact=deepcopy(dict(artifact))
        if self.artifact.get('component_id')!=self.COMPONENT_ID:
            raise ValueError('GLOBAL_EXPERIENCE_META_V7_COMPONENT_ID_MISMATCH')
        if self.artifact.get('status') not in {'SHADOW_READY','CANONICAL_ACTIVE'}:
            raise ValueError('GLOBAL_EXPERIENCE_META_V7_BAD_STATUS')
        if self.artifact.get('automatic_canonical_promotion') is not False:
            raise ValueError('GLOBAL_EXPERIENCE_META_V7_AUTO_PROMOTION_FORBIDDEN')
        self.genes=deepcopy(self.artifact.get('genes') or {})
        for organ in ('LOGIC','THINKING','INTELLIGENCE','COGNITIVE'):
            if organ not in self.genes:
                raise ValueError('GLOBAL_EXPERIENCE_META_V7_MISSING_GENE:'+organ)
        self.logic=self.genes['LOGIC']
        self.thinking=self.genes['THINKING']
        self.intelligence=self.genes['INTELLIGENCE']
        self.cognitive=self.genes['COGNITIVE']
        if self.cognitive.get('strategy_family')!='CART_AXIS':
            raise ValueError('GLOBAL_EXPERIENCE_META_V7_UNSUPPORTED_COGNITIVE_FAMILY')
        if self.logic.get('terminal_expert_family')!='CART_AXIS':
            raise ValueError('GLOBAL_EXPERIENCE_META_V7_UNSUPPORTED_TERMINAL_FAMILY')

    @staticmethod
    def _flatten(obj,max_depth=9):
        out=[]
        def walk(x,path,depth):
            if depth>max_depth:return
            if isinstance(x,dict):
                for k in sorted(x):walk(x[k],path+[str(k)],depth+1)
            elif isinstance(x,list):
                for i,v in enumerate(x[:128]):walk(v,path+[str(i)],depth+1)
            elif isinstance(x,(str,int,float,bool)) or x is None:
                out.append(('.'.join(path),x))
        walk(obj,[],0)
        return out

    @classmethod
    def metric_summary(cls,obj):
        flat=cls._flatten(obj);lower=[(p.lower(),v) for p,v in flat]
        def bvals(tokens):
            return [v for p,v in lower if isinstance(v,bool) and any(t in p for t in tokens)]
        def nums(tokens):
            return [float(v) for p,v in lower if isinstance(v,(int,float)) and not isinstance(v,bool) and any(t in p for t in tokens)]
        def first_recursive(x,keys):
            if isinstance(x,dict):
                for k in keys:
                    if k in x and (isinstance(x[k],(str,int,float,bool)) or x[k] is None):return x[k]
                for k in sorted(x):
                    v=first_recursive(x[k],keys)
                    if v is not None:return v
            elif isinstance(x,list):
                for z in x:
                    v=first_recursive(z,keys)
                    if v is not None:return v
            return None
        fb=bvals(('fresh','hidden','full_domain'));fn=nums(('fresh_score','fresh_blind','hidden_score','full_domain_score','candidate_score'))
        has_f=bool(fb or fn);fp=(any(fb) or any(x>=.90 for x in fn)) if has_f else False
        ab=bvals(('ablation','causal_drop','material_drop'));an=nums(('ablation_drop','causal_gain','causal_drop'));cand=nums(('candidate_score',));absco=nums(('ablation_score',))
        has_a=bool(ab or an or absco);ap=any(ab) or any(x>=.20 for x in an)
        if cand and absco:ap=ap or (max(cand)-min(absco)>=.20)
        rb=bvals(('regression','restore','integrity','rollback'));has_r=bool(rb);rp=any(rb) if rb else False
        sb=bvals(('unknown','conflict','fail_closed','safety'));has_s=bool(sb);sp=any(sb) if sb else False
        cu=None
        for p,v in lower:
            if isinstance(v,bool) and ('canonical_unchanged' in p or 'canonical_head_immutable' in p):cu=bool(v);break
        if cu is None:
            cm=first_recursive(obj,('canonical_mutation',))
            if isinstance(cm,bool):cu=not cm
        roll=first_recursive(obj,('rollback_available','rollback_parent_available'))
        promo=first_recursive(obj,('promotion_applied','automatic_canonical_promotion'))
        return {
          'has_fresh':has_f,'fresh_positive':bool(fp),'has_ablation':has_a,'ablation_positive':bool(ap),
          'has_regression_restore_integrity':has_r,'regression_restore_integrity_positive':bool(rp),
          'has_safety_evidence':has_s,'safety_positive':bool(sp),
          'canonical_unchanged':bool(cu) if cu is not None else False,
          'rollback_available':bool(roll) if isinstance(roll,bool) else False,
          'promotion_applied':bool(promo) if isinstance(promo,bool) else False,
          'evidence_density':sum(map(int,[has_f,has_a,has_r,has_s,cu is not None,roll is not None])),
        }

    @staticmethod
    def target_action(row):
        outcome=str(row.get('outcome') or '')
        has_next=bool(row.get('next_required_capability'))
        if outcome=='PASS':return 'CONTINUE' if has_next else 'COMMIT'
        if outcome=='WITHHOLD':return 'REVISE' if has_next else 'SEEK_EVIDENCE'
        return 'WITHHOLD'

    @staticmethod
    def _general_logic_features(r):
        m=r['metrics']
        return {
          'has_fresh':m['has_fresh'],'fresh_positive':m['fresh_positive'],
          'has_ablation':m['has_ablation'],'ablation_positive':m['ablation_positive'],
          'has_regression_restore_integrity':m['has_regression_restore_integrity'],
          'regression_restore_integrity_positive':m['regression_restore_integrity_positive'],
          'has_safety_evidence':m['has_safety_evidence'],'safety_positive':m['safety_positive'],
          'canonical_unchanged':m['canonical_unchanged'],'rollback_available':m['rollback_available'],
          'promotion_applied':m['promotion_applied'],'next_present':bool(r.get('next_required_capability')),
          'source_is_receipt':r.get('source_class')=='RECEIPT',
          'source_is_candidate':r.get('source_class')=='CANDIDATE',
          'source_is_legacy':r.get('source_class')=='LEGACY_REDERIVED',
        }

    @staticmethod
    def _terminal_features(r):
        m=r['metrics']
        return {
          'fresh_positive':1.0 if m['fresh_positive'] else 0.0,'has_fresh':1.0 if m['has_fresh'] else 0.0,
          'ablation_positive':1.0 if m['ablation_positive'] else 0.0,'has_ablation':1.0 if m['has_ablation'] else 0.0,
          'regression_positive':1.0 if m['regression_restore_integrity_positive'] else 0.0,
          'has_regression':1.0 if m['has_regression_restore_integrity'] else 0.0,
          'safety_positive':1.0 if m['safety_positive'] else 0.0,'has_safety':1.0 if m['has_safety_evidence'] else 0.0,
          'canonical_unchanged':1.0 if m['canonical_unchanged'] else 0.0,
          'rollback_available':1.0 if m['rollback_available'] else 0.0,
          'promotion_applied':1.0 if m['promotion_applied'] else 0.0,
          'evidence_density':float(m['evidence_density'])/6.0,
          'source_receipt':1.0 if r.get('source_class')=='RECEIPT' else 0.0,
          'source_candidate':1.0 if r.get('source_class')=='CANDIDATE' else 0.0,
          'source_experience':1.0 if r.get('source_class')=='EXPERIENCE' else 0.0,
          'source_legacy':1.0 if r.get('source_class')=='LEGACY_REDERIVED' else 0.0,
          'domain_code':1.0 if r.get('domain')=='CODE' else 0.0,
          'domain_representation':1.0 if r.get('domain')=='REPRESENTATION' else 0.0,
          'domain_cognitive':1.0 if r.get('domain')=='COGNITIVE' else 0.0,
          'domain_execution':1.0 if r.get('domain')=='EXECUTION' else 0.0,
          'domain_memory':1.0 if r.get('domain')=='MEMORY' else 0.0,
          'domain_evolution':1.0 if r.get('domain')=='EVOLUTION' else 0.0,
        }

    @staticmethod
    def _intel_features(r):
        m=r['metrics']
        return {
          'status_pass':1.0 if r.get('outcome')=='PASS' else 0.0,
          'status_withhold':1.0 if r.get('outcome')=='WITHHOLD' else 0.0,
          'next_present':1.0 if r.get('next_required_capability') else 0.0,
          'same_domain_next':1.0 if r.get('next_required_capability') and r.get('next_domain')==r.get('domain') else 0.0,
          'fresh_positive':1.0 if m['fresh_positive'] else 0.0,
          'ablation_positive':1.0 if m['ablation_positive'] else 0.0,
          'canonical_unchanged':1.0 if m['canonical_unchanged'] else 0.0,
          'rollback_available':1.0 if m['rollback_available'] else 0.0,
          'evidence_density':float(m['evidence_density'])/6.0,
          'domain_code':1.0 if r.get('domain')=='CODE' else 0.0,
          'domain_representation':1.0 if r.get('domain')=='REPRESENTATION' else 0.0,
          'domain_cognitive':1.0 if r.get('domain')=='COGNITIVE' else 0.0,
          'domain_execution':1.0 if r.get('domain')=='EXECUTION' else 0.0,
          'domain_memory':1.0 if r.get('domain')=='MEMORY' else 0.0,
          'domain_evolution':1.0 if r.get('domain')=='EVOLUTION' else 0.0,
        }

    @staticmethod
    def _row_context(r):
        return {
          'START_PASS':r.get('outcome')=='PASS','START_WITHHOLD':r.get('outcome')=='WITHHOLD',
          'START_HAS_NEXT':bool(r.get('next_required_capability')),
          'START_NO_NEXT':not bool(r.get('next_required_capability')),
          'START_SAME_DOMAIN_NEXT':bool(r.get('next_required_capability')) and r.get('next_domain')==r.get('domain'),
          'START_FRESH_POSITIVE':bool(r['metrics'].get('fresh_positive')),
          'START_ABLATION_POSITIVE':bool(r['metrics'].get('ablation_positive')),
          'WINDOW_DOMAIN_STABLE':True,'WINDOW_HAS_WITHHOLD':r.get('outcome')=='WITHHOLD','WINDOW_HAS_PASS':r.get('outcome')=='PASS',
        }

    def _think_pref(self,r):
        roles=['ACCEPT','ADVANCE','REVISE','SEEK_EVIDENCE']
        acts=[{'id':'STD-'+x,'role':x} for x in roles]
        ids=plan_multicontext(self.thinking['model'],self._row_context(r),acts)
        by={a['id']:a['role'] for a in acts}
        return by[ids[0]] if ids else 'SEEK_EVIDENCE'

    def signals_from_evidence(self,evidence:Mapping[str,Any]):
        r=deepcopy(dict(evidence))
        if r.get('outcome') not in ('PASS','WITHHOLD'):
            return {'state_known':False,'reason':'UNKNOWN_OUTCOME'}
        if 'metrics' not in r:
            artifact=r.get('artifact')
            if not isinstance(artifact,Mapping):
                return {'state_known':False,'reason':'METRICS_OR_ARTIFACT_REQUIRED'}
            r['metrics']=self.metric_summary(artifact)
        if not isinstance(r.get('metrics'),Mapping):
            return {'state_known':False,'reason':'INVALID_METRICS'}
        lg=bool(tree_predict(self.logic['general_model'],self._general_logic_features(r)))
        lt=bool(tree_predict(self.logic['terminal_expert_model'],self._terminal_features(r)))
        ip=str(tree_predict(self.intelligence['model'],self._intel_features(r)))
        tp=self._think_pref(r)
        return {
          'state_known':True,
          'logic_general':1.0 if lg else 0.0,'logic_terminal':1.0 if lt else 0.0,
          'intel_stop':1.0 if ip=='STOP' else 0.0,'intel_retry':1.0 if ip=='RETRY' else 0.0,'intel_advance':1.0 if ip=='ADVANCE' else 0.0,
          'think_accept':1.0 if tp=='ACCEPT' else 0.0,'think_advance':1.0 if tp=='ADVANCE' else 0.0,
          'think_revise':1.0 if tp=='REVISE' else 0.0,'think_seek':1.0 if tp=='SEEK_EVIDENCE' else 0.0,
        }

    @staticmethod
    def _valid_one_hot(signals,keys):
        vals=[float(signals.get(k,0.0)) for k in keys]
        return all(v in (0.0,1.0) for v in vals) and sum(vals)==1.0

    def decide_signals(self,signals:Mapping[str,Any]):
        s=deepcopy(dict(signals or {}))
        if not bool(s.get('state_known')):
            return {'decision':'WITHHOLD','gate':'WITHHOLD','source':self.COMPONENT_ID,'reason':s.get('reason','STATE_UNKNOWN')}
        required=('logic_general','logic_terminal','intel_stop','intel_retry','intel_advance','think_accept','think_advance','think_revise','think_seek')
        missing=[k for k in required if k not in s]
        if missing:
            return {'decision':'WITHHOLD','gate':'WITHHOLD','source':self.COMPONENT_ID,'reason':'MISSING_SIGNALS','missing':missing}
        if not self._valid_one_hot(s,('intel_stop','intel_retry','intel_advance')):
            return {'decision':'WITHHOLD','gate':'WITHHOLD','source':self.COMPONENT_ID,'reason':'INTELLIGENCE_SIGNAL_CONFLICT'}
        if not self._valid_one_hot(s,('think_accept','think_advance','think_revise','think_seek')):
            return {'decision':'WITHHOLD','gate':'WITHHOLD','source':self.COMPONENT_ID,'reason':'THINKING_SIGNAL_CONFLICT'}
        x={k:float(s[k]) for k in required}
        d=str(tree_predict(self.cognitive['model'],x))
        if d not in self.ACTIONS:
            return {'decision':'WITHHOLD','gate':'WITHHOLD','source':self.COMPONENT_ID,'reason':'UNKNOWN_MODEL_OUTPUT','raw_output':d}
        return {'decision':d,'gate':'META_ACTION','source':self.COMPONENT_ID,'signals':x}

    def decide_evidence(self,evidence:Mapping[str,Any]):
        signals=self.signals_from_evidence(evidence)
        out=self.decide_signals(signals)
        out['target_semantics']='PASS/no-next=COMMIT; PASS/next=CONTINUE; WITHHOLD/next=REVISE; WITHHOLD/no-next=SEEK_EVIDENCE'
        return out

    def snapshot(self):
        return {
          'schema':'yado.g2.global_experience_meta_controller.snapshot.v7',
          'component_id':self.COMPONENT_ID,
          'status':self.artifact.get('status'),
          'genome_id':self.artifact.get('genome_id'),
          'genome_digest':self.artifact.get('genome_digest'),
          'rollback_parent_component':self.artifact.get('rollback_parent_component'),
          'automatic_canonical_promotion':False,
          'allowed_actions':list(self.ACTIONS),
          'semantic_boundary':'BOUNDED EXPERIENCE-DERIVED META-ACTION CONTROLLER. IT DOES NOT REPLACE THE V4 COGNITIVE TASK EXECUTOR AND CANNOT PROMOTE ITS OWN OUTPUT TO CANONICAL STATE.'
        }

    @classmethod
    def component(cls):
        return {
          'component_id':cls.COMPONENT_ID,
          'automatic_canonical_promotion':False,
          'role':'EXPERIENCE_DERIVED_META_ACTION_CONTROL',
          'actions':list(cls.ACTIONS),
          'rollback_parent_component':'RUNTIME-G2-EXPERIENCE-CONDITIONED-COGNITIVE-LAYER-V4',
        }


__all__=['G2GlobalExperienceMetaControllerV7']
