from __future__ import annotations
from pathlib import Path
import hashlib, inspect, json, os, sys

ROOT = Path(__file__).resolve().parent
PKG = ROOT / "yado_rc8_v36"
sys.path.insert(0, str(PKG))

import yado_rc8_consciousness_direct_research_v1 as research
from yado_consciousness_theory_synthesis_v1 import TheoryCard, YADOTheorySynthesizer

SOURCES = [
    ("COGARCH_REVIEW_40Y", "https://arxiv.org/abs/1610.08602"),
    ("GLOBAL_WORKSPACE_AGENTS_2026", "https://arxiv.org/abs/2604.08206"),
    ("WORLD_MODELS_COGNITIVE_AGENTS_2025", "https://arxiv.org/abs/2506.00417"),
    ("ACTIVE_INFERENCE_DEEP_2022", "https://arxiv.org/abs/2207.06415"),
    ("NEUROSYMBOLIC_COGNITIVE_AI_2024", "https://arxiv.org/abs/2401.01040"),
    ("OPENCOG_HYPERON_2023", "https://arxiv.org/abs/2310.18318"),
    ("OPEN_ENDED_LENIA_2024", "https://arxiv.org/abs/2406.04235"),
    ("NEURAL_CELLULAR_AUTOMATA_2025", "https://arxiv.org/abs/2509.11131"),
    ("META_NCA_2026", "https://arxiv.org/abs/2607.07743"),
    ("LOCAL_RULES_EMERGENCE_2026", "https://arxiv.org/abs/2604.00273"),
    ("UNIFIED_CONSCIOUS_ARCHITECTURE_2022", "https://arxiv.org/abs/2204.05133"),
    ("LOCAL_GLOBAL_MULTI_AGENT_COORDINATION_2021", "https://arxiv.org/abs/2110.13827"),
]

THEORIES = {
    "CLASSICAL_COGNITIVE_ARCHITECTURES": (
        ("cognitive architecture","act-r","soar","memory","attention","reasoning","action selection"),
        ("modular_cognitive_subsystems","declarative_procedural_memory","action_selection",
         "metacognitive_representation","temporal_self_continuity","limited_global_workspace"),
    ),
    "GLOBAL_WORKSPACE": (
        ("global workspace","broadcast","competition","workspace","limited capacity"),
        ("limited_global_workspace","causal_broadcast","selective_attention",
         "metacognitive_executive_binding","temporal_self_continuity"),
    ),
    "WORLD_MODEL_PREDICTIVE": (
        ("world model","latent dynamics","predictive","planning","counterfactual","causal reasoning"),
        ("self_world_prediction_error","recurrent_processing","counterfactual_rollout",
         "causal_world_model","model_based_planning"),
    ),
    "ACTIVE_INFERENCE": (
        ("active inference","free energy","generative model","prediction error","preferences"),
        ("self_world_prediction_error","recurrent_processing","generative_model",
         "uncertainty_aware_action_selection","goal_prior"),
    ),
    "NEURO_SYMBOLIC": (
        ("neuro-symbolic","neural-symbolic","symbolic","reasoning","compositional"),
        ("symbolic_constraint_layer","learned_representation","compositional_reasoning",
         "uncertainty_representation","explicit_rule_interface"),
    ),
    "HYPERGRAPH_REFLECTIVE": (
        ("hyperon","opencog","atomspace","hypergraph","self-modification","reflection"),
        ("relational_hypergraph_state","pattern_rewrite","metacognitive_representation",
         "self_modification_reference_model","typed_relational_memory"),
    ),
    "OPEN_ENDED_EVOLUTION": (
        ("open-ended","evolution","quality-diversity","novelty","stepping stone","diversity"),
        ("diversity_archive","stepping_stone_preservation","variation_selection_loop",
         "novelty_pressure","multi_lineage_evolution"),
    ),
    "LOCAL_SELF_ORGANIZATION": (
        ("cellular automata","local rules","local interaction","self-organization","emergent","local update"),
        ("local_state_spaces","local_update_laws","neighbor_causal_interaction",
         "emergent_global_order","perturbation_recovery","distributed_adaptation"),
    ),
    "META_NCA_ARCHITECTURE_GENERALIZATION": (
        ("metanca","architecture generalization","local interactions","self-organize","weights"),
        ("local_state_spaces","local_update_laws","topology_generalization",
         "iterative_self_refinement","distributed_adaptation"),
    ),
    "MULTI_AGENT_LOCAL_GLOBAL": (
        ("multi-agent","local coordination","global coordination","collective","neighbor"),
        ("neighbor_causal_interaction","local_goal_negotiation","global_coordination",
         "emergent_global_order","distributed_adaptation"),
    ),
    "FUNCTIONAL_CONSCIOUSNESS_INTEGRATION": (
        ("global workspace","attention schema","recurrent","predictive","self"),
        ("limited_global_workspace","attention_schema","recurrent_processing",
         "source_monitoring","self_world_prediction_error","temporal_self_continuity"),
    ),
}

# Make the existing YADO research engine operate over the broader architecture corpus.
research.SOURCES = SOURCES
research.THEORIES = THEORIES

rows = []
errors = []
for sid, url in SOURCES:
    try:
        raw, final = research.fetch(url)
        text = research.clean_html(raw)
        rows.append({
            "id": sid, "url": url, "final_url": final,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "text_chars": len(text), "text": text[:120000],
        })
    except Exception as exc:
        errors.append({"id": sid, "url": url, "error": type(exc).__name__ + ":" + str(exc)[:500]})

cards, hits = research.distill(rows)

# User's universe/spaces idea is supplied only as a hypothesis, not as authority.
spatial_hypothesis = TheoryCard(
    theory="SPATIAL_UNIVERSE_LIKE_HYPOTHESIS",
    mechanisms=(
        "local_state_spaces","local_update_laws","neighbor_causal_interaction",
        "emergent_global_order","typed_spaces","causal_boundaries",
        "topology_adaptation","multi_scale_state","invariant_preservation",
        "event_driven_temporal_continuity",
    ),
    empirical_weight=0.45,
    operational_testability=0.95,
    source_ids=("USER_HYPOTHESIS_SPATIAL_UNIVERSE_2026_08_29",),
)

synth = YADOTheorySynthesizer()
external_only = synth.synthesize(cards)
combined = synth.synthesize([*cards, spatial_hypothesis])

ablation = {}
all_cards = [*cards, spatial_hypothesis]
for c in all_cards:
    reduced = [x for x in all_cards if x.theory != c.theory]
    spec = synth.synthesize(reduced)
    ablation[c.theory] = {
        "removed_selected_mechanisms": sorted(set(combined["selected_mechanisms"]) - set(spec["selected_mechanisms"])),
        "added_selected_mechanisms": sorted(set(spec["selected_mechanisms"]) - set(combined["selected_mechanisms"])),
        "spec_sha256": spec["spec_sha256"],
    }

source = inspect.getsource(YADOTheorySynthesizer)
legacy_bias = {
    "hardcoded_architecture_name_detected": "'YADO_CAUSAL_REFLECTIVE_WORKSPACE_V1'" in source or '"YADO_CAUSAL_REFLECTIVE_WORKSPACE_V1"' in source,
    "gap_bonus_is_legacy_rc8_specific": bool(getattr(YADOTheorySynthesizer, "GAP_BONUS", {})),
    "native_additions_forced": list(getattr(YADOTheorySynthesizer, "YADO_NATIVE", ())),
    "architecture_search_neutral": False,
}
legacy_bias["reason"] = (
    "CURRENT_SYNTHESIZER_SELECTS_MECHANISMS_BUT_CANNOT_CHOOSE_AN_ARCHITECTURE_FAMILY_NEUTRALLY"
    if legacy_bias["hardcoded_architecture_name_detected"] else
    "NO_HARDCODE_DETECTED"
)

receipt = {
    "schema": "yado.rc8.shadow.meta_architecture.study.v1",
    "status": "PASS_SHADOW_ARCHITECTURE_RESEARCH_AND_BIAS_AUDIT" if len(rows) >= 6 else "INSUFFICIENT_EXTERNAL_EVIDENCE",
    "github_run_id": os.getenv("GITHUB_RUN_ID"),
    "github_sha": os.getenv("GITHUB_SHA"),
    "working_base": "VERIFIED_V36_RECONSTRUCTED",
    "canonical_mutation": False,
    "promotion_applied": False,
    "external_source_count": len(rows),
    "external_errors": errors,
    "sources": [{k:v for k,v in r.items() if k != "text"} for r in rows],
    "theory_hits": hits,
    "external_only_synthesis": external_only,
    "combined_with_spatial_hypothesis": combined,
    "spatial_hypothesis_role": "NON_AUTHORITATIVE_COMPETING_HYPOTHESIS",
    "leave_one_theory_out_ablation": ablation,
    "meta_architecture_search_audit": legacy_bias,
    "next_required_capability": (
        "ARCHITECTURE_NEUTRAL_META_SYNTHESIZER_V2_THAT_CAN_GENERATE_MULTIPLE_EXECUTABLE_ARCHITECTURE_FAMILIES"
        if legacy_bias["hardcoded_architecture_name_detected"] else
        "EXECUTABLE_ARCHITECTURE_CANDIDATE_GENERATION_AND_BLIND_SELECTION"
    ),
    "semantic_boundary": "ARCHITECTURE_RESEARCH_AND_SYNTHESIS_NOT_PROOF_OF_AGI_OR_SUBJECTIVE_CONSCIOUSNESS",
}
receipt["receipt_sha256"] = hashlib.sha256(
    json.dumps(receipt, sort_keys=True, separators=(",",":"), default=str).encode()
).hexdigest()

out = ROOT / "yado_shadow_meta_architecture_study_v1_receipt.json"
out.write_text(json.dumps(receipt, indent=2, sort_keys=True, default=str) + "\n")
print(json.dumps(receipt, indent=2, sort_keys=True, default=str))
if len(rows) < 6:
    raise SystemExit("INSUFFICIENT_EXTERNAL_EVIDENCE")
