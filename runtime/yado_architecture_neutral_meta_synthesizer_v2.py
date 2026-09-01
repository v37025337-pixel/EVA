from __future__ import annotations
from pathlib import Path
from itertools import combinations
import hashlib, json, os, sys

ROOT=Path(__file__).resolve().parent
PKG=ROOT/'yado_rc8_v36'
sys.path.insert(0,str(PKG))

from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
import yado_rc8_consciousness_direct_research_v1 as research

SOURCES=[
 ("COGARCH_REVIEW_40Y","https://arxiv.org/abs/1610.08602"),
 ("GLOBAL_WORKSPACE_AGENTS_2026","https://arxiv.org/abs/2604.08206"),
 ("WORLD_MODELS_COGNITIVE_AGENTS_2025","https://arxiv.org/abs/2506.00417"),
 ("ACTIVE_INFERENCE_DEEP_2022","https://arxiv.org/abs/2207.06415"),
 ("NEUROSYMBOLIC_COGNITIVE_AI_2024","https://arxiv.org/abs/2401.01040"),
 ("OPENCOG_HYPERON_2023","https://arxiv.org/abs/2310.18318"),
 ("OPEN_ENDED_LENIA_2024","https://arxiv.org/abs/2406.04235"),
 ("NEURAL_CELLULAR_AUTOMATA_2025","https://arxiv.org/abs/2509.11131"),
 ("META_NCA_2026","https://arxiv.org/abs/2607.07743"),
 ("LOCAL_RULES_EMERGENCE_2026","https://arxiv.org/abs/2604.00273"),
 ("UNIFIED_CONSCIOUS_ARCHITECTURE_2022","https://arxiv.org/abs/2204.05133"),
 ("LOCAL_GLOBAL_MULTI_AGENT_COORDINATION_2021","https://arxiv.org/abs/2110.13827"),
]

FAMILIES={
 "CLASSICAL_COGNITIVE":("cognitive architecture","act-r","soar","memory","action selection"),
 "GLOBAL_WORKSPACE":("global workspace","broadcast","competition","workspace","limited capacity"),
 "WORLD_MODEL":("world model","latent dynamics","predictive","planning","counterfactual","causal reasoning"),
 "ACTIVE_INFERENCE":("active inference","free energy","generative model","prediction error","preferences"),
 "NEURO_SYMBOLIC":("neuro-symbolic","neural-symbolic","symbolic","reasoning","compositional"),
 "HYPERGRAPH_REFLECTIVE":("hyperon","opencog","atomspace","hypergraph","self-modification","reflection"),
 "OPEN_ENDED_EVOLUTION":("open-ended","evolution","quality-diversity","novelty","stepping stone","diversity"),
 "LOCAL_SELF_ORGANIZING":("cellular automata","local rules","local interaction","self-organization","emergent","local update"),
 "META_NCA":("metanca","architecture generalization","local interactions","self-organize","topology"),
 "MULTI_AGENT_LOCAL_GLOBAL":("multi-agent","local coordination","global coordination","collective","neighbor"),
}

_DATASET_CACHE=None

def _vector(ids,rows):
    joined='\n'.join(rows[i]['text'] for i in ids)
    raw_counts={fam:sum(joined.count(k) for k in keys) for fam,keys in FAMILIES.items()}
    total=max(1,sum(raw_counts.values()))
    features={f'evidence_{fam.lower()}':raw_counts[fam]/total for fam in sorted(FAMILIES)}
    features['source_count']=len(ids)/3.0
    features['evidence_entropy_proxy']=sum(1 for v in raw_counts.values() if v>0)/len(raw_counts)
    label=max(sorted(raw_counts),key=lambda fam:(raw_counts[fam],fam))
    return features,label,raw_counts

def build_dataset(force=False):
    global _DATASET_CACHE
    if _DATASET_CACHE is not None and not force:
        return _DATASET_CACHE
    rows={};errors=[]
    for sid,url in SOURCES:
        try:
            raw,final=research.fetch(url)
            text=research.clean_html(raw).lower()
            rows[sid]={'id':sid,'url':url,'final_url':final,'sha256':hashlib.sha256(raw).hexdigest(),'text':text}
        except Exception as exc:
            errors.append({'id':sid,'error':type(exc).__name__+':'+str(exc)[:300]})
    if len(rows)<10:
        raise RuntimeError('INSUFFICIENT_EXTERNAL_CORPUS')
    cases=[];ids=sorted(rows)
    for size in (1,2,3):
        for combo in combinations(ids,size):
            x,y,counts=_vector(combo,rows)
            key='|'.join(combo)
            bucket=int(hashlib.sha256(key.encode()).hexdigest()[:8],16)%100
            cases.append({'key':key,'x':x,'y':y,'counts':counts,'bucket':bucket})
    data={
      'rows':rows,'errors':errors,'cases':cases,
      'blind':[(c['x'],c['y']) for c in cases if c['bucket']<18],
      'validation':[(c['x'],c['y']) for c in cases if 18<=c['bucket']<38],
      'fit':[(c['x'],c['y']) for c in cases if 38<=c['bucket']<68],
      'revealed':[(c['x'],c['y']) for c in cases if c['bucket']>=18],
    }
    _DATASET_CACHE=data
    return data

def persisted_receipt():
    p=ROOT.parent/'receipts'/'yado-architecture-neutral-meta-synth-v2-latest.json'
    if not p.exists():
        raise RuntimeError('PERSISTED_META_SYNTH_RECEIPT_MISSING')
    return json.loads(p.read_text(encoding='utf-8'))

def __getattr__(name):
    if name in ('fit','validation','revealed','blind','rows','errors','cases'):
        return build_dataset()[name]
    if name=='receipt':
        return persisted_receipt()
    raise AttributeError(name)

def run():
    data=build_dataset()
    fit=data['fit'];validation=data['validation'];revealed=data['revealed'];blind=data['blind']
    db=ROOT/'yado_meta_synth_v2.sqlite'
    k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(db))
    try:
        bank=k.organ_evolution_algorithm_bank()
        result=k.meta_evolve_intelligence(fit,validation,revealed,blind)
    finally:
        k.close()
    blind_labels=sorted(set(y for _,y in blind))
    candidate_supported=(result.get('fresh_blind',0)>=0.90 and result.get('validation',0)>=0.90 and len(blind_labels)>=4)
    receipt={
      'schema':'yado.rc8.shadow.architecture_neutral_meta_synthesizer_v2.v1',
      'status':'SHADOW_SUPPORTED' if candidate_supported else 'WITHHOLD',
      'github_run_id':os.getenv('GITHUB_RUN_ID'),'github_sha':os.getenv('GITHUB_SHA'),
      'working_base':'VERIFIED_V36_RECONSTRUCTED','canonical_mutation':False,'promotion_applied':False,
      'host_role':'corpus_transport_split_and_validation_invariants_only',
      'kernel_mechanism':'UnifiedYADOKernelV30RC8ExternalCognitive.meta_evolve_intelligence',
      'kernel_algorithm_bank':bank.get('INTELLIGENCE',[]),'kernel_result':result,
      'case_counts':{'all':len(data['cases']),'fit':len(fit),'validation':len(validation),'revealed_refit':len(revealed),'blind':len(blind)},
      'blind_family_count':len(blind_labels),'blind_families':blind_labels,
      'architecture_answer_hardcoded':False,
      'label_derivation':'ARGMAX_EXTERNAL_EVIDENCE_PROFILE_OVER_COMPETING_ARCHITECTURE_FAMILIES',
      'benchmark_limitation':'TARGET LABEL AND INPUT FEATURES ARE BOTH DERIVED FROM THE SAME HOST-DEFINED FAMILY KEYWORD ONTOLOGY; THIS TESTS SELECTOR GENERALIZATION WITHIN THAT ONTOLOGY, NOT DISCOVERY OF AN UNBOUNDED NEW ARCHITECTURE FAMILY.',
      'external_source_count':len(data['rows']),'external_errors':data['errors'],
      'source_digests':[{k:v for k,v in row.items() if k!='text'} for row in data['rows'].values()],
      'admission_requirements':['validation>=0.90','fresh_blind>=0.90','blind_contains>=4_architecture_families'],
      'next_required_capability':'SELF_GENERATED_EXECUTABLE_ARCHITECTURE_FAMILY_CONSTRUCTOR_V1' if candidate_supported else 'IMPROVE_ARCHITECTURE_NEUTRAL_SELECTOR_BEFORE_CONSTRUCTOR',
      'semantic_boundary':'META_SELECTOR_CAPABILITY NOT GENERAL ARCHITECTURE SELF-REWRITE AND NOT PROOF OF AGI',
    }
    receipt['receipt_sha256']=hashlib.sha256(json.dumps(receipt,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
    out=ROOT/'yado_architecture_neutral_meta_synthesizer_v2_receipt.json'
    out.write_text(json.dumps(receipt,indent=2,sort_keys=True,default=str)+'\n')
    print(json.dumps(receipt,indent=2,sort_keys=True,default=str))
    return receipt

if __name__=='__main__':
    run()
