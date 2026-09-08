from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
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
V2=REPO/'receipts/yado-g2-portable-real-data-specialist-fresh-readmission-v2-run-34222746443-withhold.json'
REQ=REPO/'architecture/yado-g2-portable-real-data-specialist-readmission-repair-v3-request.json'
OUT=ROOT/'yado_g2_portable_real_data_specialist_readmission_repair_v3_receipt.json'
USGS_QUERY='https://earthquake.usgs.gov/fdsnws/event/1/query'


def load(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))

def canon(o):
    return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)

def digest(o):
    return hashlib.sha256(canon(o).encode()).hexdigest()

def candidate_digest(o):
    x=copy.deepcopy(o);x.pop('candidate_digest',None)
    return digest(x)

def fetch(url,timeout=35,max_bytes=12_000_000):
    req=urllib.request.Request(url,headers={'User-Agent':'YADO-G2-Portable-USGS-Readmission/3.0'})
    with urllib.request.urlopen(req,timeout=timeout) as r:
        body=r.read(max_bytes+1)
        if len(body)>max_bytes:raise RuntimeError('SOURCE_BYTE_BUDGET')
        return body,str(getattr(r,'url',url) or url),int(getattr(r,'status',200) or 200),str(r.headers.get('Content-Type') or '')

def hbytes(b):
    return hashlib.sha256(b).hexdigest()

def balanced_acc(pred,truth):
    labels=sorted(set(truth),key=str);scores=[]
    for y in labels:
        idx=[i for i,t in enumerate(truth) if t==y]
        if idx:scores.append(sum(pred[i]==truth[i] for i in idx)/len(idx))
    return sum(scores)/len(scores) if scores else 0.0

head=load(HEAD);core_before=load(CORE);head_before=copy.deepcopy(head)
cog=load(COG);cand=load(CAND);v2=load(V2);req=load(REQ)

if req.get('expected_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('STALE_HEAD')
if req.get('expected_frontier')!=head.get('current_frontier'):raise RuntimeError('STALE_FRONTIER')
if int(req.get('expected_active_capability_count',-1))!=len(head.get('active_capabilities',[])):raise RuntimeError('STALE_CAPABILITIES')
if head.get('g3_genesis_performed') is not False:raise RuntimeError('G3_ALREADY_STARTED')
if cand.get('status')!='SHADOW_READY':raise RuntimeError('CANDIDATE_NOT_READY')
if cand.get('candidate_digest')!=candidate_digest(cand):raise RuntimeError('CANDIDATE_DIGEST_DRIFT')
if v2.get('status')!='WITHHOLD_G2_PORTABLE_REAL_DATA_SPECIALIST_FRESH_READMISSION_V2':raise RuntimeError('V2_WITHHOLD_REQUIRED')
if v2.get('diagnosis')!='INSUFFICIENT_POST_CANDIDATE_SAMPLE_SIZE_AND_CLASS_SUPPORT; NOT A MODEL_ACCURACY_FAILURE':raise RuntimeError('V2_CLASSIFICATION_MISMATCH')
if float((v2.get('metrics') or {}).get('fresh_balanced',0))<.90:raise RuntimeError('V2_QUALITY_FAILURE_NOT_SAMPLE_FAILURE')

try:
    commit_time_s=subprocess.check_output(
      ['git','log','-1','--format=%cI','--',str(CAND.relative_to(REPO))],cwd=REPO,text=True
    ).strip()
    commit_time=datetime.fromisoformat(commit_time_s.replace('Z','+00:00')).astimezone(timezone.utc)
except Exception as e:
    raise RuntimeError('CANDIDATE_COMMIT_TIME_UNAVAILABLE') from e

# Candidate source was an all_week feed captured at candidate construction.
# Pick a deterministic 72h interval ending eight days before persistence.
# This lies entirely before the maximum rolling-week coverage and therefore
# cannot overlap the source observations used to construct the candidate.
window_end=commit_time-timedelta(days=8)
window_start=window_end-timedelta(days=3)
def iso(dt):
    return dt.strftime('%Y-%m-%dT%H:%M:%S')
query=USGS_QUERY+'?'+urlencode({
  'format':'geojson',
  'starttime':iso(window_start),
  'endtime':iso(window_end),
  'orderby':'time-asc',
  'limit':'20000'
})
body,resolved,http_status,ctype=fetch(query)
source_sha=hbytes(body)
obj=json.loads(body.decode('utf-8','replace'))

rows=[]
for f in obj.get('features') or []:
    p=f.get('properties') or {};g=f.get('geometry') or {};coords=g.get('coordinates') or []
    try:
        tm=int(p.get('time'));mag=float(p.get('mag'));sig=float(p.get('sig'));depth=float(coords[2])
    except (TypeError,ValueError,IndexError):continue
    rows.append({
      'id':str(f.get('id')),'time':tm,'mag':mag,'sig':sig,'depth':depth,
      'tsunami':bool(p.get('tsunami')),'felt_any':(p.get('felt') or 0)>0,
      'reviewed':str(p.get('status'))=='reviewed'
    })
rows=sorted(rows,key=lambda x:(x['time'],x['id']))

ft=cand['feature_transform'];tc=cand['target_contract']
def transform(raw,contract=ft):
    return {
      'mag_ge_q75':float(raw['mag'])>=float(contract['mag_q75']),
      'shallow':float(raw['depth'])<float(contract['depth_shallow_lt']),
      'very_shallow':float(raw['depth'])<float(contract['depth_very_shallow_lt']),
      'tsunami':bool(raw['tsunami']),
      'felt_any':bool(raw['felt_any']),
      'reviewed':bool(raw['reviewed']),
    }
def oracle(raw,contract=tc):
    return float(raw['sig'])>=float(contract['sig_q75'])

features=[transform(r) for r in rows]
truth=[oracle(r) for r in rows]
pred=[bool(tree_predict(cand['model'],x)) for x in features]
fresh_balanced=balanced_acc(pred,truth) if rows else 0.0
counts=Counter(truth)
maj=counts.most_common(1)[0][0] if counts else False
baseline=balanced_acc([maj]*len(truth),truth) if rows else 0.0
causal_gain=fresh_balanced-baseline

# Candidate portability must depend on the bound learned preprocessing.
ablated=[dict(x,mag_ge_q75=False) for x in features]
ablation_pred=[bool(tree_predict(cand['model'],x)) for x in ablated]
ablation=balanced_acc(ablation_pred,truth) if rows else 0.0
preprocess_drop=fresh_balanced-ablation

# Independent replay from serialized candidate.
reloaded=json.loads(json.dumps(cand,sort_keys=True))
features2=[transform(r,reloaded['feature_transform']) for r in rows]
pred2=[bool(tree_predict(reloaded['model'],x)) for x in features2]

def model_features(model):
    out=set();stack=[model]
    while stack:
        n=stack.pop()
        if not isinstance(n,dict):continue
        if 'feature' in n:out.add(str(n['feature']))
        if isinstance(n.get('left'),dict):stack.append(n['left'])
        if isinstance(n.get('right'),dict):stack.append(n['right'])
    return sorted(out)
used=model_features(cand['model'])
declared=sorted(str(x) for x in ft.get('output_features') or [])

# Strict non-overlap proof with rolling seven-day source coverage.
candidate_coverage_start=commit_time-timedelta(days=7)
nonoverlap=window_end<=candidate_coverage_start

legacy=((cog.get('real_data_genes') or {}).get('LOGIC') or {})
legacy_portable=bool(legacy.get('feature_transform') or legacy.get('preprocessing') or legacy.get('input_contract'))
core=UnifiedYADOCoreV1(REPO);core_audit=core.audit()

checks={
  'v2_withhold_was_sample_only':v2.get('failed_checks')==['fresh_events_post_candidate_ge_12','fresh_both_classes_ge_2'],
  'candidate_digest_verified':cand.get('candidate_digest')==candidate_digest(cand),
  'candidate_unchanged_from_v2':cand.get('candidate_digest')==v2.get('candidate_digest'),
  'historical_window_strictly_outside_candidate_week':nonoverlap,
  'historical_holdout_events_ge_100':len(rows)>=100,
  'historical_holdout_both_classes_ge_10':len(counts)==2 and min(counts.values())>=10,
  'fresh_balanced_ge_0_90':fresh_balanced>=.90,
  'fresh_causal_gain_ge_0_25':causal_gain>=.25,
  'preprocessing_causal_drop_ge_0_25':preprocess_drop>=.25,
  'preprocessing_replay_exact':features==features2 and pred==pred2,
  'thresholds_frozen':float(ft['mag_q75'])==2.57 and float(tc['sig_q75'])==102.0,
  'model_features_declared':all(x in declared for x in used),
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
status='PASS_SHADOW_G2_PORTABLE_REAL_DATA_SPECIALIST_READMISSION_REPAIR_V3' if passed else 'WITHHOLD_G2_PORTABLE_REAL_DATA_SPECIALIST_READMISSION_REPAIR_V3'

receipt={
  'schema':'yado.g2.portable_real_data_specialist_readmission_repair.receipt.v3',
  'status':status,
  'generation':head.get('generation_id'),
  'frontier':head.get('current_frontier'),
  'canonical_head_digest':head.get('canonical_head_digest'),
  'active_capability_count':len(head.get('active_capabilities',[])),
  'candidate_path':str(CAND.relative_to(REPO)),
  'candidate_digest':cand.get('candidate_digest'),
  'candidate_commit_time':commit_time_s,
  'v2_withhold_receipt':str(V2.relative_to(REPO)),
  'v2_prospective_evidence':{
    'post_candidate_event_count':(v2.get('fresh_temporal_evidence') or {}).get('post_candidate_event_count'),
    'class_counts':(v2.get('fresh_temporal_evidence') or {}).get('class_counts'),
    'fresh_balanced':(v2.get('metrics') or {}).get('fresh_balanced'),
    'causal_gain':(v2.get('metrics') or {}).get('causal_gain'),
    'classification':v2.get('diagnosis'),
  },
  'disjoint_holdout':{
    'strategy':'DETERMINISTIC_PRE_ROLLING_WEEK_WINDOW',
    'candidate_coverage_start':candidate_coverage_start.isoformat(),
    'window_start':window_start.isoformat(),
    'window_end':window_end.isoformat(),
    'strict_nonoverlap':nonoverlap,
    'query_url':query,'resolved_url':resolved,'http_status':http_status,'content_type':ctype,
    'bytes':len(body),'sha256':source_sha,'event_count':len(rows),
    'class_counts':{str(k).lower():v for k,v in counts.items()},
    'first_event_time':rows[0]['time'] if rows else None,
    'last_event_time':rows[-1]['time'] if rows else None,
  },
  'metrics':{
    'fresh_balanced':fresh_balanced,'majority_baseline_balanced':baseline,'causal_gain':causal_gain,
    'preprocessing_ablation_balanced':ablation,'preprocessing_causal_drop':preprocess_drop,
  },
  'checks':checks,
  'thresholds_lowered':False,
  'candidate_retrained':False,
  'canonical_mutation':False,
  'promotion_applied':False,
  'generation_transition':False,
  'g3_genesis_performed':False,
  'next_required_capability':'G2_PORTABLE_REAL_DATA_SPECIALIST_CANONICAL_INTEGRATION_V1' if passed else 'G2_PORTABLE_REAL_DATA_SPECIALIST_READMISSION_REPAIR_V4',
  'semantic_boundary':'V3 PRESERVES THE V2 PROSPECTIVE WITHHOLD AND ADDS A DETERMINISTIC LARGE USGS HOLDOUT STRICTLY OUTSIDE THE ROLLING SEVEN-DAY SOURCE COVERAGE USED TO CONSTRUCT THE UNCHANGED CANDIDATE. THRESHOLDS AND MODEL ARE FROZEN. NO CANONICAL MUTATION OR PROMOTION.',
}
receipt['receipt_sha256']=digest(receipt)
OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps(receipt,indent=2,sort_keys=True,default=str))
