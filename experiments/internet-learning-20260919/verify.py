"""Reopen, verify real source bindings, and seal a native-only continuation."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'runtime'),str(ROOT/'runtime/yado_rc8_v36')]
from successor.kernel import SuccessorKernel, equivalent, fingerprint
from successor.cognitive import CognitiveLoop, replay
from successor.compositional_source import execute

def main(out, predecessor):
    lesson=out/'internet-lesson'
    summary=json.loads((lesson/'summary.json').read_text())
    assert summary['status']=='COMPLETED_WITH_MEASURED_RESULTS'
    kernel=SuccessorKernel(out/'birth/manifest.json',out/'kernel.sqlite')
    try:
        assert kernel.identity==summary['identity_digest']
        final=dict(kernel.db.execute('SELECT tick,event_hash FROM events ORDER BY tick DESC LIMIT 1').fetchone())
        assert final=={k:summary['state_after'][k] for k in final}
        with sqlite3.connect((predecessor/'kernel.sqlite').as_uri()+'?mode=ro',uri=True) as db:
            old=[tuple(r) for r in db.execute('SELECT * FROM events ORDER BY tick')]
        assert [tuple(r) for r in kernel.db.execute('SELECT * FROM events WHERE tick<=? ORDER BY tick',(summary['state_before']['tick'],))]==old
        goals=replay(CognitiveLoop(kernel)._records())
        tasks={x['name']:x['spec'] for x in json.loads((lesson/'tasks.json').read_text())['tasks']}
        results=json.loads((lesson/'hivemind-results.json').read_text())
        applications=json.loads((lesson/'fresh-application.json').read_text())
        assert len(results)==len(tasks)==2
        assert {r['task_name'] for r in results}==set(tasks)
        assert len(applications)==sum(r['passed'] for r in results)
        assert {r['task_name'] for r in applications}=={r['task_name'] for r in results if r['passed']}
        checked={}
        generated_sources=[]
        for result in results:
            goal=goals[result['goal_id']]
            assert fingerprint(goal['spec'])==fingerprint(tasks[result['task_name']])
            assert goal['status']==result['status']
            assert bool(goal['verification']['passed'])==result['passed']
            if not result['passed']:continue
            candidate=goal['result']
            assert candidate['source_sha256']==result['source_sha256']
            generated_sources.append({'task_name':result['task_name'],'goal_id':result['goal_id'],
                'source_sha256':candidate['source_sha256'],'source':candidate['source'],
                'parent_source_sha256':candidate.get('parent_source_sha256',[])})
            app=next(x for x in applications if x['task_name']==result['task_name'])
            assert app['source_sha256']==candidate['source_sha256']
            if result['task_name']=='json-string-preservation':
                corpus=json.loads((lesson/'corpus-provenance.json').read_text())
                for item in corpus:
                    if item.get('document_sha256'):
                        raw=(lesson/'bytes'/(item['document_sha256']+'.txt')).read_bytes()
                        assert hashlib.sha256(raw).hexdigest()==item['document_sha256']
                        assert item['text'] in raw.decode('utf-8')
                encoded=execute(candidate,[{'text':x['text']} for x in corpus])
                js="let t='';process.stdin.setEncoding('utf8');process.stdin.on('data',s=>t+=s);process.stdin.on('end',()=>process.stdout.write(JSON.stringify(JSON.parse(t).map(s=>JSON.parse(s)))));"
                parsed=subprocess.run([os.environ.get('CODEX_PRIMARY_RUNTIME_NODE','node'),'-e',js],input=json.dumps(encoded),text=True,capture_output=True,check=True,timeout=15)
                values=json.loads(parsed.stdout)
                assert len(values)==len(corpus)
                checks=[{'partition':x['partition'],'downloaded':x.get('repository') is not None,
                         'roundtrip_passed':v==x['text'],
                         'ascii_json_passed':e==json.dumps(x['text'],ensure_ascii=True,separators=(',',':'))}
                         for x,v,e in zip(corpus,values,encoded)]
                assert all(x['roundtrip_passed'] and x['ascii_json_passed'] for x in checks)
                assert app['count']==app['passed']==sum(x['partition']=='fresh' for x in checks)
                checked[result['task_name']]={'independent_parser':'V8 JSON.parse','all_corpus_checks':len(checks),'checks':checks,
                                               'fresh_same_documents':sum(x['partition']=='fresh' for x in checks),
                                               'author_supplied_boundary_checks':sum(not x['downloaded'] for x in checks)}
            else:
                assert len(app['checks'])==app['count']==app['passed']==4
                assert all(row['passed'] for row in app['checks'])
                for row in app['checks']:
                    o=row['observation'];raw=(lesson/'bytes'/(o['raw_response_hash']+'.txt')).read_bytes()
                    assert hashlib.sha256(raw).hexdigest()==o['raw_response_hash']
                    response=json.loads(raw)
                    assert {k:response[k] for k in o['projection_fields']}==o['projection']
                    projection={**dict(reversed(list(o['projection'].items()))),'decoy':{'method':'WRONG','data':'WRONG'}}
                    assert json.loads(row['input']['response'])==projection
                    assert response['method']==o['request_method'] and response['data']==o['request_data']
                    assert row['expected']=={'method':o['request_method'],'body':o['request_data']}
                    assert equivalent(execute(candidate,[row['input']])[0],row['output'])
                    assert row['passed']==equivalent(row['output'],row['expected'])
                checked[result['task_name']]={'fresh_real_responses':len(app['checks']),
                    'passed':sum(x['passed'] for x in app['checks']),
                    'negative_contract_probes':app['negative_contract_probes']}
        assert sum(r['passed'] for r in results)==summary['tasks_passed']
        # Reuse the earlier, preserved source-normalization program on the new
        # actual repository cards. This is application, not a new training run.
        prior_candidate=goals[1788]['result']
        assert prior_candidate['source_sha256']=='02ee6fa37d05cf6c711e9f8ed0d363ef3d35e9cb8eea1315d8b2821bcd706679'
        transferred=[]
        for source in json.loads((lesson/'sources.json').read_text()):
            digest=source['metadata']['sha256'];raw=(lesson/'bytes'/(digest+'.txt')).read_bytes()
            assert hashlib.sha256(raw).hexdigest()==digest
            metadata=json.loads(raw);inputs={'record':{k:metadata[k] for k in ('full_name','html_url')}}
            prediction=execute(prior_candidate,[inputs])[0]
            expected={'source_id':metadata['full_name'].lower(),'source_url':metadata['html_url']}
            transferred.append({'repository':source['repository'],'metadata_sha256':digest,
                                'input':inputs,'output':prediction,'passed':prediction==expected})
        assert len(transferred)==4 and all(x['passed'] for x in transferred)
        checked['prior-normalizer-transfer']={'origin_goal':1788,'source_sha256':prior_candidate['source_sha256'],
            'records_processed':len(transferred),'records_passed':sum(x['passed'] for x in transferred),'rows':transferred}
    finally:
        kernel.close()
    subprocess.run(['git','diff','--exit-code','HEAD','--','runtime','successor','canonical','architecture'],cwd=ROOT,check=True,capture_output=True)
    # Unused component state is retained exactly, not relabelled as repaired.
    for name in ('experience.sqlite','state.sqlite'):
        assert hashlib.sha256((out/'component-evolution'/name).read_bytes()).hexdigest()==hashlib.sha256((predecessor/'component-evolution'/name).read_bytes()).hexdigest()
    versions={x:importlib.metadata.version(x) for x in ('aiohttp','beautifulsoup4','cryptography','fastapi','networkx','numpy','pydantic','scikit-learn')}
    verification={'status':'PASS_NATIVE_RESTART_AND_REAPPLICATION','state':summary['state_after'],
                  'previous_event_prefix_preserved':True,'component_files_preserved':True,
                  'core_runtime_modified':False,'checks':checked,'runtime_dependency_versions':versions,
                  'generated_sources':generated_sources}
    (lesson/'verification.json').write_text(json.dumps(verification,ensure_ascii=False,indent=2)+'\n')
    summary.update(status='COMPLETED_WITH_LIMITATIONS',native_restart_verified=True,
        checkpoint_id='yado-internet-learning-20260919',predecessor_component_admission_repaired=False,
        complete_api_schema_validation_proven=False,
        script_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path(__file__).parent.glob('*.py'))})
    (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    receipt={'status':'PASS_NATIVE_CHECKPOINT_INTEGRITY_COMPONENT_WITHHELD','source_run_id':0,
       'local_checkpoint_id':summary['checkpoint_id'],'predecessor_local_checkpoint_id':summary['predecessor'],
       'identity_digest':summary['identity_digest'],'state_before':summary['state_before'],'state_after':summary['state_after'],
       'prior_events_preserved_exactly':True,
       'checkpoint_files_sha256':{str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.rglob('*'))
         if p.is_file() and p.relative_to(out).as_posix() not in {'summary.json','continuation-receipt.json'} and not p.name.endswith(('-wal','-shm'))}}
    (out/'continuation-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'summary':summary,'verification_status':verification['status']},ensure_ascii=False),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);p.add_argument('--predecessor',type=Path,required=True)
    args=p.parse_args();main(args.output.resolve(),args.predecessor.resolve())
