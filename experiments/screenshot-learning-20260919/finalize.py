"""Verify restart and preserve a complete continuation checkpoint."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT/'runtime'), str(ROOT/'runtime/yado_rc8_v36')]
from successor.kernel import SuccessorKernel, fingerprint
from successor.generation import GenerationKernel
from successor.cognitive import CognitiveLoop, replay

def main(out):
    native=json.loads((out/'native-summary.json').read_text())
    if native['status']!='COMPLETED_WITH_MEASURED_RESULTS':
        raise ValueError('NATIVE_CAMPAIGN_INCOMPLETE')
    source_stages={name:json.loads((out/(name+'.json')).read_text()) for name in
                   ('ecosystem-host-transport','repository-development-host-transport','router-comparison')}
    kernel=SuccessorKernel(out/'birth/manifest.json',out/'kernel.sqlite')
    try:
        state=kernel.verify_state()
        assert state==native['state_after']
        assert kernel.identity==native['identity_digest']
        goals=replay(CognitiveLoop(kernel)._records())
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
        component=out/'component-evolution'
        generation=GenerationKernel(kernel,component/'experience.sqlite',component/'state.sqlite')
        try:
            profile=generation.snapshot()
            assert profile['component_generation']==1
        finally:
            generation.close()
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
    summary={**native, 'restart_verified':True,'component_restart_verified':True,
             'source_repositories_received':sum(x['status']=='FETCHED_REAL_CONTENT' for x in inventory),
             'source_repositories_requested':len(inventory),
             'source_documents_received':sum(2 for x in inventory if x['status']=='FETCHED_REAL_CONTENT'),
             'source_stage_statuses':{k:v.get('status','RECORDED') for k,v in source_stages.items()},
             'router_measured_gain':source_stages['router-comparison']['gain'],
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
    receipt={'status':'PASS_SHADOW_STATEFUL_RESTART_CONTINUATION_V1',
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
    main(parser.parse_args().output.resolve())
