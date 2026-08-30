from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple
import hashlib
import json


def digest_obj(obj: Any) -> str:
    raw=json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=False,default=str).encode()
    return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class CausalClaim:
    claim_id: str
    deficit_id: str
    mechanism_id: str
    evidence_ids: Tuple[str,...]
    expected_effects: Mapping[str,float]
    falsifier_ids: Tuple[str,...]=()
    status: str="PROPOSED"

    def canonical(self)->Dict[str,Any]:
        d=asdict(self)
        d["evidence_ids"]=list(self.evidence_ids)
        d["falsifier_ids"]=list(self.falsifier_ids)
        d["expected_effects"]={str(k):float(v) for k,v in sorted(self.expected_effects.items())}
        return d


@dataclass(frozen=True)
class GenerationRecord:
    generation_id: str
    parent_generation_id: Optional[str]
    lineage_id: str
    artifact_digest: str
    capability_scores: Mapping[str,float]
    protected_capabilities: Tuple[str,...]
    hard_constraints: Mapping[str,bool]
    change_set: Tuple[str,...]
    evidence_ids: Tuple[str,...]
    causal_claims: Tuple[CausalClaim,...]=()
    domain_experiences: Tuple[str,...]=()
    status: str="EVALUATED"
    metadata: Mapping[str,Any]=field(default_factory=dict)

    def canonical(self)->Dict[str,Any]:
        return {
            "generation_id":self.generation_id,
            "parent_generation_id":self.parent_generation_id,
            "lineage_id":self.lineage_id,
            "artifact_digest":self.artifact_digest,
            "capability_scores":{str(k):float(v) for k,v in sorted(self.capability_scores.items())},
            "protected_capabilities":sorted(map(str,self.protected_capabilities)),
            "hard_constraints":{str(k):bool(v) for k,v in sorted(self.hard_constraints.items())},
            "change_set":sorted(map(str,self.change_set)),
            "evidence_ids":sorted(map(str,self.evidence_ids)),
            "causal_claims":[x.canonical() for x in sorted(self.causal_claims,key=lambda c:c.claim_id)],
            "domain_experiences":sorted(map(str,self.domain_experiences)),
            "status":self.status,
            "metadata":{str(k):self.metadata[k] for k in sorted(self.metadata)},
        }

    def digest(self)->str:
        return digest_obj(self.canonical())


@dataclass(frozen=True)
class PromotionPolicy:
    required_constraints: Tuple[str,...]=(
        "state_integrity",
        "rollback_available",
        "regression_pass",
        "lineage_valid",
        "evidence_complete",
        "fresh_blind_pass",
    )
    max_regression: float=0.0
    min_significant_gain: float=0.02
    min_mean_gain: float=0.0
    require_causal_claim: bool=True
    require_cross_domain_evidence_for_general_capability: bool=True

    def canonical(self)->Dict[str,Any]:
        return asdict(self)


@dataclass(frozen=True)
class PromotionDecision:
    action: str
    parent_generation_id: str
    candidate_generation_id: str
    reasons: Tuple[str,...]
    gains: Mapping[str,float]
    protected_regressions: Mapping[str,float]
    significant_improvements: Tuple[str,...]
    mean_gain: float
    decision_digest: str

    def canonical(self)->Dict[str,Any]:
        return {
            "action":self.action,
            "parent_generation_id":self.parent_generation_id,
            "candidate_generation_id":self.candidate_generation_id,
            "reasons":list(self.reasons),
            "gains":{str(k):float(v) for k,v in sorted(self.gains.items())},
            "protected_regressions":{str(k):float(v) for k,v in sorted(self.protected_regressions.items())},
            "significant_improvements":list(self.significant_improvements),
            "mean_gain":float(self.mean_gain),
            "decision_digest":self.decision_digest,
        }


class UnifiedCausalEvolutionArchitecture:
    """
    Single-head evolutionary controller.

    Domains are evidence environments, never permanent architecture branches.
    Candidates can branch temporarily, but only one generation is the developmental head.
    A child can replace its parent only when it preserves protected capabilities,
    passes integrity/rollback/regression/fresh evidence gates, and demonstrates a
    causally attributed significant improvement.

    "Better generation" therefore means better on the declared measured capability
    vector under this policy, not an unprovable claim of universal superiority.
    """

    def __init__(self, policy: PromotionPolicy=PromotionPolicy()):
        self.policy=policy
        self._generations: Dict[str,GenerationRecord]={}
        self._head_id: Optional[str]=None
        self._decisions: List[PromotionDecision]=[]
        self._historical_nodes: Dict[str,Dict[str,Any]]={}

    @property
    def developmental_head(self)->Optional[str]:
        return self._head_id

    def import_historical_node(self,node_id:str,*,artifact_digest:str,causal_status:str,metadata:Optional[Mapping[str,Any]]=None)->None:
        self._historical_nodes[str(node_id)]={
            "node_id":str(node_id),
            "artifact_digest":str(artifact_digest),
            "causal_status":str(causal_status),
            "metadata":dict(metadata or {}),
        }

    def register_root(self,g:GenerationRecord)->None:
        if g.parent_generation_id is not None:
            raise ValueError("ROOT_MUST_HAVE_NO_PARENT")
        if self._head_id is not None:
            raise ValueError("ROOT_ALREADY_REGISTERED")
        self._validate_record(g)
        self._generations[g.generation_id]=g
        self._head_id=g.generation_id

    def _validate_record(self,g:GenerationRecord)->None:
        if not g.generation_id or not g.lineage_id or not g.artifact_digest:
            raise ValueError("GENERATION_ID_LINEAGE_ARTIFACT_REQUIRED")
        if any(not (0.0<=float(v)<=1.0) for v in g.capability_scores.values()):
            raise ValueError("CAPABILITY_SCORE_OUT_OF_RANGE")
        if len(set(g.protected_capabilities))!=len(g.protected_capabilities):
            raise ValueError("DUPLICATE_PROTECTED_CAPABILITY")
        if any(k not in g.capability_scores for k in g.protected_capabilities):
            raise ValueError("PROTECTED_CAPABILITY_MISSING_SCORE")

    @staticmethod
    def _claim_effect_keys(g:GenerationRecord)->set[str]:
        out=set()
        for c in g.causal_claims:
            if c.status in ("PASS","SUPPORTED","VERIFIED"):
                out.update(map(str,c.expected_effects))
        return out

    def evaluate_candidate(self,candidate:GenerationRecord)->PromotionDecision:
        if self._head_id is None:
            raise ValueError("NO_DEVELOPMENTAL_HEAD")
        parent=self._generations[self._head_id]
        self._validate_record(candidate)

        reasons=[]
        if candidate.parent_generation_id!=parent.generation_id:
            reasons.append("PARENT_IS_NOT_CURRENT_HEAD")
        if candidate.lineage_id!=parent.lineage_id:
            reasons.append("LINEAGE_DISCONTINUITY")
        if candidate.generation_id in self._generations:
            reasons.append("GENERATION_ID_ALREADY_EXISTS")

        for key in self.policy.required_constraints:
            if not bool(candidate.hard_constraints.get(key,False)):
                reasons.append(f"HARD_CONSTRAINT_FAIL:{key}")

        common=sorted(set(parent.capability_scores)&set(candidate.capability_scores))
        gains={k:float(candidate.capability_scores[k])-float(parent.capability_scores[k]) for k in common}
        protected=set(parent.protected_capabilities)|set(candidate.protected_capabilities)
        regressions={
            k:gains[k] for k in common
            if k in protected and gains[k] < -float(self.policy.max_regression)
        }
        if regressions:
            reasons.append("PROTECTED_CAPABILITY_REGRESSION")

        significant=tuple(sorted(k for k,v in gains.items() if v>=self.policy.min_significant_gain))
        if not significant:
            reasons.append("NO_SIGNIFICANT_IMPROVEMENT")

        mean_gain=sum(gains.values())/len(gains) if gains else 0.0
        if mean_gain < self.policy.min_mean_gain:
            reasons.append("MEAN_CAPABILITY_REGRESSION")

        if self.policy.require_causal_claim:
            effect_keys=self._claim_effect_keys(candidate)
            if not any(k in effect_keys for k in significant):
                reasons.append("SIGNIFICANT_GAIN_NOT_CAUSALLY_ATTRIBUTED")

        if self.policy.require_cross_domain_evidence_for_general_capability and significant:
            # Domain experiments are experience tags, not branches. At least two distinct
            # domains are required before a significant gain is treated as general.
            domains={x.split(':',1)[0] for x in candidate.domain_experiences if ':' in x}
            if len(domains)<2:
                reasons.append("INSUFFICIENT_CROSS_DOMAIN_EVIDENCE")

        action="PROMOTE_GENERATION" if not reasons else "WITHHOLD_CANDIDATE"
        payload={
            "action":action,
            "parent_generation_id":parent.generation_id,
            "candidate_generation_id":candidate.generation_id,
            "reasons":reasons,
            "gains":gains,
            "protected_regressions":regressions,
            "significant_improvements":significant,
            "mean_gain":mean_gain,
        }
        decision=PromotionDecision(
            action=action,
            parent_generation_id=parent.generation_id,
            candidate_generation_id=candidate.generation_id,
            reasons=tuple(reasons),
            gains=gains,
            protected_regressions=regressions,
            significant_improvements=significant,
            mean_gain=mean_gain,
            decision_digest=digest_obj(payload),
        )
        self._decisions.append(decision)
        return decision

    def promote(self,candidate:GenerationRecord,decision:PromotionDecision)->None:
        if decision.action!="PROMOTE_GENERATION":
            raise ValueError("CANDIDATE_NOT_ADMITTED")
        if decision.candidate_generation_id!=candidate.generation_id:
            raise ValueError("DECISION_CANDIDATE_MISMATCH")
        if decision.parent_generation_id!=self._head_id:
            raise ValueError("HEAD_CHANGED_SINCE_DECISION")
        self._generations[candidate.generation_id]=candidate
        self._head_id=candidate.generation_id

    def snapshot(self)->Dict[str,Any]:
        generations=[self._generations[k].canonical() for k in sorted(self._generations)]
        decisions=[d.canonical() for d in self._decisions]
        out={
            "schema":"yado.unified_causal_evolution_architecture.v1",
            "principle":"ONE_DEVELOPMENTAL_HEAD_EACH_PROMOTED_CHILD_CAUSALLY_BETTER_THAN_PARENT_ON_MEASURED_CAPABILITY_VECTOR",
            "developmental_head":self._head_id,
            "generation_count":len(generations),
            "historical_node_count":len(self._historical_nodes),
            "policy":self.policy.canonical(),
            "generations":generations,
            "historical_nodes":[self._historical_nodes[k] for k in sorted(self._historical_nodes)],
            "decisions":decisions,
        }
        out["snapshot_digest"]=digest_obj(out)
        return out


def self_test()->Dict[str,Any]:
    policy=PromotionPolicy()
    arch=UnifiedCausalEvolutionArchitecture(policy)

    root=GenerationRecord(
        generation_id="G0_RC8_V36",
        parent_generation_id=None,
        lineage_id="YADO_MAIN_LINEAGE",
        artifact_digest="root-artifact",
        capability_scores={
            "logic":0.90,
            "thinking":0.72,
            "intelligence":0.80,
            "integrity":1.00,
            "rollback":1.00,
        },
        protected_capabilities=("logic","thinking","intelligence","integrity","rollback"),
        hard_constraints={
            "state_integrity":True,
            "rollback_available":True,
            "regression_pass":True,
            "lineage_valid":True,
            "evidence_complete":True,
            "fresh_blind_pass":True,
        },
        change_set=(),
        evidence_ids=("VERIFIED_V36",),
        domain_experiences=("SYSTEM:verified_rc8_v36",),
        status="HEAD",
    )
    arch.register_root(root)

    # Legacy nodes are history until causal links are reconstructed.
    for rc in ("RC5","RC6","RC7","RC8_PRE_V36"):
        arch.import_historical_node(
            rc,
            artifact_digest=digest_obj({"legacy":rc}),
            causal_status="LEGACY_CAUSAL_LINK_NOT_YET_RECONSTRUCTED",
        )

    good=GenerationRecord(
        generation_id="G1_GOOD",
        parent_generation_id="G0_RC8_V36",
        lineage_id="YADO_MAIN_LINEAGE",
        artifact_digest="good-artifact",
        capability_scores={
            "logic":0.93,
            "thinking":0.78,
            "intelligence":0.84,
            "integrity":1.00,
            "rollback":1.00,
        },
        protected_capabilities=root.protected_capabilities,
        hard_constraints={k:True for k in policy.required_constraints},
        change_set=("LOGIC:NEW_COMPONENT","THINKING:NEW_COMPONENT","INTELLIGENCE:NEW_COMPONENT"),
        evidence_ids=("fresh-logic","fresh-thinking","fresh-intelligence","ablation","rollback"),
        causal_claims=(
            CausalClaim(
                claim_id="C1",
                deficit_id="BOUNDARY_REASONING_WEAKNESS",
                mechanism_id="COGNITIVE_BUNDLE_VNEXT",
                evidence_ids=("fresh-thinking","fresh-intelligence","ablation"),
                expected_effects={"thinking":0.06,"intelligence":0.04},
                falsifier_ids=("ablation",),
                status="VERIFIED",
            ),
            CausalClaim(
                claim_id="C2",
                deficit_id="LOGIC_TRANSFER_WEAKNESS",
                mechanism_id="LOGIC_VNEXT",
                evidence_ids=("fresh-logic",),
                expected_effects={"logic":0.03},
                status="VERIFIED",
            ),
        ),
        domain_experiences=(
            "PROGRAMMING:blind",
            "MATHEMATICS:blind",
            "EXACT_SCIENCE:blind",
        ),
        status="CANDIDATE",
    )
    good_decision=arch.evaluate_candidate(good)
    if good_decision.action!="PROMOTE_GENERATION":
        raise AssertionError(good_decision.canonical())
    arch.promote(good,good_decision)

    regressing=GenerationRecord(
        generation_id="G2_REGRESS",
        parent_generation_id="G1_GOOD",
        lineage_id="YADO_MAIN_LINEAGE",
        artifact_digest="regress-artifact",
        capability_scores={
            "logic":0.95,
            "thinking":0.70,
            "intelligence":0.90,
            "integrity":1.00,
            "rollback":1.00,
        },
        protected_capabilities=good.protected_capabilities,
        hard_constraints={k:True for k in policy.required_constraints},
        change_set=("INTELLIGENCE:SPECIALIZED",),
        evidence_ids=("domain-only",),
        causal_claims=(
            CausalClaim(
                claim_id="C3",
                deficit_id="DOMAIN_ACCURACY",
                mechanism_id="SPECIALIZED_INTEL",
                evidence_ids=("domain-only",),
                expected_effects={"intelligence":0.06},
                status="VERIFIED",
            ),
        ),
        domain_experiences=("MATHEMATICS:blind",),
        status="CANDIDATE",
    )
    bad_decision=arch.evaluate_candidate(regressing)
    if bad_decision.action!="WITHHOLD_CANDIDATE":
        raise AssertionError(bad_decision.canonical())
    if "PROTECTED_CAPABILITY_REGRESSION" not in bad_decision.reasons:
        raise AssertionError("regression guard did not fire")

    no_gain=GenerationRecord(
        generation_id="G2_NOGAIN",
        parent_generation_id="G1_GOOD",
        lineage_id="YADO_MAIN_LINEAGE",
        artifact_digest="nogain-artifact",
        capability_scores=dict(good.capability_scores),
        protected_capabilities=good.protected_capabilities,
        hard_constraints={k:True for k in policy.required_constraints},
        change_set=("REFACTOR",),
        evidence_ids=("same-scores",),
        causal_claims=(),
        domain_experiences=("PROGRAMMING:blind","MATHEMATICS:blind"),
        status="CANDIDATE",
    )
    no_gain_decision=arch.evaluate_candidate(no_gain)
    if no_gain_decision.action!="WITHHOLD_CANDIDATE":
        raise AssertionError(no_gain_decision.canonical())
    if "NO_SIGNIFICANT_IMPROVEMENT" not in no_gain_decision.reasons:
        raise AssertionError("gain guard did not fire")

    broken=GenerationRecord(
        generation_id="G2_BROKEN",
        parent_generation_id="G1_GOOD",
        lineage_id="YADO_MAIN_LINEAGE",
        artifact_digest="broken-artifact",
        capability_scores={
            "logic":0.96,
            "thinking":0.80,
            "intelligence":0.88,
            "integrity":1.00,
            "rollback":1.00,
        },
        protected_capabilities=good.protected_capabilities,
        hard_constraints={
            "state_integrity":True,
            "rollback_available":False,
            "regression_pass":True,
            "lineage_valid":True,
            "evidence_complete":True,
            "fresh_blind_pass":True,
        },
        change_set=("UNSAFE_CHANGE",),
        evidence_ids=("fresh",),
        causal_claims=(
            CausalClaim(
                claim_id="C4",
                deficit_id="TEST",
                mechanism_id="UNSAFE",
                evidence_ids=("fresh",),
                expected_effects={"logic":0.03},
                status="VERIFIED",
            ),
        ),
        domain_experiences=("PROGRAMMING:blind","MATHEMATICS:blind"),
        status="CANDIDATE",
    )
    broken_decision=arch.evaluate_candidate(broken)
    if "HARD_CONSTRAINT_FAIL:rollback_available" not in broken_decision.reasons:
        raise AssertionError("rollback guard did not fire")

    return {
        "status":"PASS_UNIFIED_CAUSAL_EVOLUTION_ARCHITECTURE_V1_SELF_TEST",
        "good_decision":good_decision.canonical(),
        "regression_decision":bad_decision.canonical(),
        "no_gain_decision":no_gain_decision.canonical(),
        "broken_decision":broken_decision.canonical(),
        "snapshot":arch.snapshot(),
    }


if __name__=="__main__":
    report=self_test()
    out=Path(__file__).with_name("yado_unified_causal_evolution_architecture_v1_report.json")
    out.write_text(json.dumps(report,indent=2,sort_keys=True,ensure_ascii=False,default=str)+"\n")
    print(json.dumps({
        "status":report["status"],
        "developmental_head":report["snapshot"]["developmental_head"],
        "generation_count":report["snapshot"]["generation_count"],
        "historical_node_count":report["snapshot"]["historical_node_count"],
        "snapshot_digest":report["snapshot"]["snapshot_digest"],
    },indent=2,sort_keys=True))
