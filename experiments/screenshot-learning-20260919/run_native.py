"""Continue the preserved YADO identity through a real Hivemind agent exchange."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import sqlite3
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT/'runtime'), str(ROOT/'runtime/yado_rc8_v36')]
from agent_tasks import TASKS, PROVENANCE
from successor.kernel import SuccessorKernel, encode, equivalent
from successor.hivemind import CRITERIA, run_issue
from successor.hivemind_client import HivemindClient
from successor.endogenous_run import propose_endogenous_goal, run_endogenous_cycles
from successor.generation import GenerationKernel, retained_memory
from successor.generation_tasks import challenge
from successor.runtime_evolution import active_candidates
from successor.cognitive import CognitiveLoop
from successor.compositional_binding import memories

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main(args):
    out = args.output.resolve()
    parent = json.loads((args.predecessor/'continuation-receipt.json').read_text())
    def save(name, value, typed=False):
        (out/(name+('.typed.json' if typed else '.json'))).write_text(
            (encode(value) if typed else json.dumps(value, indent=2, ensure_ascii=False))+'\n')
    report = {'status':'RUNNING', 'predecessor_run_id': parent['source_run_id'],
              'source_commit': subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
              'orchestration_author':'ASSISTANT', 'task_author':PROVENANCE,
              'canonical_modified':False, 'background_service_started':False}
    save('native-summary', report)
    save('agent-tasks', {'provenance':PROVENANCE, 'tasks':[{'name':n,'spec':v} for n,v in TASKS]})
    assert sha(args.hive) == '32a9f345f1bb69f0bda237449bbd28b8fb6262f1e1b7a13efff7dafe9d5c764d'
    workspace = out/'hivemind-agent-workspace'
    workspace.mkdir(exist_ok=args.resume)
    env = dict(os.environ, XDG_CONFIG_HOME=str(out/'hivemind-config'))
    if not args.resume:
        initialized = subprocess.run([str(args.hive), 'init', '--prefix','YADO','--no-agentic','--json'],
                          cwd=workspace, env=env, text=True, capture_output=True, timeout=60, check=True)
        save('hivemind-init',json.loads(initialized.stdout))
    kernel = SuccessorKernel(out/'birth/manifest.json',out/'kernel.sqlite')
    error = None
    try:
        before = parent['state_after']
        assert kernel.identity == parent['identity_digest']
        report.update(state_before=before, identity_digest=kernel.identity)
        with sqlite3.connect((args.predecessor/'kernel.sqlite').resolve().as_uri()+'?mode=ro',uri=True) as db:
            prefix=[tuple(r) for r in db.execute('SELECT * FROM events ORDER BY tick')]
        assert [tuple(r) for r in kernel.db.execute('SELECT * FROM events WHERE tick<=? ORDER BY tick',(before['tick'],))]==prefix
        old_records=[r for r in CognitiveLoop(kernel)._records() if r['tick']<=before['tick']]
        previous = {p['source_sha256'] for p in memories(old_records)}
        previous_active = active_candidates(old_records)
        workspace_id = 'yado-agent-learning-' + before['event_hash'][:32]
        results = json.loads((out/'hivemind-agent-results.json').read_text()) if args.resume else []
        with HivemindClient([str(args.hive),'mcp-stdio'],workspace/'.hivemind',env=env,actor='source_tasks') as client:
            if args.resume:
                proposal=json.loads((out/'kernel-own-proposal.json').read_text())
            else:
                proposal = propose_endogenous_goal(kernel)
                save('kernel-own-proposal', proposal)
            requests = TASKS + [('kernel-own-goal',proposal['spec'])]
            existing={i['title']:i for i in client.call('hive_list_issues',{})}
            for name,spec in requests:
                if any(r['task_name']==name for r in results):
                    continue
                issue = existing.get(name) or client.call('hive_create_issue',{'title':name,'description':json.dumps(
                    {'schema':'yado.hivemind.goal.v1','spec':spec,'budget':10,'mode':'full'}),
                    'acceptance_criteria':list(CRITERIA),'state':'todo'})
                result = run_issue(kernel,client,workspace_id,issue['id'],max_steps=100)
                result.update(task_name=name, task_origin='KERNEL' if name=='kernel-own-goal' else 'EXTERNAL_MODEL_AGENT',
                              optional_retry_check='NOT_REPEATED')
                results.append(result)
                save('hivemind-agent-results',results)
                print(json.dumps({'task':name,'status':result['status'],'passed':result['passed']}),flush=True)
            save('hivemind-readback', client.call('hive_list_issues',{}))
        development = kernel.develop_native_programs(rounds=1)
        save('native-development',development,True)
        continuation = run_endogenous_cycles(kernel,cycles=args.cycles,budget=3)
        save('native-continuation',continuation)
        assert continuation['cycles_completed']==args.cycles
        component = out/'component-evolution'
        generation = GenerationKernel(kernel,component/'experience.sqlite',component/'state.sqlite')
        try:
            application=[]
            for _ in range(3):
                seed=secrets.token_hex(24)
                for task,expected in challenge(seed):
                    result=generation.execute(task)
                    passed=equivalent(result['result']['answer'],expected)
                    application.append({'seed':seed,'task':task,'expected':expected,'execution':result,'passed':passed})
            save('component-fresh-application',application,True)
            assert all(r['passed'] for r in application)
        finally:
            generation.close()
        memory=retained_memory(kernel)
        save('retained-memory',memory,True)
        assert memory['passed']
        final_memory=kernel.native_program_status()
        current={p['source_sha256'] for p in final_memory['verified_programs']}
        assert previous <= current
        assert active_candidates(CognitiveLoop(kernel)._records())==previous_active
        after=kernel.verify_state()
        assert [tuple(r) for r in kernel.db.execute('SELECT * FROM events ORDER BY tick')][:len(prefix)]==prefix
        report.update(status='COMPLETED_WITH_MEASURED_RESULTS', state_after=after,
                      prior_events_preserved_exactly=True, inherited_runtime_strategies_preserved=True,
                      agent_tasks=len(TASKS), agent_tasks_passed=sum(r['passed'] for r in results if r['task_origin']=='EXTERNAL_MODEL_AGENT'),
                      hivemind_results=results, endogenous_cycles_verified=continuation['cycles_verified'],
                      native_programs_before=len(previous),native_programs_after=len(current),new_program_hashes=sorted(current-previous),
                      component_fresh_tasks=len(application),component_fresh_passed=sum(r['passed'] for r in application),
                      retained_memory_passed=memory['passed'],general_intelligence_proven=False,
                      development_selections=sum(len(s['selections']) for s in development['sessions']))
        save('native-program-memory',final_memory,True)
    except Exception as exc:
        error=exc
        report.update(status='WITHHOLD',error=type(exc).__name__+':'+str(exc))
    finally:
        kernel.close()
        save('native-summary',report)
    if error:
        raise error
    print(json.dumps(report,ensure_ascii=False),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--predecessor',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--hive',type=Path,required=True)
    parser.add_argument('--resume',action='store_true')
    parser.add_argument('--cycles',type=int,choices=range(1,11),default=3)
    main(parser.parse_args())
