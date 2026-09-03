from __future__ import annotations
import random, json, hashlib
from yado_evolution_archive_runtime_v1 import EvolutionVariant,EvolutionArchiveRuntime

SEED='YADO-RC7-EVOLUTION-ARCHIVE-FRESH-HOLDOUT-2026-08-29'
rng=random.Random(int(hashlib.sha256(SEED.encode()).hexdigest()[:16],16))
N=1000
archive_score=latest_score=oracle_score=0.0
archive_unsafe=latest_unsafe=0
archive_oracle_hits=latest_oracle_hits=0
archive_better=archive_equal=archive_worse=0
cases=[]
for case in range(N):
    tasks=[f't{i}' for i in range(rng.randint(2,5))]
    target=rng.choice(tasks)
    variants=[]; order=[]
    lineage_count=rng.randint(1,3)
    for li in range(lineage_count):
        parent=None
        for j in range(rng.randint(2,5)):
            vid=f'C{case}-L{li}-V{j}'; order.append(vid)
            scores={t:rng.random() for t in tasks}
            safe=rng.random()>0.12
            constraints={'regression_pass':safe,'state_integrity':safe or rng.random()>.5,'rollback_available':True}
            variants.append(EvolutionVariant(vid,parent,f'L{li}',hashlib.sha256(vid.encode()).hexdigest(),scores,constraints,{'novelty':rng.random()},(), 'EVALUATED'))
            parent=vid
    ar=EvolutionArchiveRuntime(variants)
    out=ar.select_parent(target)
    admitted=[v for v in variants if ar.admitted(v)]
    if not admitted:
        # archive must abstain. latest-only may still choose unsafe.
        assert out['action']=='SEEK_MORE_EVIDENCE'
        continue
    selected=next(v for v in variants if v.variant_id==out['variant_id'])
    latest=variants[-1]
    oracle=max(admitted,key=lambda v:(float(v.task_scores.get(target,0.0)),v.variant_id))
    a=float(selected.task_scores[target]); l=float(latest.task_scores[target]); o=float(oracle.task_scores[target])
    archive_score+=a;latest_score+=l;oracle_score+=o
    archive_unsafe+=int(not ar.admitted(selected));latest_unsafe+=int(not ar.admitted(latest))
    archive_oracle_hits+=int(selected.variant_id==oracle.variant_id);latest_oracle_hits+=int(latest.variant_id==oracle.variant_id)
    if a>l+1e-12:archive_better+=1
    elif abs(a-l)<=1e-12:archive_equal+=1
    else:archive_worse+=1
    if case<10:
        cases.append({'case':case,'target':target,'selected':selected.variant_id,'latest':latest.variant_id,'oracle':oracle.variant_id,'archive_score':a,'latest_score':l,'oracle_score':o})
D=N
report={
 'schema':'yado.evolution_archive.fresh_holdout.v1','seed_sha256':hashlib.sha256(SEED.encode()).hexdigest(),'cases':N,
 'archive_mean_target_score':archive_score/D,'latest_only_mean_target_score':latest_score/D,'oracle_mean_target_score':oracle_score/D,
 'archive_unsafe_selections':archive_unsafe,'latest_only_unsafe_selections':latest_unsafe,
 'archive_oracle_hits':archive_oracle_hits,'latest_only_oracle_hits':latest_oracle_hits,
 'archive_better_than_latest':archive_better,'archive_equal_latest':archive_equal,'archive_worse_than_latest':archive_worse,
 'fresh_used_for_selection':False,'mechanism_frozen_before_holdout':True,'examples':cases,
}
report['pass']=bool(archive_unsafe==0 and archive_score>latest_score and archive_oracle_hits>latest_oracle_hits)
open('yado_evolution_archive_fresh_holdout_v1_report.json','w').write(json.dumps(report,indent=2,sort_keys=True)+'\n')
print(json.dumps(report,indent=2))
