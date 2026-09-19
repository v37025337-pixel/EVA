"""Verify restart and preserve a complete continuation checkpoint."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT/'runtime'), str(ROOT/'runtime/yado_rc8_v36')]
from successor.kernel import SuccessorKernel, fingerprint, decode, encode
from successor.generation import retained_memory, evaluate, parent_profile
from successor.generation_tasks import challenge
from successor.cognitive import CognitiveLoop, replay
from successor.compositional_source import execute
from successor.compositional_binding import memories
from successor.runtime_evolution import active_candidates

def main(out, predecessor):
    native=json.loads((out/'native-summary.json').read_text())
    assert native['status']=='WITHHOLD'
    assert native['error']=='ValueError:GENERATION_ADMISSION_NOT_REPRODUCIBLE'
    continuation=json.loads((out/'native-continuation.json').read_text())
    native['hivemind_results']=json.loads((out/'hivemind-agent-results.json').read_text())
    source_stages={name:json.loads((out/(name+'.json')).read_text()) for name in
                   ('ecosystem-host-transport','repository-development-host-transport','router-comparison')}
    kernel=SuccessorKernel(out/'birth/manifest.json',out/'kernel.sqlite')
    try:
        # Opening SuccessorKernel already performs complete state verification.
        # This sealed checkpoint has no concurrent writer.
        last=kernel.db.execute('SELECT tick,event_hash FROM events ORDER BY tick DESC LIMIT 1').fetchone()
        state={'status':'PASS','tick':last['tick'],'event_hash':last['event_hash']}
        assert state==continuation['state_verification']
        assert kernel.identity==native['identity_digest']
        with sqlite3.connect((predecessor/'kernel.sqlite').as_uri()+'?mode=ro',uri=True) as db:
            prefix=[tuple(r) for r in db.execute('SELECT * FROM events ORDER BY tick')]
        assert [tuple(r) for r in kernel.db.execute('SELECT * FROM events WHERE tick<=? ORDER BY tick',
                (native['state_before']['tick'],))]==prefix
        records=CognitiveLoop(kernel)._records()
        old_records=[r for r in records if r['tick']<=native['state_before']['tick']]
        previous={p['source_sha256'] for p in memories(old_records)}
        current={p['source_sha256'] for p in memories(records)}
        assert previous <= current
        assert active_candidates(old_records)==active_candidates(records)
        goals=replay(records)
        tasks=json.loads((out/'agent-tasks.json').read_text())
        expected={row['name']:row['spec'] for row in tasks['tasks']}
        expected['kernel-own-goal']=json.loads((out/'kernel-own-proposal.json').read_text())['spec']
        assert len(native['hivemind_results'])==len(expected)
        assert {r['task_name'] for r in native['hivemind_results']}==set(expected)
        for result in native['hivemind_results']:
            goal=goals[result['goal_id']]
            assert fingerprint(goal['spec'])==fingerprint(expected[result['task_name']])
            assert goal['status']==result['status']
            assert bool(goal['verification']['passed'])==result['passed']
            if result.get('source_sha256'):
                actual=goal['result'] if goal['result'] is not None else goal['execution']['result']
                assert actual['source_sha256']==result['source_sha256']
        application=json.loads((out/'learned-normalizer-live-application.json').read_text())
        candidate=goals[application['candidate_origin_goal_id']]['result']
        assert candidate['source_sha256']==application['source_sha256']
        predictions=execute(candidate,[row['input'] for row in application['rows']])
        assert len(predictions)==len(application['rows'])==9
        for row,prediction in zip(application['rows'],predictions):
            raw=(out/'public-source-bytes'/(row['metadata_sha256']+'.txt')).read_bytes()
            assert hashlib.sha256(raw).hexdigest()==row['metadata_sha256']
            metadata=json.loads(raw)
            assert row['input']=={'record':{key:metadata[key] for key in ('full_name','html_url')}}
            assert prediction==row['output']=={'source_id':metadata['full_name'].lower(),'source_url':metadata['html_url']}
        component=out/'component-evolution'
        component_hashes={}
        for filename in ('experience.sqlite','state.sqlite'):
            component_hashes[filename]=hashlib.sha256((component/filename).read_bytes()).hexdigest()
            assert component_hashes[filename]==hashlib.sha256((predecessor/'component-evolution'/filename).read_bytes()).hexdigest()
        with sqlite3.connect((component/'state.sqlite').as_uri()+'?mode=ro',uri=True) as db:
            component_records=[decode(r[0]) for r in db.execute('SELECT body FROM events ORDER BY tick')]
        birth=component_records[0]
        proposal=next(r for r in component_records if r['kind']=='PROPOSE')
        admission=next(r for r in component_records if r['kind']=='ADMISSION')
        cases=challenge(admission['fresh_seed'])
        protected=challenge(admission['fresh_seed'],retention=True)
        # Diagnostic calculations only. No component gate is bypassed or activated.
        expected={'parent':evaluate(parent_profile(),cases),'child':evaluate(proposal['profile'],cases),
                  'parent_retention':evaluate(parent_profile(),protected),
                  'child_retention':evaluate(proposal['profile'],protected),
                  'inherited_memory':retained_memory(kernel,birth['parent_state']['tick'])}
        comparisons={key:admission[key]==value for key,value in expected.items()}
        old_checks={r['goal_id']:r for r in admission['inherited_memory']['checks']}
        diffs=[{'goal_id':r['goal_id'],'archived':old_checks.get(r['goal_id']),'replayed':r}
               for r in expected['inherited_memory']['checks'] if old_checks.get(r['goal_id'])!=r]
        diagnostic={'status':'WITHHOLD','error':native['error'],'matching_sections':comparisons,
                    'differing_memory_checks':diffs,'component_files_preserved_exactly':component_hashes,
                    'historical_parent_tick':birth['parent_state']['tick'],
                    'current_replay_passed':expected['inherited_memory']['passed'],
                    'component_fresh_tasks_executed':0,'gate_bypassed':False}
        (out/'component-admission-diagnostic.json').write_text(json.dumps(diagnostic,indent=2)+'\n')
        (out/'component-inherited-memory-replay.typed.json').write_text(encode(expected['inherited_memory'])+'\n')
        assert not all(comparisons.values()), 'EXPECTED_FAILURE_NOT_REPRODUCED'
        development=decode((out/'native-development.typed.json').read_text())
        native.update(state_after=state,prior_events_preserved_exactly=True,
            inherited_runtime_strategies_preserved=True,agent_tasks=2,
            agent_tasks_passed=sum(r['passed'] for r in native['hivemind_results'] if r['task_origin']=='EXTERNAL_MODEL_AGENT'),
            endogenous_cycles_verified=continuation['cycles_verified'],native_programs_before=len(previous),
            native_programs_after=len(current),new_program_hashes=sorted(current-previous),
            component_fresh_tasks=0,component_fresh_passed=0,
            component_historical_memory_replay_passed=expected['inherited_memory']['passed'],
            general_intelligence_proven=False,development_selections=sum(len(s['selections']) for s in development['sessions']))
    finally:
        kernel.close()
    loader=importlib.util.spec_from_file_location('resume',ROOT/'experiments/repository-learning-resume-20260919/run.py')
    resume=importlib.util.module_from_spec(loader);loader.loader.exec_module(resume)
    for relative in resume.OVERLAY:
        target=out/'source-overlay'/relative
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(ROOT/relative,target)
    # Keep script hashes here; their reviewed source is retained in Git.
    script_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in sorted(Path(__file__).parent.glob('*.py'))}
    inventory=json.loads((out/'screenshot-source-inventory.json').read_text())
    summary={**native, 'restart_verified':True,'component_restart_verified':False,
             'native_progress_status':'VERIFIED_PARTIAL_PROGRESS',
             'source_repositories_received':sum(x['status']=='FETCHED_REAL_CONTENT' for x in inventory),
             'source_repositories_requested':len(inventory),
             'source_documents_received':sum(2 for x in inventory if x['status']=='FETCHED_REAL_CONTENT'),
             'source_stage_statuses':{k:v.get('status','RECORDED') for k,v in source_stages.items()},
             'router_measured_gain':source_stages['router-comparison']['gain'],
             'learned_program_real_records_passed':len(predictions),
             'learned_program_real_records_previously_unseen':application['independent_new_input_count'],
             'all_documents_semantically_understood':False,
             'external_agent_tasks_relayed_by_assistant':True,
             'third_party_repositories_modified':False,
             'external_model_agents_launched_by_yado':False,
             'local_checkpoint_id':'yado-screenshot-learning-20260919',
             'campaign_script_sha256':script_hashes,
             'network_limitations':['YADO direct resolver: DNS_RESOLUTION_FAILED',
                                    'Direct Exa MCP POST: HTTP 403; Exa connector fetch succeeded'],
             'source_processing_scope':'Public content receipts and existing marker checks; native training uses explicitly agent-authored structured tasks'}
    (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    receipt={'status':'PASS_NATIVE_CHECKPOINT_INTEGRITY_COMPONENT_WITHHELD',
             'source_run_id':0,'local_checkpoint_id':summary['local_checkpoint_id'],
             'predecessor_run_id':native['predecessor_run_id'],'identity_digest':native['identity_digest'],
             'state_before':native['state_before'],'state_after':state,
             'prior_events_preserved_exactly':True,
             'checkpoint_files_sha256':{str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(out.rglob('*')) if p.is_file() and p.name not in {'summary.json','continuation-receipt.json'}
                and not p.name.endswith(('-wal','-shm'))}}
    (out/'continuation-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(summary,ensure_ascii=False),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path)
    parser.add_argument('--predecessor',type=Path,required=True)
    args=parser.parse_args()
    main(args.output.resolve(),args.predecessor.resolve())
