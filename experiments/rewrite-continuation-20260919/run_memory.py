"""Observe existing YADO selectors; never inject a candidate or success verdict."""
import json
from pathlib import Path
import shutil
import sqlite3
import sys
from contextlib import ExitStack
from unittest.mock import patch

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--predecessor', required=True, type=Path)
parser.add_argument('--output', required=True, type=Path)
args = parser.parse_args()
ROOT = Path(__file__).resolve().parents[2]
BASE = args.predecessor.resolve()
OUT = args.output.resolve()
sys.path[:0] = [str(ROOT), str(ROOT/'runtime'), str(ROOT/'runtime/yado_rc8_v36')]
from successor.archive import file_sha
from successor.kernel import SuccessorKernel, encode
from successor.cognitive import CognitiveLoop, replay
from successor.generation import retained_memory
from successor.continuity import prepare_upgrade
from successor.lineage import ConsecutiveLineage, REQUEST
from yado_unified_core_v1 import UnifiedYADOCoreV1

def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')

def rows(path):
    with sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True) as db:
        return list(db.execute('SELECT * FROM events ORDER BY tick'))

def main():
    receipt=json.loads((BASE/'continuation-receipt.json').read_text())
    for name,digest in receipt['checkpoint_files_sha256'].items():
        p=(BASE/name).resolve()
        assert p.is_relative_to(BASE) and file_sha(p)==digest,name
    prior=rows(BASE/'kernel.sqlite')
    shutil.copytree(BASE,OUT)
    evidence=OUT/'rewrite-continuation'
    evidence.mkdir()
    shutil.copyfile(__file__,evidence/'run.py')
    save(evidence/'predecessor-receipt.json',receipt)
    print('CHECKPOINT_VERIFIED_AND_COPIED',flush=True)
    (OUT/'birth').rename(OUT/'pre-rewrite-birth')
    manifest=json.loads((OUT/'pre-rewrite-birth/manifest.json').read_text())
    changes={p:{'previous_sha256':h,'current_sha256':file_sha(ROOT/p)}
             for p,h in manifest['inherited_files'].items() if file_sha(ROOT/p)!=h}
    assert set(changes)=={'runtime/yado_native_self_rewrite_v4_fresh_experience.py',
                          'runtime/test_yado_native_self_rewrite_v4_fresh_experience.py'}, changes
    transition=prepare_upgrade(OUT/'pre-rewrite-birth/manifest.json',OUT/'kernel.sqlite',
                               OUT/'birth',source_updates=changes)
    shutil.copyfile(OUT/'birth/kernel.sqlite',OUT/'kernel.sqlite')
    save(evidence/'implementation-transition.json',transition)
    print('EXPLICIT_IMPLEMENTATION_TRANSITION_WITH_PREFIX_PRESERVED',flush=True)
    with ExitStack() as stack:
        accessors=[stack.enter_context(patch.object(UnifiedYADOCoreV1,name,
            side_effect=AssertionError('HISTORICAL_REPLAY_MUST_BE_OFFLINE')))
            for name in ('native_library_candidate','verify_native_library')]
        kernel=SuccessorKernel(OUT/'birth/manifest.json',OUT/'kernel.sqlite')
        try:
            kernel.db.execute('PRAGMA journal_mode=DELETE')
            assert kernel.identity==receipt['identity_digest']
            assert kernel.verify_state()['tick']==receipt['state_after']['tick']+1
            before=kernel.native_program_status()
            old_goals=replay(CognitiveLoop(kernel)._records())
            development=kernel.develop_native_programs(rounds=1)
            save(evidence/'development.json',development)
            print(json.dumps({'phase':'DEVELOPMENT','selections':sum(len(s['selections']) for s in development['sessions']),
                'reasons':[s.get('reason') for s in development['sessions']]}),flush=True)
            sid=kernel.start_autonomy(budget=30,max_cycles=2)
            for step in range(150):
                events=kernel.run_autonomy(max_steps=1)
                for event in events:
                    body=event.get('body',event)
                    if body.get('kind') in {'AUTO_SELECT','AUTO_OUTCOME','AUTO_FINISH'}:
                        print(json.dumps({'phase':'AUTONOMY','tick':event.get('tick'),'kind':body['kind'],
                            'route':body.get('choice',{}).get('route'),'domain':body.get('choice',{}).get('spec',{}).get('domain'),
                            'status':body.get('status')}),flush=True)
                if not events:
                    break
            autonomy=kernel.autonomy_snapshot()['sessions'][sid]
            save(evidence/'autonomy.json',autonomy)
            assert autonomy['status']=='COMPLETE',autonomy['status']
            print('AUTONOMY_COMPLETED',flush=True)
            lineage=ConsecutiveLineage(kernel)
            lid=lineage.start('local-authorized-rewrite-continuation','YADO-CURRENT-PARENT-20260919',REQUEST)
            result=lineage.run(lid,evidence/'lineage-gates',progress=lambda r:print(json.dumps({'phase':'LINEAGE',**r}),flush=True))
            (evidence/'lineage.typed.json').write_text(encode(result)+'\n')
            memory=retained_memory(kernel)
            save(evidence/'memory.json',memory)
            assert memory['passed']
            current=replay(CognitiveLoop(kernel)._records())
            assert all(current[key]==value for key,value in old_goals.items())
            after=kernel.native_program_status()
            state=kernel.verify_state()
            assert kernel.parent.audit()['pass']
        finally:
            kernel.close()
        assert all(a.call_count==0 for a in accessors)
    assert rows(OUT/'kernel.sqlite')[:len(prior)]==prior
    assert file_sha(BASE/'component-evolution/state.sqlite')==file_sha(OUT/'component-evolution/state.sqlite')
    summary={'status':'COMPLETED_VERIFIED_CONTINUATION','source_base_commit':'c3979b41d675f54b6f797106b47e23b591d1794e',
        'source_updates':changes,
        'identity_digest':receipt['identity_digest'],'state_before':receipt['state_after'],'state_after':state,
        'native_history_prefix_preserved':True,'component_state_unchanged':True,
        'native_programs_before':len(before['verified_programs']),'native_programs_after':len(after['verified_programs']),
        'new_program_hashes':sorted({p['source_sha256'] for p in after['verified_programs']}-{p['source_sha256'] for p in before['verified_programs']}),
        'development_selections':sum(len(s['selections']) for s in development['sessions']),
        'development_reasons':[s.get('reason') for s in development['sessions']],
        'autonomy_cycles':len(autonomy['outcomes']),
        'autonomy_verified':sum(r['status'] in {'VALIDATED_ON_HOLDOUT','VERIFIED'} for r in autonomy['outcomes']),
        'autonomy_routes':[s['route'] for s in autonomy['selections']],
        'autonomy_domains':[s['spec']['domain'] for s in autonomy['selections']],
        'lineage_status':result['status'],'lineage_reason':result['finish']['reason'],
        'lineage_generations':len(result['generations']),'retained_goals':memory['goals'],
        'memory_passed':True,'historical_pypi_calls':0,'host_supplied_new_goals':0,
        'active_grammar':after['language']['grammar'],'background_process_running':False,
        'new_internet_data_collected':False,'g3_established':False}
    save(evidence/'summary.json',summary)
    save(OUT/'summary.json',summary)
    new_receipt={'status':summary['status'],'identity_digest':summary['identity_digest'],'state_after':state,
        'source_run_id':0,'checkpoint_files_sha256':{str(p.relative_to(OUT)):file_sha(p) for p in sorted(OUT.rglob('*'))
        if p.is_file() and p.name!='continuation-receipt.json' and not p.name.endswith(('-wal','-shm'))}}
    save(OUT/'continuation-receipt.json',new_receipt)
    print(json.dumps(summary),flush=True)

if __name__=='__main__':
    main()
