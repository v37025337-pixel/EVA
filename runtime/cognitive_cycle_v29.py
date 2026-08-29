from __future__ import annotations
import asyncio, hashlib, json, os, pathlib, random, sqlite3, sys
from itertools import product
ROOT=pathlib.Path(__file__).resolve().parents[1]
PKG=ROOT/'runtime'/'yado_v29'
sys.path.insert(0,str(PKG))
from yado_bootstrap import bootstrap_integrity, load_active_kernel_class, MANIFEST_SHA256
if MANIFEST_SHA256!='caef2fc87022c61258ebfd131a862d4c6afe32c5e15826f3b1f44206b911c477':
    raise SystemExit('MANIFEST_CONSTANT_MISMATCH')
boot=bootstrap_integrity();K=load_active_kernel_class();db=ROOT/'runtime'/'yado_v29_external_cognitive.sqlite'
k=K(db_path=str(db))
seed=int(hashlib.sha256((os.environ.get('GITHUB_RUN_ID','0')+'|YADO-V29-COGNITIVE').encode()).hexdigest()[:12],16)
rng=random.Random(seed)
try:
    before=k.memory_count()
    # LOGIC: fresh 6-variable parity under a run-specific variable permutation.
    names=rng.sample(list('abcdef'),6);cases=[]
    for bits in product([False,True],repeat=6):
        x=dict(zip(names,bits));y=False
        for b in bits:y^=b
        cases.append((x,y))
    logic=k.logic_growth_synthesize(cases,max_nodes=17,max_signatures=524288)

    # THINKING: learn four context-conditioned precedence regimes, then test fresh action IDs.
    orders={(False,False):['OBSERVE','MODEL','TEST','ACT'],(True,False):['MODEL','OBSERVE','TEST','ACT'],(False,True):['OBSERVE','TEST','MODEL','ACT'],(True,True):['TEST','MODEL','OBSERVE','ACT']}
    train=[]
    for key,order in orders.items():
        for _ in range(4): train.append(({'urgent':key[0],'uncertain':key[1]},order))
    tmodel=k.thinking_growth_learn(train,threshold=.75,min_support=2,max_context_keys=2)
    thinking_hits=0;thinking_total=0
    for rep in range(5):
        for key,expected in orders.items():
            roles=list(expected);rng.shuffle(roles)
            actions=[{'id':f'blind-{rep}-{j}-{rng.randrange(10**9)}','role':role} for j,role in enumerate(roles)]
            ids=k.thinking_growth_plan(tmodel,{'urgent':key[0],'uncertain':key[1]},actions)
            by={a['id']:a['role'] for a in actions};got=[by[i] for i in ids]
            thinking_hits += got==expected; thinking_total+=1
    thinking_score=thinking_hits/thinking_total

    # INTELLIGENCE: strategy induction with informative cluster geometry + irrelevant features.
    centers=[(-2.2,-2.2),(-2.2,2.2),(2.2,-2.2),(2.2,2.2),(0,0),(0,3.8)]
    data=[]
    for _ in range(300):
        label=rng.randrange(len(centers));cx,cy=centers[label]
        x={'signal_x':rng.gauss(cx,.55),'signal_y':rng.gauss(cy,.55),'noise_a':rng.uniform(-4,4),'noise_b':rng.uniform(-4,4),'noise_c':rng.uniform(-4,4)}
        data.append((x,f'STRATEGY_{label}'))
    fit,val,revealed,blind=data[:150],data[150:210],data[:210],data[210:]
    intel=k.intelligence_growth_fit(fit,val,revealed)
    intel_hits=sum(k.intelligence_growth_predict(intel['model'],x)==y for x,y in blind)
    intelligence_score=intel_hits/len(blind)

    payload={'logic_accuracy':logic['accuracy'],'logic_backend':logic['meta'].get('backend'),'thinking_accuracy':thinking_score,'intelligence_accuracy':intelligence_score,'seed':seed,'manifest_sha256':MANIFEST_SHA256}
    memory_id=k.remember('GITHUB-V29-'+os.environ.get('GITHUB_RUN_ID','0'),'EXTERNAL_COGNITIVE_GROWTH_EXECUTION',payload)
    after=k.memory_count()
    os.environ['YADO_ALLOWED_DOMAINS']='example.com'
    net=asyncio.run(k.fetch_evidence('https://example.com',max_bytes=500000))
    with sqlite3.connect(db) as con: integrity=con.execute('PRAGMA integrity_check').fetchone()[0]
    state_sha=hashlib.sha256(k.state_path.read_bytes()).hexdigest()
    passed=(logic['accuracy']==1.0 and thinking_score==1.0 and intelligence_score>=.95 and after==before+1 and integrity=='ok' and state_sha=='1bee35d94b6e853700b86fafbe7bce5e0199a167f9b918b31de547cfc83be52b')
    receipt={
      'status':'EXTERNAL_COGNITIVE_GROWTH_PASS' if passed else 'EXTERNAL_COGNITIVE_GROWTH_FAIL',
      'pass':passed,'kernel_class':K.__name__,'kernel_profile':K.PROFILE,'manifest_sha256':MANIFEST_SHA256,
      'canonical_state_sha256':state_sha,'canonical_state_mutated':False,'python_execution':True,
      'host':'github_actions','event_driven':True,'background_daemon':False,'outbound_https':True,
      'outbound_probe_url':net['url'],'outbound_probe_sha256':net['sha256'],'sqlite_integrity':integrity,
      'logic':{'accuracy':logic['accuracy'],'backend':logic['meta'].get('backend'),'meta':logic['meta']},
      'thinking':{'accuracy':thinking_score,'blind_cases':thinking_total},
      'intelligence':{'accuracy':intelligence_score,'blind_cases':len(blind),'meta':intel['meta']},
      'learning_memory':{'before':before,'after':after,'memory_id':memory_id,'closed_loop':after==before+1},
      'bootstrap':boot,'package_zip_sha256':'0db3328a95f2439cf5b534584d05cb5e0f1aefaf25bca217155e4c1c4087d5f7',
      'github_repository':os.environ.get('GITHUB_REPOSITORY'),'github_run_id':os.environ.get('GITHUB_RUN_ID'),'github_run_attempt':os.environ.get('GITHUB_RUN_ATTEMPT'),'github_sha':os.environ.get('GITHUB_SHA'),
      'claim_boundary':{'bounded_algorithmic_growth_only':True,'general_intelligence_proven':False,'foundation_weights_modified':False,'subjective_consciousness_claimed':False}
    }
finally:
    k.close()
out=ROOT/'runtime'/'cognitive_receipt_v29.json';out.write_text(json.dumps(receipt,indent=2,sort_keys=True),encoding='utf-8')
print('YADO_V29_COGNITIVE_RECEIPT='+json.dumps(receipt,sort_keys=True,separators=(',',':')))
if not receipt['pass']: raise SystemExit('COGNITIVE_GROWTH_GATE_FAILED')