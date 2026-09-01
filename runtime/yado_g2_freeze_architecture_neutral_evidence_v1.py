from __future__ import annotations
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parent; REPO=ROOT.parent; PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]
import yado_architecture_neutral_meta_synthesizer_v2 as neutral

BASE=REPO/'receipts/yado-architecture-neutral-meta-synth-v2-latest.json'
OUT=REPO/'resources/yado-architecture-neutral-evidence-corpus-frozen-v1.json'
REC=ROOT/'yado_g2_freeze_architecture_neutral_evidence_v1_receipt.json'
def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()

base=json.loads(BASE.read_text(encoding='utf-8'))
data=neutral.build_dataset(force=True)
expected={x['id']:x['sha256'] for x in base['source_digests']}
actual={sid:row['sha256'] for sid,row in data['rows'].items()}
if actual!=expected:
    raise RuntimeError('SOURCE_DIGEST_DRIFT:'+json.dumps({'expected':expected,'actual':actual},sort_keys=True))
cases=[{'key':c['key'],'x':c['x'],'y':c['y'],'counts':c['counts'],'bucket':c['bucket']} for c in data['cases']]
corpus={
 'schema':'yado.g2.architecture_neutral_evidence_corpus.frozen.v1',
 'status':'FROZEN_VERIFIED_HISTORY',
 'source_receipt':'receipts/yado-architecture-neutral-meta-synth-v2-latest.json',
 'source_digests':base['source_digests'],
 'case_counts':base['case_counts'],
 'cases':cases,
 'partition_rule':{'blind':'bucket<18','validation':'18<=bucket<38','fit':'38<=bucket<68','revealed':'bucket>=18'},
 'usage_invariant':'CREATION_MUST_FILTER bucket>=18; bucket<18 IS ADMISSION_ONLY',
}
corpus['corpus_digest']=h(corpus)
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(corpus,indent=2,sort_keys=True)+'\n',encoding='utf-8')
receipt={
 'schema':'yado.g2.freeze_architecture_neutral_evidence.receipt.v1','status':'PASS_FROZEN_VERIFIED_HISTORY',
 'corpus_digest':corpus['corpus_digest'],'case_count':len(cases),
 'source_count':len(expected),'source_digest_exact_match':True,
 'canonical_mutation':False,'ledger_mutation':False,'g3_genesis_performed':False,
}
receipt['receipt_sha256']=h(receipt)
REC.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n',encoding='utf-8')
print(json.dumps(receipt,indent=2,sort_keys=True))
