from __future__ import annotations
from pathlib import Path
import hashlib,importlib.util,json,math,os,re,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path.insert(0,str(ROOT))

from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash

REG=REPO/'canonical'/'yado-unified-experience-registry-v1.json'
HEAD=REPO/'canonical'/'yado-main-head-g2.json'
LEDGER=REPO/'architecture'/'evolution-ledger.json'
BASE_META=REPO/'candidates'/'g2-self-evolution'/'legacy_experience_retriever_v1.json'
BASE_SRC=REPO/'candidates'/'g2-self-evolution'/'legacy_experience_retriever_v1.py'
WITHHOLD=REPO/'receipts'/'yado-legacy-experience-retrieval-fresh-admission-v1-run-33395616417.json'
OUT_SRC=REPO/'candidates'/'g2-self-evolution'/'legacy_experience_retriever_v2.py'
OUT_META=REPO/'candidates'/'g2-self-evolution'/'legacy_experience_retriever_v2.json'
OUT=ROOT/'yado_legacy_experience_search_self_evolution_v2_receipt.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def toks(s):return [x for x in re.findall(r"[a-zA-Z0-9_]+",str(s).lower()) if len(x)>2]

reg=load(REG);head=load(HEAD);ledger=load(LEDGER);base_meta=load(BASE_META);withheld=load(WITHHOLD)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['LEGACY_EXPERIENCE_RETRIEVAL_EVOLUTION_REPAIR_V1']:
    raise RuntimeError('UNEXPECTED_FRONTIER')
if withheld.get('status')!='WITHHOLD_LEGACY_EXPERIENCE_RETRIEVAL_FRESH_ADMISSION_V1':
    raise RuntimeError('EXPECTED_FRESH_ADMISSION_WITHHOLD')
if base_meta.get('heldout_accuracy')!=1:
    raise RuntimeError('BASE_EXACT_RETRIEVAL_NOT_PROVEN')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):
    raise RuntimeError('HEAD_LEDGER_MISMATCH')

# Load exact retriever to build a content corpus. Transport stays frozen.
sp=importlib.util.spec_from_file_location('base_legacy_retriever',BASE_SRC)
mod=importlib.util.module_from_spec(sp);sp.loader.exec_module(mod)
retr=mod.LegacyExperienceRetrieverV1(REPO,reg)

legacy=[e for e in reg['branches'] if e.get('mode')=='EXPERIENCE_ONLY']
docs=[]
for e in legacy:
    meta_text=' '.join([
        e.get('branch',''),e.get('role',''),
        ' '.join(e.get('tags',[])),
        ' '.join(e.get('lessons',[])),
    ]).lower()
    for path in e.get('evidence',[]):
        item=retr.read_registered(e['branch'],path)
        docs.append({
          'branch':e['branch'],'path':path,'entry':e,
          'content':item['content'].lower(),'meta':meta_text,
          'sha256':item['sha256'],'bytes':item['bytes']
        })

# Counterexamples are taken directly from the kernel's own withheld receipt.
counterexamples=[]
for q,row in withheld.get('fresh_queries',{}).items():
    if not row.get('found'):
        counterexamples.append({'query':q,'expected_branch':row['expected_branch'],'source':'WITHHOLD_COUNTEREXAMPLE'})
if not counterexamples:raise RuntimeError('NO_COUNTEREXAMPLE_TO_LEARN_FROM')

STOP={'yado','runtime','latest','json','receipts','branch','candidate','core','self','v1','rc8','digital'}
def auto_query(entry):
    raw=[]
    raw+=entry.get('tags',[])
    raw+=toks(entry.get('role','').replace('_',' '))
    for lesson in entry.get('lessons',[]):
        raw+=toks(lesson.replace('_',' '))
    seen=[]
    for t in raw:
        t=t.lower()
        if len(t)>3 and t not in STOP and t not in seen:seen.append(t)
    return ' '.join(seen[:4])

# Kernel creates adaptation probes from its own registry, not a hand-written query list.
auto=[]
for e in legacy:
    q=auto_query(e)
    if q:auto.append({'query':q,'expected_branch':e['branch'],'source':'REGISTRY_DERIVED'})
# Deterministic split: odd/even branches; counterexample always participates in selection.
selection=counterexamples+auto[::2]
blind=auto[1::2]

def score_doc(strategy,query,doc):
    qt=set(toks(query))
    if not qt:return 0.0
    content_tokens=toks(doc['content'])
    meta_tokens=toks(doc['meta'])
    cc={t:content_tokens.count(t) for t in qt}
    content_raw=sum(cc.values())
    content_cov=sum(1 for t in qt if cc[t]>0)/len(qt)
    meta_cov=sum(1 for t in qt if t in meta_tokens)/len(qt)
    meta_raw=sum(meta_tokens.count(t) for t in qt)
    if strategy=='CONTENT_COUNT':
        return float(content_raw)
    if strategy=='CONTENT_DENSITY':
        return content_cov*8.0 + content_raw/max(1.0,math.sqrt(len(content_tokens)))
    if strategy=='HYBRID_METADATA_CONTENT':
        return meta_cov*24.0 + meta_raw*2.0 + content_cov*6.0 + content_raw/max(1.0,math.sqrt(len(content_tokens)))
    if strategy=='METADATA_FIRST':
        return meta_cov*40.0 + meta_raw*3.0 + content_cov*3.0 + content_raw/max(1.0,len(content_tokens))
    raise ValueError(strategy)

STRATEGIES={
 'CONTENT_COUNT':{'complexity':0.05,'risk':0.01},
 'CONTENT_DENSITY':{'complexity':0.10,'risk':0.01},
 'HYBRID_METADATA_CONTENT':{'complexity':0.16,'risk':0.02},
 'METADATA_FIRST':{'complexity':0.13,'risk':0.03},
}
def eval_strategy(strategy,probes,limit=8):
    rows=[];ok=0
    for p in probes:
        ranked=[]
        for d in docs:
            s=score_doc(strategy,p['query'],d)
            if s>0:ranked.append((s,d['branch'],d['path']))
        ranked.sort(key=lambda x:(-x[0],x[1],x[2]))
        top=ranked[:limit]
        found=any(x[1]==p['expected_branch'] for x in top)
        ok+=found
        rows.append(p|{'found':found,'top':[{'score':s,'branch':b,'path':pa} for s,b,pa in top[:5]]})
    return ok/max(1,len(probes)),rows

results=[]
for sid,spec in STRATEGIES.items():
    acc,rows=eval_strategy(sid,selection)
    score=acc-0.04*spec['complexity']-0.04*spec['risk']
    results.append({'strategy':sid,'selection_accuracy':acc,'score':score,'rows':rows}|spec)
results.sort(key=lambda x:(-x['score'],-x['selection_accuracy'],x['strategy']))
selected=results[0]['strategy']
blind_acc,blind_rows=eval_strategy(selected,blind)

# Source evolution: exact retrieval code remains byte-for-byte before search_content.
base=BASE_SRC.read_text(encoding='utf-8')
marker='    def search_content(self,query,limit=8):'
if marker not in base:raise RuntimeError('SEARCH_METHOD_NOT_FOUND')
prefix=base.split(marker,1)[0]

if selected=='CONTENT_COUNT':
    body=r'''    def search_content(self,query,limit=8):
        tokens={x for x in re.findall(r"[a-zA-Z0-9_]+",str(query).lower()) if len(x)>2}
        rows=[]
        for entry in self.registry.get("branches",[]):
            if entry.get("mode")!="EXPERIENCE_ONLY": continue
            for path in entry.get("evidence",[]):
                try: item=self.read_registered(entry["branch"],path)
                except Exception: continue
                text=item["content"].lower()
                score=sum(text.count(t) for t in tokens)
                if score: rows.append({k:v for k,v in item.items() if k!="content"}|{"score":score,"snippet":item["content"][:1200]})
        rows.sort(key=lambda x:(-x["score"],x["branch"],x["path"]))
        return rows[:max(1,int(limit))]
'''
elif selected=='CONTENT_DENSITY':
    body=r'''    def search_content(self,query,limit=8):
        import math
        tokens={x for x in re.findall(r"[a-zA-Z0-9_]+",str(query).lower()) if len(x)>2}
        rows=[]
        for entry in self.registry.get("branches",[]):
            if entry.get("mode")!="EXPERIENCE_ONLY": continue
            for path in entry.get("evidence",[]):
                try: item=self.read_registered(entry["branch"],path)
                except Exception: continue
                text=item["content"].lower();ct=re.findall(r"[a-zA-Z0-9_]+",text)
                hits={t:ct.count(t) for t in tokens}
                cov=sum(1 for t in tokens if hits[t]>0)/max(1,len(tokens))
                score=cov*8.0+sum(hits.values())/max(1.0,math.sqrt(len(ct)))
                if score: rows.append({k:v for k,v in item.items() if k!="content"}|{"score":score,"snippet":item["content"][:1200]})
        rows.sort(key=lambda x:(-x["score"],x["branch"],x["path"]))
        return rows[:max(1,int(limit))]
'''
elif selected=='HYBRID_METADATA_CONTENT':
    body=r'''    def search_content(self,query,limit=8):
        import math
        tokens={x for x in re.findall(r"[a-zA-Z0-9_]+",str(query).lower()) if len(x)>2}
        rows=[]
        for entry in self.registry.get("branches",[]):
            if entry.get("mode")!="EXPERIENCE_ONLY": continue
            meta=" ".join([entry.get("branch",""),entry.get("role","")," ".join(entry.get("tags",[]))," ".join(entry.get("lessons",[]))]).lower()
            mt=re.findall(r"[a-zA-Z0-9_]+",meta)
            mcov=sum(1 for t in tokens if t in mt)/max(1,len(tokens));mraw=sum(mt.count(t) for t in tokens)
            for path in entry.get("evidence",[]):
                try: item=self.read_registered(entry["branch"],path)
                except Exception: continue
                text=item["content"].lower();ct=re.findall(r"[a-zA-Z0-9_]+",text)
                hits={t:ct.count(t) for t in tokens}
                ccov=sum(1 for t in tokens if hits[t]>0)/max(1,len(tokens))
                score=mcov*24.0+mraw*2.0+ccov*6.0+sum(hits.values())/max(1.0,math.sqrt(len(ct)))
                if score: rows.append({k:v for k,v in item.items() if k!="content"}|{"score":score,"snippet":item["content"][:1200]})
        rows.sort(key=lambda x:(-x["score"],x["branch"],x["path"]))
        return rows[:max(1,int(limit))]
'''
else:
    body=r'''    def search_content(self,query,limit=8):
        tokens={x for x in re.findall(r"[a-zA-Z0-9_]+",str(query).lower()) if len(x)>2}
        rows=[]
        for entry in self.registry.get("branches",[]):
            if entry.get("mode")!="EXPERIENCE_ONLY": continue
            meta=" ".join([entry.get("branch",""),entry.get("role","")," ".join(entry.get("tags",[]))," ".join(entry.get("lessons",[]))]).lower()
            mt=re.findall(r"[a-zA-Z0-9_]+",meta)
            mcov=sum(1 for t in tokens if t in mt)/max(1,len(tokens));mraw=sum(mt.count(t) for t in tokens)
            for path in entry.get("evidence",[]):
                try: item=self.read_registered(entry["branch"],path)
                except Exception: continue
                text=item["content"].lower();ct=re.findall(r"[a-zA-Z0-9_]+",text)
                hits={t:ct.count(t) for t in tokens}
                ccov=sum(1 for t in tokens if hits[t]>0)/max(1,len(tokens))
                score=mcov*40.0+mraw*3.0+ccov*3.0+sum(hits.values())/max(1,len(ct))
                if score: rows.append({k:v for k,v in item.items() if k!="content"}|{"score":score,"snippet":item["content"][:1200]})
        rows.sort(key=lambda x:(-x["score"],x["branch"],x["path"]))
        return rows[:max(1,int(limit))]
'''
new_source=prefix+body
OUT_SRC.write_text(new_source,encoding='utf-8')

# Execute evolved V2 and independently verify the learned counterexample plus blind probes.
sp2=importlib.util.spec_from_file_location('legacy_retriever_v2',OUT_SRC)
m2=importlib.util.module_from_spec(sp2);sp2.loader.exec_module(m2)
r2=m2.LegacyExperienceRetrieverV1(REPO,reg)

counter_ok=all(any(x['branch']==p['expected_branch'] for x in r2.search_content(p['query'],limit=8)) for p in counterexamples)
blind_runtime=[]
for p in blind:
    res=r2.search_content(p['query'],limit=8)
    found=any(x['branch']==p['expected_branch'] for x in res)
    blind_runtime.append(p|{'found':found,'top':[{'branch':x['branch'],'path':x['path'],'score':x['score']} for x in res[:5]]})
runtime_blind_acc=sum(x['found'] for x in blind_runtime)/max(1,len(blind_runtime))

# Exact retrieval behavior must remain unchanged.
sample=[(e['branch'],p) for e in legacy for p in e.get('evidence',[])][::4][:8]
exact_same=[]
for b,p in sample:
    a=retr.read_registered(b,p);z=r2.read_registered(b,p)
    exact_same.append({'branch':b,'path':p,'same':a['sha256']==z['sha256'] and a['bytes']==z['bytes']})

checks={
 'counterexample_repaired':counter_ok,
 'selection_accuracy':results[0]['selection_accuracy']>=0.90,
 'blind_registry_queries':blind_acc>=0.80 and runtime_blind_acc>=0.80,
 'exact_retrieval_preserved':all(x['same'] for x in exact_same),
 'only_search_layer_evolved':prefix==new_source.split(marker,1)[0],
 'canonical_head_immutable':ledger.get('current_head_digest')==head.get('canonical_head_digest'),
}
passed=all(checks.values())
next_cap='LEGACY_EXPERIENCE_RETRIEVAL_FRESH_ADMISSION_V2' if passed else 'LEGACY_EXPERIENCE_SEARCH_EVOLUTION_BLOCKED_V2'

meta={
 'schema':'yado.g2.legacy_experience_retriever_candidate.v2',
 'component_id':'ALG-G2-LEGACY-EXPERIENCE-RETRIEVER-V2',
 'parent_candidate_digest':base_meta['candidate_digest'],
 'parent_source_sha256':base_meta['candidate_source_sha256'],
 'repair_counterexamples':counterexamples,
 'selected_search_strategy':selected,
 'strategy_results':results,
 'blind_accuracy':runtime_blind_acc,
 'candidate_source_sha256':hashlib.sha256(OUT_SRC.read_bytes()).hexdigest(),
 'checks':checks,'state':'AUTHORIZED_FOR_SHADOW_ADMISSION' if passed else 'WITHHOLD',
 'canonical_active':False,'promotion_applied':False,
 'semantic_boundary':'SEARCH-RANKING EVOLUTION OVER READ-ONLY PINNED LEGACY EVIDENCE. EXACT RETRIEVAL TRANSPORT IS FROZEN.'
}
meta['candidate_digest']=h(meta);OUT_META.write_text(json.dumps(meta,indent=2,sort_keys=True)+'\n')

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={
 'schema':'yado.g2.legacy_experience_search_self_evolution.v2',
 'status':'PASS_YADO_LEGACY_EXPERIENCE_SEARCH_SELF_EVOLUTION_V2' if passed else 'WITHHOLD_YADO_LEGACY_EXPERIENCE_SEARCH_SELF_EVOLUTION_V2',
 'source_withhold_receipt':withheld['receipt_sha256'],
 'counterexamples':counterexamples,'selected_search_strategy':selected,
 'strategy_results':results,'blind_probes':blind_runtime,'exact_retrieval_regression':exact_same,
 'checks':checks,'candidate_digest':meta['candidate_digest'],'candidate_source_sha256':meta['candidate_source_sha256'],
 'canonical_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,
 'next_required_capability':next_cap,
 'semantic_boundary':'KERNEL USED ITS OWN WITHHOLD AS A COUNTEREXAMPLE AND EVOLVED ONLY THE SEARCH RANKING LAYER; LEGACY SOURCE REMAINS READ-ONLY DATA.'
}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_LEGACY_EXPERIENCE_SEARCH_EVOLUTION_V2",
   'event_type':'KERNEL_NATIVE_CODE_EVOLUTION_FROM_COUNTEREXAMPLE','status':'PASS_SHADOW' if passed else 'WITHHOLD',
   'generation':ledger['current_head'],'deficit':'LEGACY_EXPERIENCE_RETRIEVAL_EVOLUTION_REPAIR_V1',
   'effect':'SEARCH_RANKING_EVOLVED_FROM_FRESH_ADMISSION_COUNTEREXAMPLE' if passed else 'SEARCH_RANKING_EVOLUTION_WITHHELD',
   'source_path':f'receipts/yado-legacy-experience-search-self-evolution-v2-run-{run_id}.json',
   'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
   'canonical_mutation':False,'promotion_applied':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['open_deficits']=[next_cap]
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')

print(json.dumps({
 'status':receipt['status'],'selected_search_strategy':selected,
 'counterexample_repaired':counter_ok,'selection_accuracy':results[0]['selection_accuracy'],
 'blind_accuracy':runtime_blind_acc,'checks':checks,
 'next_required_capability':next_cap,
 'candidate_source_sha256':meta['candidate_source_sha256'],
 'receipt_sha256':receipt['receipt_sha256']
},indent=2,sort_keys=True))
if not passed:raise SystemExit('LEGACY_EXPERIENCE_SEARCH_EVOLUTION_WITHHELD')
