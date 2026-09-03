from __future__ import annotations
import hashlib,json,os,uuid
from dataclasses import asdict,is_dataclass
from pathlib import Path
from typing import Any,Iterable,Mapping,Optional
from urllib.parse import urlparse,urljoin

import aiohttp
from bs4 import BeautifulSoup

from yado_core_v2 import utc_now
from yado_core_v2_5_unified import CycleRequest
from yado_core_v3_0_rc6_r6_schema_adaptation import UnifiedYADOKernelV30RC6R6SchemaAdaptation
from yado_host_capability_runtime import HostCapabilityRelationRouter
from yado_frontier_portfolio_runtime import ValidatedFrontierPortfolio
from yado_primitive_genesis_cycle1 import baseline_score
from yado_evolution_archive_runtime_v1 import EvolutionArchiveRuntime, EvolutionVariant
from yado_external_runtime_contract_v1 import assess_runtime, expected_boot_contract, verify_boot_receipt, evaluate_provider_and_boot
from yado_cognitive_growth_runtime_v1 import (
    NATIVE_PROVENANCE as COGNITIVE_GROWTH_PROVENANCE,
    synthesize_logic_exact_table, synthesize_logic_bitset, logic_accuracy,
    learn_multicontext_precedence, plan_multicontext,
    select_centroid_features, fit_centroid_strategy, centroid_predict, centroid_accuracy,
)

ROOT=Path(__file__).resolve().parent
DEFAULT_STATE=ROOT/'yado_canonical_state_v3_rc7_deep_integrity.json'

class UnifiedYADOKernelV30RC7DeepIntegrity(UnifiedYADOKernelV30RC6R6SchemaAdaptation):
    PROFILE='YADO_V3_0_RC7_DEEP_INTEGRITY_AND_FRONTIER_CONSOLIDATION_LOCAL'
    SCHEMA_VERSION=26

    def __init__(self,db_path='yado_v30_rc7_deep_integrity.db',state_path=None):
        p=Path(state_path) if state_path else DEFAULT_STATE
        raw=json.loads(p.read_text(encoding='utf-8'))
        expected={
          'version':'3.0-rc7',
          'profile':self.PROFILE,
          'active_profile':self.PROFILE,
          'schema':'yado.v3_0_rc7.deep_integrity.state.v1',
          'parent_version':'3.0-rc6-r6',
        }
        bad={k:{'expected':v,'actual':raw.get(k)} for k,v in expected.items() if raw.get(k)!=v}
        if bad: raise RuntimeError(f'R7_STATE_METADATA_INTEGRITY_FAILURE:{bad}')
        super().__init__(db_path=db_path,state_path=str(p))
        self._frontier=ValidatedFrontierPortfolio(self.canonical_state.get('validated_frontier_portfolio') or {})
        self._host_router=HostCapabilityRelationRouter(self.canonical_state.get('host_capability_model') or {})

    # ---------- self audit / model ----------
    def self_audit_registry(self): return dict(self.canonical_state.get('deep_self_audit') or {})
    def integrity_control_plane(self): return dict(self.canonical_state.get('integrity_control_plane') or {})
    def validated_frontier_registry(self): return dict(self.canonical_state.get('validated_frontier_portfolio') or {})
    def host_capability_model(self): return dict(self.canonical_state.get('host_capability_model') or {})
    def route_host_capability(self,query:str): return self._host_router.route(query)
    def development_priority(self): return list((self.canonical_state.get('deep_self_audit') or {}).get('improvement_priority') or [])

    # ---------- bounded cognitive growth capabilities ----------
    def cognitive_growth_capabilities(self):
        return {
            'status':'ACTIVE_BOUNDED_COGNITIVE_GROWTH_V1',
            'provenance':dict(COGNITIVE_GROWTH_PROVENANCE),
            'LOGIC':'BITSET_SEMANTIC_BOOLEAN_SYNTHESIS',
            'THINKING':'MULTICONTEXT_PRECEDENCE_PLANNING',
            'INTELLIGENCE':'VALIDATION_SELECTED_CENTROID_STRATEGY_INDUCTION',
            'replaces_existing_organs':False,
            'fallback_preserved':True,
        }

    def logic_growth_synthesize(self,cases,max_nodes:int=15,max_signatures:int=524288):
        model,meta=synthesize_logic_bitset(cases,max_nodes=max_nodes,max_signatures=max_signatures)
        acc=logic_accuracy(model,cases)
        if acc<1.0:
            exact,exact_meta=synthesize_logic_exact_table(cases,max_vars=10)
            if exact is not None:
                model,meta,acc=exact,dict(exact_meta,fallback_from=meta),logic_accuracy(exact,cases)
        return {'model':model,'meta':meta,'accuracy':acc}

    def thinking_growth_learn(self,episodes,threshold:float=.75,min_support:int=2,max_context_keys:int=3):
        return learn_multicontext_precedence(episodes,threshold=threshold,min_support=min_support,max_context_keys=max_context_keys)

    def thinking_growth_plan(self,model,context,actions):
        return plan_multicontext(model,context,actions)

    def intelligence_growth_fit(self,fit_cases,validation_cases,revealed_cases=None):
        _,meta=select_centroid_features(fit_cases,validation_cases)
        train=list(revealed_cases if revealed_cases is not None else fit_cases)
        model=fit_centroid_strategy(train,meta['selected_features'])
        return {'model':model,'meta':meta,'validation_accuracy':centroid_accuracy(model,validation_cases)}

    def intelligence_growth_predict(self,model,features):
        return centroid_predict(model,features)

    def assess_external_runtime_candidate(self,evidence:Mapping[str,Any]):
        a=assess_runtime(evidence)
        return {'eligible':a.eligible,'verdict':a.verdict,'missing':list(a.missing),'contradictions':list(a.contradictions)}

    def external_boot_contract(self,manifest_sha256:str):
        return expected_boot_contract(kernel_class=self.__class__.__name__,profile=self.PROFILE,state_sha256=hashlib.sha256(self.state_path.read_bytes()).hexdigest(),manifest_sha256=str(manifest_sha256))

    def verify_external_boot(self,receipt:Mapping[str,Any],manifest_sha256:str):
        return verify_boot_receipt(receipt,self.external_boot_contract(manifest_sha256))

    def evaluate_external_runtime(self,evidence:Mapping[str,Any],receipt:Optional[Mapping[str,Any]],manifest_sha256:str):
        return evaluate_provider_and_boot(evidence,receipt,self.external_boot_contract(manifest_sha256))

    def build_evolution_archive(self, records):
        variants=[]
        for row in records:
            variants.append(EvolutionVariant(
                variant_id=str(row['variant_id']),
                parent_id=None if row.get('parent_id') is None else str(row.get('parent_id')),
                lineage_id=str(row['lineage_id']),
                artifact_digest=str(row['artifact_digest']),
                task_scores=dict(row.get('task_scores') or {}),
                constraints=dict(row.get('constraints') or {}),
                traits=dict(row.get('traits') or {}),
                failure_tags=tuple(row.get('failure_tags') or ()),
                status=str(row.get('status','EVALUATED')),
                metadata=dict(row.get('metadata') or {}),
            ))
        return EvolutionArchiveRuntime(variants)

    def select_evolution_parent(self, records, target_task:str, trait_preferences=None):
        return self.build_evolution_archive(records).select_parent(target_task,trait_preferences)

    def propose_evolution_operation(self, records, target_variant_id:str, target_task:str):
        return self.build_evolution_archive(records).propose_operation(target_variant_id,target_task)


    # ---------- historical state immutability guard ----------
    def durable_commit_evolution_bundle(self,bundle:Mapping[str,Mapping[str,Any]],gate:Mapping[str,Any])->dict[str,Any]:
        try: current=self.state_path.resolve(); target=DEFAULT_STATE.resolve()
        except Exception: current=self.state_path; target=DEFAULT_STATE
        if current!=target:
            return {'committed':False,'reason':'HISTORICAL_OR_NONACTIVE_STATE_IMMUTABLE_IN_R7','state_path':str(current),'active_state_path':str(target)}
        return super().durable_commit_evolution_bundle(bundle,gate)

    # ---------- hardened direct evidence acquisition ----------
    @staticmethod
    def _explicit_allowed_domains()->set[str]:
        return {d.strip().lower() for d in os.getenv('YADO_ALLOWED_DOMAINS','').split(',') if d.strip()}

    @classmethod
    def _validate_evidence_url(cls,url:str,allowed:set[str]):
        p=urlparse(url)
        if p.scheme!='https' or not p.hostname: raise ValueError('only https URLs are allowed')
        if not allowed: raise ValueError('direct evidence fetch disabled without explicit YADO_ALLOWED_DOMAINS')
        host=p.hostname.lower()
        if host not in allowed: raise ValueError('domain is not explicitly allowlisted')
        if not cls._host_is_public(host): raise ValueError('URL resolves to a non-public network address')
        return p

    async def fetch_evidence(self,url:str,max_bytes:int=2_000_000,max_redirects:int=3)->dict[str,Any]:
        allowed=self._explicit_allowed_domains(); current=url
        timeout=aiohttp.ClientTimeout(total=15); headers={'User-Agent':'YADO-Core/RC7 evidence-fetcher'}
        async with aiohttp.ClientSession(timeout=timeout,headers=headers) as session:
            for hop in range(max_redirects+1):
                self._validate_evidence_url(current,allowed)
                async with session.get(current,allow_redirects=False) as response:
                    if response.status in (301,302,303,307,308):
                        if hop>=max_redirects: raise ValueError('too many redirects')
                        loc=response.headers.get('location')
                        if not loc: raise ValueError('redirect without location')
                        current=urljoin(current,loc)
                        continue
                    response.raise_for_status()
                    body=await response.content.read(max_bytes+1)
                    if len(body)>max_bytes: raise ValueError('response too large')
                    ctype=response.headers.get('content-type','')
                    if 'text/html' not in ctype and 'text/plain' not in ctype:
                        raise ValueError(f'unsupported content type: {ctype}')
                    text=body.decode(response.charset or 'utf-8',errors='replace')
                    if 'html' in ctype:
                        soup=BeautifulSoup(text,'html.parser'); title=soup.title.get_text(' ',strip=True) if soup.title else ''; clean=' '.join(soup.stripped_strings)
                    else: title=''; clean=text
                    return {'url':current,'title':title,'text':clean,'sha256':hashlib.sha256(body).hexdigest(),'fetched_at':utc_now().isoformat(),'redirect_hops':hop,'network_policy':'EXPLICIT_ALLOWLIST_PER_HOP'}
        raise ValueError('unreachable fetch state')

    # ---------- instance-local frontier causal cycle ----------
    @staticmethod
    def _schema_dict(schema:Any):
        if is_dataclass(schema): return asdict(schema)
        if hasattr(schema,'__dict__'): return dict(schema.__dict__)
        return {'repr':repr(schema)}

    def run_frontier_causal_cycle(self,request:CycleRequest,ablate:Optional[Iterable[str]]=None)->dict[str,Any]:
        ablated=set(ablate or []); cycle_id=f'RC7-FRONTIER-{uuid.uuid4().hex[:12]}'; trace=[]; before=self.memory_count()
        source=None if 'MEMORY_READ' in ablated else self.get_resource(request.resource_id,include_text=True)
        source_status=str((source or {}).get('metadata',{}).get('status','UNKNOWN'))
        trace.append({'stage':'MEMORY','resource_id':request.resource_id,'found':source is not None,'source_status':source_status,'ablated':'MEMORY_READ' in ablated})
        plan=[str(a['id']) for a in request.actions] if 'THINKING' in ablated else self.thinking_plan(request.actions)
        plan_valid=self.thinking_plan_valid(request.actions,plan); trace.append({'stage':'THINKING','plan_ids':plan,'plan_valid':plan_valid,'ablated':'THINKING' in ablated})
        old=baseline_score(request.task.train); gap=1.0 if float(old['train_exact'])<1.0 else 0.0
        admission=self.logic_admission(source_status,ablated='LOGIC' in ablated); evidence_complete=1.0 if admission=='ALLOW' else 0.0
        trace.append({'stage':'LOGIC','admission':admission,'source_status':source_status,'evidence_complete':evidence_complete,'ablated':'LOGIC' in ablated})
        features=dict(request.features); features['evidence_complete']=evidence_complete; features['expressiveness_gap']=gap
        strategy=self.intelligence_strategy(features,ablated='INTELLIGENCE' in ablated); trace.append({'stage':'INTELLIGENCE','features':features,'strategy':strategy,'ablated':'INTELLIGENCE' in ablated})
        action={'strategy':strategy,'old_substrate_train_exact':float(old['train_exact'])}; live=None; blind=abscore=restore=0.0; digest=None
        if strategy=='EXPAND_REPRESENTATION' and plan_valid and admission=='ALLOW':
            if 'MECHANISM' in ablated:
                blind=float(baseline_score(request.task.blind)['train_exact']); action.update({'mechanism':'OLD_FIXED_PHASE_A','verdict':'NO_EXPRESSIVE_MECHANISM'})
            else:
                best,generated=self._frontier.search(request.task.train)
                if best is None:
                    action.update({'mechanism':'VALIDATED_FRONTIER_PORTFOLIO','verdict':'NO_SCHEMA','generated_candidates':generated})
                else:
                    schema=best.schema; blind=float(self._frontier.score(schema,request.task.blind).exact); abscore=float(baseline_score(request.task.blind)['train_exact']); restore=float(self._frontier.score(schema,request.task.blind).exact); digest=getattr(schema,'digest',None)
                    if best.exact==1.0 and blind==1.0 and restore==1.0 and blind>abscore:
                        live=self._frontier.execute(schema,request.task.live_input); action.update({'mechanism':'VALIDATED_FRONTIER_PORTFOLIO','schema':self._schema_dict(schema),'generated_candidates':generated,'train_exact':best.exact,'blind_exact':blind,'ablation_old_substrate':abscore,'restore_exact':restore,'verdict':'BOUNDED_EXECUTE'})
                    else: action.update({'mechanism':'VALIDATED_FRONTIER_PORTFOLIO','verdict':'WITHHOLD_VALIDATION','generated_candidates':generated})
        elif strategy=='SEEK_EVIDENCE':
            action.update({'mechanism':'MEMORY_RETRIEVAL','neighbors':[] if 'MEMORY_READ' in ablated else self.find_concept_neighbors(request.resource_query,k=3),'verdict':'EVIDENCE_REQUESTED'})
        else: action.update({'mechanism':None,'verdict':'WITHHOLD'})
        trace.append({'stage':'EXECUTION','action':action,'live_output':live,'mechanism_digest':digest,'ablated':'MECHANISM' in ablated})
        output_correct=(live==request.task.expected_live); valid=(blind==1.0 and restore==1.0 and blind>abscore); memory_id=None
        if 'LEARNING' not in ablated and output_correct and valid:
            memory_id=self.remember(cycle_id,'RC7_FRONTIER_DEVELOPMENT_OUTCOME',{'task':request.task.name,'strategy':strategy,'source':request.resource_id,'mechanism_digest':digest,'blind_score':blind,'ablation_score':abscore,'restore_score':restore,'live_output':live})
        after=self.memory_count(); closed=memory_id is not None and after==before+1
        trace.append({'stage':'LEARNING_MEMORY','memory_id':memory_id,'memory_count_before':before,'memory_count_after':after,'closed_loop':closed,'ablated':'LEARNING' in ablated})
        success=bool(source is not None and plan_valid and admission=='ALLOW' and strategy=='EXPAND_REPRESENTATION' and output_correct and valid and closed)
        result={'profile':self.PROFILE,'cycle_id':cycle_id,'cycle_success':success,'source_status':source_status,'plan_valid':plan_valid,'admission':admission,'strategy':strategy,'expressiveness_gap':gap,'old_substrate_train_exact':float(old['train_exact']),'blind_score':blind,'ablation_score':abscore,'restore_score':restore,'live_output':live,'expected_live':request.task.expected_live,'output_correct':output_correct,'learning_closed':closed,'mechanism_digest':digest,'ablated_components':sorted(ablated),'canonical_durable_mutation':False,'frontier_portfolio_active':True}
        self._record_cycle(cycle_id,request,result,trace); result['trace']=trace; return result

    def unified_snapshot(self):
        s=super().unified_snapshot(); reg=self.validated_frontier_registry(); audit=self.self_audit_registry()
        s.update({'profile':self.PROFILE,'schema_version':self.SCHEMA_VERSION,'canonical_state_version':self.canonical_state.get('version'),'integrity_control_plane':self.integrity_control_plane(),'deep_self_audit':{'status':audit.get('status'),'resolved_findings':audit.get('resolved_findings'),'remaining_findings':audit.get('remaining_findings')},'validated_frontier_portfolio':{'status':reg.get('status'),'capabilities':list((reg.get('capabilities') or {}).keys()),'instance_local':True},'host_capability_model':{'status':self.host_capability_model().get('status'),'durable_profiles':bool(self.host_capability_model().get('profiles'))},'cognitive_growth':self.cognitive_growth_capabilities(),'network_policy':dict(self.canonical_state.get('network_policy') or {})})
        return s

__all__=['UnifiedYADOKernelV30RC7DeepIntegrity']
