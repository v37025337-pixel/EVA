"""Continue the same native identity on real echo data and local text examples."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'runtime'),str(ROOT/'runtime/yado_rc8_v36')]
from successor.kernel import SuccessorKernel, equivalent
from successor.cognitive import CognitiveLoop, replay
from successor.compositional_binding import memories
from successor.compositional_source import execute
from successor.hivemind import run_issue, CRITERIA
from successor.hivemind_client import HivemindClient
from sources import echo

def save(folder,name,value):
    (folder/(name+'.json')).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')

def spec(training,validation,queries):
    return {'schema':'yado.native_program_goal.v1','domain':'native_source',
            'training':training,'validation':validation,'queries':queries}

def tasks(lesson):
    inventory=json.loads((lesson/'sources.json').read_text())
    corpus=[]; seen=set()
    for repo in inventory:
        if repo['repository']=='hoppscotch/hoppscotch': continue
        docs=[d for d in repo['documents'] if d['path']!='README.md']
        items=[]
        for doc in docs:
            raw=(lesson/'bytes'/(doc['sha256']+'.txt')).read_bytes()
            assert hashlib.sha256(raw).hexdigest()==doc['sha256']
            text=raw.decode('utf-8')
            values=text.splitlines() if doc['path'].endswith('.txt') else re.findall(r'(?<!`)`([^`\n]+)`(?!`)',text)
            for value in values:
                if value not in seen and 0<len(value)<=240 and not value.startswith('#'):
                    seen.add(value)
                    items.append({'text':value,'repository':repo['repository'],'document_sha256':doc['sha256'],'path':doc['path']})
        assert len(items)>=6,repo['repository']
        corpus.extend({**x,'partition':'training' if i<2 else 'validation' if i<4 else 'queries' if i<5 else 'fresh'} for i,x in enumerate(items[:13]))
    # Explicit contract/agent cases are disclosed and never labelled downloaded.
    for value,partition in [('Ж🙂','training'),('line one\nline two','training'),
                            ('literal \\n vs actual\n; literal \\u0061 vs a; " \\ 😀','validation')]:
        assert value not in seen
        seen.add(value);corpus.append({'text':value,'repository':None,'origin':'EXPLICIT_CONTRACT_AND_AGENT_CASE','partition':partition})
    rows={p:[] for p in ('training','validation','queries')}
    for item in corpus:
        if item['partition'] in rows:
            row={'input':{'text':item['text']}}
            if item['partition']!='queries':row['expected']=json.dumps(item['text'],ensure_ascii=True,separators=(',',':'))
            rows[item['partition']].append(row)
    serializer=spec(**rows)
    observations=json.loads((lesson/'echo-observations.json').read_text())
    echo_rows=[]
    for i,o in enumerate(observations):
        projection=o['projection']
        if i>=3:
            projection={**dict(reversed(list(projection.items()))),'decoy':{'method':'WRONG','data':'WRONG'}}
        row={'input':{'response':json.dumps(projection,ensure_ascii=True,separators=(',',':'))}}
        if i<5:row['expected']={'method':o['request_method'],'body':o['request_data']}
        echo_rows.append(row)
    extraction=spec(echo_rows[:3],echo_rows[3:5],echo_rows[5:])
    save(lesson,'corpus-provenance',corpus)
    definitions=[{'name':'json-string-preservation','spec':serializer}, {'name':'echo-response-extraction','spec':extraction}]
    save(lesson,'tasks',{'author':'ASSISTANT','external_agent_role':'INDEPENDENT_EDGE_CASE_REVIEW',
         'network_projection':'Host removes routing headers; kernel receives a JSON text and performs its own parse',
         'security_scope':'LOCAL_STRING_SERIALIZATION_ONLY','tasks':definitions})
    return definitions,corpus

def main(args):
    out=args.output.resolve();lesson=out/'internet-lesson'
    prior=json.loads((args.predecessor/'summary.json').read_text())
    assert prior['state_after']['tick']==1840
    definitions,corpus=tasks(lesson)
    report={'status':'RUNNING','state_before':prior['state_after'],'predecessor':'yado-screenshot-learning-20260919',
            'identity_digest':prior['identity_digest'],'canonical_modified':False,
            'task_authorship':'ASSISTANT','network_transport_authorship':'ASSISTANT',
            'security_payloads_sent_to_external_targets':False,'background_process_running':False,
            'inherited_component_status':'WITHHOLD_NOT_RETESTED','core_defects_repaired':False}
    save(lesson,'summary',report)
    assert hashlib.sha256(args.hive.read_bytes()).hexdigest()=='32a9f345f1bb69f0bda237449bbd28b8fb6262f1e1b7a13efff7dafe9d5c764d'
    workspace=out/'internet-hivemind';workspace.mkdir()
    env=dict(os.environ,XDG_CONFIG_HOME=str(out/'internet-hive-config'))
    subprocess.run([str(args.hive),'init','--prefix','WEB','--no-agentic','--json'],cwd=workspace,env=env,check=True,capture_output=True,timeout=30)
    print('OPENING_PRESERVED_NATIVE_KERNEL',flush=True)
    kernel=SuccessorKernel(out/'birth/manifest.json',out/'kernel.sqlite')
    try:
        assert kernel.identity==prior['identity_digest']
        last=kernel.db.execute('SELECT tick,event_hash FROM events ORDER BY tick DESC LIMIT 1').fetchone()
        assert dict(last)=={k:prior['state_after'][k] for k in ('tick','event_hash')}
        records=CognitiveLoop(kernel)._records();before={x['source_sha256'] for x in memories(records)}
        results=[]
        with HivemindClient([str(args.hive),'mcp-stdio'],workspace/'.hivemind',env=env,actor='internet-learning-observer') as client:
            for task in definitions:
                issue=client.call('hive_create_issue',{'title':task['name'],'description':json.dumps({'schema':'yado.hivemind.goal.v1','spec':task['spec'],'budget':10,'mode':'full'}),'acceptance_criteria':list(CRITERIA),'state':'todo'})
                result=run_issue(kernel,client,'yado-internet-1840',issue['id'],max_steps=40)
                result['task_name']=task['name'];results.append(result)
                save(lesson,'hivemind-results',results)
                print(json.dumps({'task':task['name'],'status':result['status'],'passed':result['passed']}),flush=True)
            save(lesson,'tracker',client.call('hive_list_issues',{}))
        goals=replay(CognitiveLoop(kernel)._records())
        applied=[]
        for row in results:
            if not row['passed']:continue
            candidate=goals[row['goal_id']]['result']
            if row['task_name']=='json-string-preservation':
                fresh=[x for x in corpus if x['partition']=='fresh']
                encoded=execute(candidate,[{'text':x['text']} for x in fresh])
                # Independent parser implementation: V8 JSON.parse, not Python's encoder.
                node=os.environ.get('CODEX_PRIMARY_RUNTIME_NODE','node')
                script="let t='';process.stdin.setEncoding('utf8');process.stdin.on('data',x=>t+=x);process.stdin.on('end',()=>process.stdout.write(JSON.stringify(JSON.parse(t).map(x=>JSON.parse(x)))));"
                checked=subprocess.run([node,'-e',script],input=json.dumps(encoded),text=True,capture_output=True,check=True,timeout=15)
                decoded=json.loads(checked.stdout)
                checks=[{'corpus':x,'encoded':v,'roundtrip_passed':d==x['text'],'canonical_ascii_passed':v==json.dumps(x['text'],ensure_ascii=True,separators=(',',':'))} for x,v,d in zip(fresh,encoded,decoded)]
                applied.append({'task_name':row['task_name'],'source_sha256':candidate['source_sha256'],'count':len(checks),'passed':sum(c['roundtrip_passed'] and c['canonical_ascii_passed'] for c in checks),'checks':checks,'independent_parser':'V8 JSON.parse'})
            else:
                checks=[]
                for method in ('POST','GET','POST','GET'):
                    observation=echo(lesson,method,'after-source-freeze')
                    projection={**dict(reversed(list(observation['projection'].items()))),'decoy':{'method':'WRONG','data':'WRONG'}}
                    inputs={'response':json.dumps(projection,separators=(',',':'))}
                    prediction=execute(candidate,[inputs])[0]
                    expected={'method':method,'body':observation['request_data']}
                    checks.append({'observation':observation,'input':inputs,'output':prediction,'expected':expected,'passed':equivalent(prediction,expected)})
                    save(lesson,'fresh-echo-progress',checks)
                negative=[]
                for label,body in [('missing-method',{'data':'sample'}),('wrong-method-type',{'method':17,'data':'sample'})]:
                    try:
                        value=execute(candidate,[{'response':json.dumps(body)}])[0]
                        negative.append({'case':label,'rejected':False,'output':value})
                    except Exception as exc:negative.append({'case':label,'rejected':True,'error':type(exc).__name__+':'+str(exc)})
                applied.append({'task_name':row['task_name'],'source_sha256':candidate['source_sha256'],'count':len(checks),'passed':sum(c['passed'] for c in checks),'checks':checks,'negative_contract_probes':negative})
        save(lesson,'fresh-application',applied)
        current={x['source_sha256'] for x in memories(CognitiveLoop(kernel)._records())}
        assert before<=current
        state=kernel.verify_state()
        with sqlite3.connect(args.predecessor.resolve().joinpath('kernel.sqlite').as_uri()+'?mode=ro',uri=True) as db:
            old=[tuple(r) for r in db.execute('SELECT * FROM events ORDER BY tick')]
        assert [tuple(r) for r in kernel.db.execute('SELECT * FROM events WHERE tick<=? ORDER BY tick',(prior['state_after']['tick'],))]==old
        report.update(status='COMPLETED_WITH_MEASURED_RESULTS',state_after=state,prior_events_preserved_exactly=True,
            tasks_submitted=len(results),tasks_passed=sum(r['passed'] for r in results),native_programs_before=len(before),
            native_programs_after=len(current),new_program_hashes=sorted(current-before),
            fresh_application_counts=[{k:r[k] for k in ('task_name','count','passed')} for r in applied],
            all_documents_semantically_understood=False,autonomous_architecture_evolution_proven=False,
            agent_review_received=True)
    except Exception as exc:
        report.update(status='WITHHOLD',error=type(exc).__name__+':'+str(exc))
        raise
    finally:
        kernel.close();save(lesson,'summary',report)
    print(json.dumps(report,ensure_ascii=False),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--predecessor',type=Path,required=True);p.add_argument('--hive',type=Path,required=True)
    main(p.parse_args())
