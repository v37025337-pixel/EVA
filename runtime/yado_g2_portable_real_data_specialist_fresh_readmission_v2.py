from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import copy
import hashlib
import json
import subprocess
import sys
import urllib.request

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_organ_runtime_native_v1 import tree_predict
from yado_unified_core_v1 import UnifiedYADOCoreV1

HEAD=REPO/'canonical/yado-main-head-g2.json'
CORE=REPO/'canonical/yado-unified-core-v1.json'
COG=REPO/'canonical/yado-g2-experience-conditioned-cognitive-layer-v4.json'
CAND=REPO/'candidates/kernel-self-generated/g2-portable-usgs-real-data-specialist-repair-v1.json'
PARENT=REPO/'receipts/yado-g2-fresh-real-data-cognitive-transfer-v1-run-34211495466.json'
REQ=REPO/'architecture/yado-g2-portable-real-data-specialist-fresh-readmission-v2-request.json'
OUT=ROOT/'yado_g2_portable_real_data_specialist_fresh_readmission_v2_receipt.json'
USGS_DAY='https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson'


def load(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))

def canon(o):
    return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)

def digest(o):
    return hashlib.sha256(canon(o).encode()).hexdigest()

def hbytes(b):
    return hashlib.sha256(b).hexdigest()

def candidate_digest(o):
    x=copy.deepcopy(o);x.pop('candidate_digest',None)
    return digest(x)

def fetch(url,timeout=30,max_bytes=8_000_000):
    req=urllib.request.Request(url,headers={'User-Agent':'YADO-G2-Portable-USGS-Readmission/2.0'})
    with urllib.request.urlopen(req,timeout=timeout) as r:
        body=r.read(max_bytes+1)
        if len(body)>max_bytes:raise RuntimeError('SOURCE_BYTE_BUDGET')
        return body,str(getattr(r,'url',url) or url),int(getattr(r,'status',200) or 200),str(r.headers.get('Content-Type') or '')

def balanced_acc(pred,truth):
    labels=sorted(set(truth),key=str);scores=[]
    for y in labels:
        idx=[i for i,t in enumerate(truth) if t==y]
        if idx:scores.append(sum(pred[i]==truth[i] for i in idx)/len(idx))
    return sum(scores)/len(scores) if scores else 0.0

head=load(HEAD);core_before=load(CORE);head_before=copy.deepcopy(head)
cog=load(COG);cand=load(CAND);parent=load(PARENT);req=load(REQ)

if req.get('expected_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('STALE_HEAD')
if req.get('expected_frontier')!=head.get('current_frontier'):raise RuntimeError('STALE_FRONTIER')
if int(req.get('expected_active_capability_count',-1))!=len(head.get('active_capabilities',[])):raise RuntimeError('STALE_CAPABILITIES')
if head.get('g3_genesis_performed') is not False:raise RuntimeError('G3_ALREADY_STARTED')
if cand.get('status')!='SHADOW_READY':raise RuntimeError('CANDIDATE_NOT_SHADOW_READY')
if cand.get('candidate_digest')!=candidate_digest(cand):raise RuntimeError('CANDIDATE_DIGEST_DRIFT')
if parent.get('status')!='PASS_WITH_LIMITATIONS_SHADOW_G2_FRESH_REAL_DATA_COGNITIVE_TRANSFER_V1':raise RuntimeError('PARENT_TRANSFER_PASS_REQUIRED')
if (parent.get('portable_usgs_shadow_repair') or {}).get('candidate_digest')!=cand.get('candidate_digest'):raise RuntimeError('PARENT_CANDIDATE_BINDING_MISMATCH')

# Candidate persistence commit is the temporal boundary. Only events strictly newer
# than this commit can count as readmission evidence.
try:
    commit_time_s=subprocess.check_output(
      ['git','log','-1','--format=%cI','--',str(CAND.relative_to(REPO))],cwd=REPO,text=True
    ).strip()
    commit_time=datetime.fromisoformat(commit_time_s.replace('Z','+00:00'))
except Exception as e:
    raise RuntimeError('CANDIDATE_COMMIT_TIME_UNAVAILABLE') from e
cutoff_ms=int(commit_time.timestamp()*1000)

body,resolved,http_status,ctype=fetch(USGS_DAY)
source_sha=hbytes(body)
obj=json.loads(body.decode('utf-8','replace'))
rows=[]
for f in obj.get('features') or []:
    p=f.get('properties') or {};g=f.get('geometry') or {};coords=g.get('coordinates') or []
    try:
        tm=int(p.get('time'));mag=float(p.get('mag'));sig=float(p.get('sig'));depth=float(coords[2])
    except (TypeError,ValueError,IndexError):continue
    if tm<=cutoff_ms:continue
    rows.append({
      'id':str(f.get('id')),'time':tm,'mag':mag,'sig':sig,'depth':depth,
      'tsunami':bool(p.get('tsunami')),'felt_any':(p.get('felt') or 0)>0,
      'reviewed':str(p.get('status'))=='reviewed'
    })
rows=sorted(rows,key=lambda x:(x['time'],x['id']))

ft=cand.get('feature_transform') or {}
tc=cand.get('target_contract') or {}
required_transform={'mag_q75','depth_shallow_lt','depth_very_shallow_lt','boolean_fields','output_features','threshold_source'}
if not required_transform.issubset(ft):raise RuntimeError('PORTABLE_PREPROCESSING_CONTRACT_INCOMPLETE')
if tc.get('field')!='sig' or tc.get('operator')!='>=' or 'sig_q75' not in tc:raise RuntimeError('TARGET_CONTRACT_INCOMPLETE')
if ft.get('threshold_source')!='FIT_PARTITION_ONLY' or tc.get('threshold_source')!='FIT_PARTITION_ONLY':raise RuntimeError('THRESHOLD_PROVENANCE_NOT_BOUND')

def transform(raw):
    return {
      'mag_ge_q75':float(raw['mag'])>=float(ft['mag_q75']),
      'shallow':float(raw['depth'])<float(ft['depth_shallow_lt']),
      'very_shallow':float(raw['depth'])<float(ft['depth_very_shallow_lt']),
      'tsunami':bool(raw['tsunami']),
      'felt_any':bool(raw['felt_any']),
      'reviewed':bool(raw['reviewed']),
    }

def oracle(raw):
    return float(raw['sig'])>=float(tc['sig_q75'])

# Independent replay: serialize candidate, reload, and run the same declarative contract.
reloaded=json.loads(json.dumps(cand,sort_keys=True))
ft2=reloaded['feature_transform'];tc2=reloaded['target_contract']
def transform_reloaded(raw):
    return {
      'mag_ge_q75':float(raw['mag'])>=float(ft2['mag_q75']),
      'shallow':float(raw['depth'])<float(ft2['depth_shallow_lt']),
      'very_shallow':float(raw['depth'])<float(ft2['depth_very_shallow_lt']),
      'tsunami':bool(raw['tsunami']),
      'felt_any':bool(raw['felt_any']),
      'reviewed':bool(raw['reviewed']),
    }

features=[transform(r) for r in rows]
features2=[transform_reloaded(r) for r in rows]
truth=[oracle(r) for r in rows]
pred=[bool(tree_predict(cand['model'],x)) for x in features]
pred2=[bool(tree_predict(reloaded['model'],x)) for x in features2]
fresh_balanced=balanced_acc(pred,truth) if rows else 0.0

class_counts={str(k).lower():v for k,v in Counter(truth).items()}
maj=Counter(truth).most_common(1)[0][0] if truth else False
baseline_balanced=balanced_acc([maj]*len(truth),truth) if truth else 0.0
causal_gain=fresh_balanced-baseline_balanced

# Preprocessing ablation: remove learned q75 meaning by forcing the critical feature false.
ablated_features=[dict(x,mag_ge_q75=False) for x in features]
ablated_pred=[bool(tree_predict(cand['model'],x)) for x in ablated_features]
preprocess_ablation=balanced_acc(ablated_pred,truth) if rows else 0.0
preprocess_causal_drop=fresh_balanced-preprocess_ablation

# Verify the tree actually consumes only declared transformed features.
def model_features(model):
    out=set();stack=[model]
    while stack:
        n=stack.pop()
        if not isinstance(n,dict):continue
        if 'feature' in n:out.add(str(n['feature']))
        if isinstance(n.get('left'),dict):stack.append(n['left'])
        if isinstance(n.get('right'),dict):stack.append(n['right'])
    return sorted(out)
used=model_features(cand.get('model') or {})
declared=sorted(str(x) for x in ft.get('output_features') or [])

# Legacy canonical specialist must still be distinguishable and not silently treated as portable.
legacy=((cog.get('real_data_genes') or {}).get('LOGIC') or {})
legacy_portable=bool(legacy.get('feature_transform') or legacy.get('preprocessing') or legacy.get('input_contract'))

core=UnifiedYADOCoreV1(REPO);core_audit=core.audit()

checks={
  'candidate_digest_verified':cand.get('candidate_digest')==candidate_digest(cand),
  'candidate_unchanged_from_parent':(parent.get('portable_usgs_shadow_repair') or {}).get('candidate_digest')==cand.get('candidate_digest'),
  'fresh_source_changed_from_candidate_training':source_sha!=cand.get('source_sha256'),
  'fresh_events_post_candidate_ge_12':len(rows)>=12,
  'fresh_both_classes_ge_2':min(Counter(truth).values())>=2 if len(set(truth))==2 else False,
  'fresh_balanced_ge_0_90':fresh_balanced>=.90,
  'fresh_causal_gain_ge_0_25':causal_gain>=.25,
  'preprocessing_replay_exact':features==features2 and pred==pred2,
  'preprocessing_causal_drop_ge_0_25':preprocess_causal_drop>=.25,
  'model_features_declared':all(x in declared for x in used),
  'thresholds_bound_and_frozen':float(ft['mag_q75'])==2.57 and float(tc['sig_q75'])==102.0,
  'legacy_portability_gap_still_visible':legacy_portable is False,
  'core_self_audit_pass':core_audit.get('pass') is True,
  'canonical_head_unchanged':load(HEAD).get('canonical_head_digest')==head_before.get('canonical_head_digest'),
  'canonical_core_unchanged':load(CORE)==core_before,
  'frontier_unchanged':load(HEAD).get('current_frontier')==req.get('expected_frontier'),
  'active_capabilities_31':len(load(HEAD).get('active_capabilities',[]))==31,
  'g3_not_started':load(HEAD).get('g3_genesis_performed') is False,
  'automatic_promotion_forbidden':cand.get('automatic_canonical_promotion') is False,
}
passed=all(checks.values())
status='PASS_SHADOW_G2_PORTABLE_REAL_DATA_SPECIALIST_FRESH_READMISSION_V2' if passed else 'WITHHOLD_G2_PORTABLE_REAL_DATA_SPECIALIST_FRESH_READMISSION_V2'

receipt={
  'schema':'yado.g2.portable_real_data_specialist_fresh_readmission.receipt.v2',
  'status':status,
  'generation':head.get('generation_id'),
  'frontier':head.get('current_frontier'),
  'canonical_head_digest':head.get('canonical_head_digest'),
  'active_capability_count':len(head.get('active_capabilities',[])),
  'candidate_path':str(CAND.relative_to(REPO)),
  'candidate_digest':cand.get('candidate_digest'),
  'candidate_source_sha256':cand.get('source_sha256'),
  'candidate_commit_time':commit_time_s,
  'fresh_source':{
    'url':USGS_DAY,'resolved_url':resolved,'http_status':http_status,'content_type':ctype,
    'bytes':len(body),'sha256':source_sha,'feed_generated':(obj.get('metadata') or {}).get('generated')
  },
  'fresh_temporal_evidence':{
    'cutoff_ms':cutoff_ms,'post_candidate_event_count':len(rows),
    'first_event_time':rows[0]['time'] if rows else None,'last_event_time':rows[-1]['time'] if rows else None,
    'class_counts':class_counts,
  },
  'portable_contract':{
    'feature_transform':copy.deepcopy(ft),'target_contract':copy.deepcopy(tc),
    'model_features':used,'declared_output_features':declared,
  },
  'metrics':{
    'fresh_balanced':fresh_balanced,'majority_baseline_balanced':baseline_balanced,'causal_gain':causal_gain,
    'preprocessing_ablation_balanced':preprocess_ablation,'preprocessing_causal_drop':preprocess_causal_drop,
  },
  'checks':checks,
  'canonical_mutation':False,
  'promotion_applied':False,
  'generation_transition':False,
  'g3_genesis_performed':False,
  'next_required_capability':'G2_PORTABLE_REAL_DATA_SPECIALIST_CANONICAL_INTEGRATION_V1' if passed else 'G2_PORTABLE_REAL_DATA_SPECIALIST_READMISSION_REPAIR_V3',
  'semantic_boundary':'UNCHANGED PORTABLE USGS SHADOW CANDIDATE IS REPLAYED ON RAW USGS EVENTS STRICTLY NEWER THAN ITS PERSISTENCE COMMIT. PREPROCESSING AND TARGET THRESHOLDS ARE READ ONLY FROM THE CANDIDATE CONTRACT. NO RETRAINING, CANONICAL MUTATION, PROMOTION OR G3 TRANSITION.',
}
receipt['receipt_sha256']=digest(receipt)
OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps(receipt,indent=2,sort_keys=True,default=str))
