from __future__ import annotations
from pathlib import Path
from typing import Any, Iterable
import copy,hashlib,json,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path.insert(0,str(ROOT))

from yado_evolution_ledger_v2 import validate_ledger_v2
from yado_g2_typed_recurrent_capability_graph_runtime_v1 import G2TypedRecurrentCapabilityGraphRuntimeV1
from yado_g2_contextual_stream_capability_adapter_v1 import ContextualStreamCapabilityAdapterV1

def canon(o:Any)->str:
    return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o:Any)->str:
    return hashlib.sha256(canon(o).encode()).hexdigest()

class UnifiedYADOCoreV1:
    """Single entry point over the current G2 runtime plus read-only legacy experience.

    Important: legacy branches are knowledge/evidence sources only. This class never
    imports code from legacy Git branches. Re-admission requires a separate fresh gate.
    """
    CORE_ID='UNIFIED_YADO_CORE_V1'

    def __init__(self,repo_root:Path|str|None=None):
        self.repo=Path(repo_root) if repo_root else REPO
        self.head=self._load('canonical/yado-main-head-g2.json')
        self.architecture=self._load('canonical/yado-g2-architecture-v1.json')
        self.ledger=self._load('architecture/evolution-ledger.json')
        self.portfolio=self._load('resources/yado-unified-external-resource-portfolio-v1.json')
        self.manifest=self._load('candidates/unified-core-v1/manifest.json')
        self.experience=self._load('candidates/unified-core-v1/experience-registry.json')
        self.shadow_context=self._load('candidates/g2-development/contextual-stream-capability-adapter-v1.json')
        validate_ledger_v2(self.ledger)

    def _load(self,rel:str)->dict[str,Any]:
        return json.loads((self.repo/rel).read_text(encoding='utf-8'))

    def audit(self)->dict[str,Any]:
        branches=self.experience.get('branches',[])
        active=[x for x in branches if x.get('mode')=='ACTIVE_LINEAGE']
        legacy=[x for x in branches if x.get('mode')=='EXPERIENCE_ONLY']
        active_components=set()
        for p in self.manifest.get('planes',[]):
            active_components.update(p.get('active_components',[]))
        checks={
            'core_id':self.manifest.get('core_id')==self.CORE_ID,
            'generation_is_g2':self.head.get('generation_id')=='G2_CANDIDATE_TRCG_V1',
            'one_active_experience_lineage':len(active)==1 and active[0].get('branch')=='yado-architecture-shadow-search',
            'all_other_branches_experience_only':len(legacy)==13 and all(x.get('mode')=='EXPERIENCE_ONLY' for x in legacy),
            'branch_inventory_complete':len(branches)==14,
            'legacy_auto_execution_forbidden':self.experience.get('policy',{}).get('legacy_code_import_forbidden_without_fresh_admission_gate') is True,
            'ledger_head_matches_generation':self.ledger.get('current_head')==self.head.get('generation_id'),
            'ledger_head_digest_matches':self.ledger.get('current_head_digest')==self.head.get('canonical_head_digest'),
            'g2_architecture_canonical':self.architecture.get('canonical_active') is True and self.architecture.get('promotion_applied') is True,
            'experience_registry_bound':self.manifest.get('experience_registry')=='candidates/unified-core-v1/experience-registry.json',
            'raw_grounding_frontier_preserved':self.manifest.get('current_frontier')=='G2_RAW_TASK_REPRESENTATION_AND_GROUNDING_V1',
            'g3_blocked':self.manifest.get('g3_genesis_performed') is False and self.experience.get('policy',{}).get('g3_genesis_blocked') is True,
            'shadow_context_not_smuggled_canonical':self.shadow_context.get('canonical_active') is False,
            'required_active_families_present':all(x in active_components for x in [
                'ALG-CONJUNCTIVE-RULE-INDUCER-V1',
                'ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1',
                'ALG-BUDGETED-STAGE-POLICY-V1',
                'ALG-BOUNDED-CAPABILITY-ROUTER-V1',
                'ALG-NEUTRAL-EVIDENCE-PROFILE-SELECTOR-V1',
                'RESOURCE-PORTFOLIO-V1',
                'RUNTIME-G2-TYPED-RECURRENT-CAPABILITY-GRAPH-V1',
            ]),
        }
        return {
            'core_id':self.CORE_ID,
            'generation':self.head.get('generation_id'),
            'branch_count':len(branches),
            'legacy_experience_count':len(legacy),
            'checks':checks,
            'pass':all(checks.values()),
            'current_frontier':self.manifest.get('current_frontier'),
            'open_deficits':copy.deepcopy(self.ledger.get('open_deficits',[])),
        }

    def experience_search(self,tags:Iterable[str],limit:int=8)->list[dict[str,Any]]:
        wanted={str(x).strip().lower() for x in tags if str(x).strip()}
        rows=[]
        for entry in self.experience.get('branches',[]):
            if entry.get('mode')!='EXPERIENCE_ONLY':
                continue
            hay={str(x).lower() for x in entry.get('tags',[])}
            lessons=' '.join(entry.get('lessons',[])).lower()
            score=len(wanted & hay)
            score+=sum(1 for w in wanted if w and w in lessons)
            if score:
                rows.append({
                    'branch':entry.get('branch'),
                    'role':entry.get('role'),
                    'score':score,
                    'tags':entry.get('tags',[]),
                    'lessons':entry.get('lessons',[]),
                    'evidence':entry.get('evidence',[]),
                    'claim_boundary':entry.get('claim_boundary'),
                })
        rows.sort(key=lambda x:(-x['score'],x['branch']))
        return rows[:max(1,int(limit))]

    def developmental_frontier(self)->dict[str,Any]:
        return {
            'generation':self.head.get('generation_id'),
            'open_deficits':copy.deepcopy(self.ledger.get('open_deficits',[])),
            'manifest_frontier':self.manifest.get('current_frontier'),
            'recommended_experience':self.experience_search(
                ['representation','grounding','workspace','attention','thinking','self_audit'],limit=6
            ),
        }

    def instantiate_runtime(self,router_program,scalar_program,relation_program,enable_shadow_context:bool=True):
        runtime=G2TypedRecurrentCapabilityGraphRuntimeV1(
            self.architecture,router_program,scalar_program,relation_program,self.portfolio
        )
        if enable_shadow_context:
            return ContextualStreamCapabilityAdapterV1(runtime,'BOUNDED_STREAM_CONTEXT_MAP')
        return runtime

    def snapshot(self)->dict[str,Any]:
        audit=self.audit()
        return {
            'schema':'yado.unified_core.snapshot.v1',
            'core_id':self.CORE_ID,
            'generation':self.head.get('generation_id'),
            'head_digest':self.head.get('canonical_head_digest'),
            'architecture_id':self.head.get('architecture_id'),
            'experience_registry_digest':digest(self.experience),
            'manifest_digest':digest(self.manifest),
            'audit':audit,
            'frontier':self.developmental_frontier(),
            'semantic_boundary':'ONE ACTIVE YADO SOFTWARE KERNEL WITH LEGACY BRANCHES AS READ-ONLY EXPERIENCE; NOT AGI OR SUBJECTIVE CONSCIOUSNESS.'
        }

__all__=['UnifiedYADOCoreV1','digest']
