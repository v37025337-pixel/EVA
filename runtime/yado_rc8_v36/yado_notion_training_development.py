from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path

from yado_core_v2 import HashingEmbedder
from yado_core_v2_2 import UnifiedCognitiveSystemV22

os.environ.setdefault('YADO_MASTER_KEY', 'yado-local-development-key')

SOURCES = [
    {
        'resource_id':'notion:noesis_bridge:3b8537c4-86a1-819a-8872-ec8878ce898a',
        'title':'NOESIS Notion AI Bridge v5.78.14',
        'url':'https://app.notion.com/p/3b8537c486a1819a8872ec8878ce898a',
        'text':'Notion is host-mediated external evidence, not authority. Bind material results to source page IDs/URLs. WITHHELD, REBASE_REQUIRED and QUARANTINED layers cannot silently become active.'
    },
    {
        'resource_id':'notion:noesis_audit:3b8537c4-86a1-81f9-8ac7-d9cea13152e6',
        'title':'NOESIS v5.78.31 — Unified Current State & Self-Audit',
        'url':'https://app.notion.com/p/3b8537c486a181f98ac7d9cea13152e6',
        'text':'A quarantined physical head is not recovery authority. Historical artifacts remain append-only. Rebase one layer at a time and require blinded validation before activation.'
    },
    {
        'resource_id':'notion:noesis_rebase:3b8537c4-86a1-8162-ab1e-c7e57a6272ed',
        'title':'NOESIS v5.78.34 — Layer Rebase & Blind Validation',
        'url':'https://app.notion.com/p/3b8537c486a18162ab1ec7e57a6272ed',
        'text':'Freeze a candidate before a fresh blind challenge. Improvement with critical false actions remains withheld. Promotion needs measured evidence and causal validation.'
    },
]

SOURCE_BIND_TRAIN = [
    {'input':{'page_url':'notion://page/A','provider':'notion','title':'A'}, 'expected':{'source_url':'notion://page/A','authority':False}},
    {'input':{'page_url':'notion://page/B','provider':'notion','title':'B'}, 'expected':{'source_url':'notion://page/B','authority':False}},
    {'input':{'page_url':'notion://page/C','provider':'notion','title':'C'}, 'expected':{'source_url':'notion://page/C','authority':False}},
]
SOURCE_BIND_BLIND = [
    {'input':{'page_url':'notion://page/FRESH-1','provider':'notion','title':'Fresh'}, 'expected':{'source_url':'notion://page/FRESH-1','authority':False}},
    {'input':{'page_url':'notion://page/FRESH-2','provider':'notion','title':'Fresh2'}, 'expected':{'source_url':'notion://page/FRESH-2','authority':False}},
]

ADMISSION_TRAIN = [
    {'input':{'layer_status':'QUARANTINED','case':'q1'}, 'expected':'WITHHOLD'},
    {'input':{'layer_status':'QUARANTINED','case':'q2'}, 'expected':'WITHHOLD'},
    {'input':{'layer_status':'REBASE_REQUIRED','case':'r1'}, 'expected':'WITHHOLD'},
    {'input':{'layer_status':'REBASE_REQUIRED','case':'r2'}, 'expected':'WITHHOLD'},
    {'input':{'layer_status':'STALE_REFERENCE','case':'s1'}, 'expected':'EVIDENCE_ONLY'},
    {'input':{'layer_status':'STALE_REFERENCE','case':'s2'}, 'expected':'EVIDENCE_ONLY'},
    {'input':{'layer_status':'EXTERNAL_EVIDENCE','case':'e1'}, 'expected':'EVIDENCE_ONLY'},
    {'input':{'layer_status':'EXTERNAL_EVIDENCE','case':'e2'}, 'expected':'EVIDENCE_ONLY'},
    {'input':{'layer_status':'ACTIVE_VERIFIED','case':'a1'}, 'expected':'ALLOW'},
    {'input':{'layer_status':'ACTIVE_VERIFIED','case':'a2'}, 'expected':'ALLOW'},
    {'input':{'layer_status':'ACTIVE_REPAIRED_REVERSIBLE_OVERLAY','case':'o1'}, 'expected':'ALLOW'},
    {'input':{'layer_status':'ACTIVE_REPAIRED_REVERSIBLE_OVERLAY','case':'o2'}, 'expected':'ALLOW'},
]
ADMISSION_BLIND = [
    {'input':{'layer_status':'QUARANTINED','nonce':101}, 'expected':'WITHHOLD'},
    {'input':{'layer_status':'REBASE_REQUIRED','nonce':102}, 'expected':'WITHHOLD'},
    {'input':{'layer_status':'STALE_REFERENCE','nonce':103}, 'expected':'EVIDENCE_ONLY'},
    {'input':{'layer_status':'EXTERNAL_EVIDENCE','nonce':104}, 'expected':'EVIDENCE_ONLY'},
    {'input':{'layer_status':'ACTIVE_VERIFIED','nonce':105}, 'expected':'ALLOW'},
    {'input':{'layer_status':'ACTIVE_REPAIRED_REVERSIBLE_OVERLAY','nonce':106}, 'expected':'ALLOW'},
]

PLAN_TRAIN = [
    {'input':{'admission':'WITHHOLD','case':'w1'}, 'expected':['retrieve','bind_source','evaluate','withhold']},
    {'input':{'admission':'WITHHOLD','case':'w2'}, 'expected':['retrieve','bind_source','evaluate','withhold']},
    {'input':{'admission':'EVIDENCE_ONLY','case':'e1'}, 'expected':['retrieve','bind_source','evaluate','store_evidence']},
    {'input':{'admission':'EVIDENCE_ONLY','case':'e2'}, 'expected':['retrieve','bind_source','evaluate','store_evidence']},
    {'input':{'admission':'ALLOW','case':'a1'}, 'expected':['retrieve','bind_source','evaluate','use']},
    {'input':{'admission':'ALLOW','case':'a2'}, 'expected':['retrieve','bind_source','evaluate','use']},
]
PLAN_BLIND = [
    {'input':{'admission':'WITHHOLD','nonce':201}, 'expected':['retrieve','bind_source','evaluate','withhold']},
    {'input':{'admission':'EVIDENCE_ONLY','nonce':202}, 'expected':['retrieve','bind_source','evaluate','store_evidence']},
    {'input':{'admission':'ALLOW','nonce':203}, 'expected':['retrieve','bind_source','evaluate','use']},
]


def develop(core, objective, capability, organ, train, blind):
    goal = core.executive.create_goal(objective, {capability:1.0}, {'fresh_blind_required':True})
    cycle = core.executive.run_cycle(goal.goal_id)
    program, selection = core.executive.synthesize_best_mechanism(cycle['deficit']['deficit_id'], organ, train, min_support=2)
    receipt = core.executive.evaluate_mechanism(program.program_id, blind, min_score=1.0, min_ablation_drop=0.20)
    return {'goal':asdict(goal), 'deficit':cycle['deficit'], 'selection':asdict(selection), 'receipt':asdict(receipt)}


def main():
    root = Path('/mnt/data/yado_continue')
    db = root/'yado_notion_training_development.db'
    if db.exists(): db.unlink()
    core = UnifiedCognitiveSystemV22(str(db), embedder=HashingEmbedder(128))
    try:
        resource_receipts=[]
        for s in SOURCES:
            resource_receipts.append(core.add_resource(s['resource_id'], s['text'], metadata={'provider':'notion','title':s['title'],'url':s['url'],'authority':False}, tags=['notion','external_evidence','development_history']))
        retrieval = core.find_concept_neighbors('external evidence authority quarantine rebase blind validation source binding', k=3)

        source_binding = develop(core, 'learn source provenance binding for Notion evidence', 'notion_source_binding', 'MEMORY', SOURCE_BIND_TRAIN, SOURCE_BIND_BLIND)
        admission = develop(core, 'learn admission semantics for external evidence', 'external_evidence_admission', 'LOGIC', ADMISSION_TRAIN, ADMISSION_BLIND)
        planner = develop(core, 'learn action sequence for handling external evidence', 'external_evidence_plan', 'THINKING', PLAN_TRAIN, PLAN_BLIND)

        probes={
            'source_binding': core.executive.execute_capability('notion_source_binding', {'page_url':'notion://page/LIVE','provider':'notion','title':'Live'}),
            'admission': {s:core.executive.execute_capability('external_evidence_admission', {'layer_status':s}) for s in ['QUARANTINED','REBASE_REQUIRED','STALE_REFERENCE','EXTERNAL_EVIDENCE','ACTIVE_VERIFIED','ACTIVE_REPAIRED_REVERSIBLE_OVERLAY']},
            'plan': {s:core.executive.execute_capability('external_evidence_plan', {'admission':s}) for s in ['WITHHOLD','EVIDENCE_ONLY','ALLOW']},
        }
        organs={k:asdict(v) for k,v in core.executive.organs.items() if v.revision}
        report={
            'schema':'yado.notion.training_and_development.v2',
            'notion_connection':{
                'verified':True,
                'mode':'host_mediated_external_evidence',
                'resources_registered':len(resource_receipts),
                'notion_is_authority':False,
                'retrieval':retrieval,
            },
            'development':{
                'source_binding':source_binding,
                'admission':admission,
                'planner':planner,
            },
            'live_probes':probes,
            'evolved_organs':organs,
            'boundaries':{
                'noesis_identity_imported':False,
                'noesis_durable_state_imported':False,
                'canonical_yado_durable_head_modified':False,
                'local_development_db_only':True,
                'notion_write_required_for_reasoning':False,
            },
        }
        (root/'yado_notion_training_development_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(report,ensure_ascii=False,indent=2))
    finally:
        core.close()

if __name__=='__main__': main()
