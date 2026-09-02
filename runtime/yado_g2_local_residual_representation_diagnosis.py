from __future__ import annotations
from pathlib import Path
import json,hashlib,copy,sys,math,statistics
ROOT=Path(__file__).resolve().parent; REPO=ROOT.parent; PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_organ_runtime_native_v1 import tree_predict
from yado_cognitive_growth_runtime_v1 import centroid_predict

def h(o):return hashlib.sha256(json.dumps(o,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def load(p):return json.loads(p.read_text())
base=load(REPO/'receipts/yado-architecture-neutral-meta-synth-v2-latest.json')
corpus=load(REPO/'resources/yado-architecture-neutral-evidence-corpus-frozen-v1.json')
cal=load(REPO/'candidates/kernel-self-generated/evolutionary-centroid-calibrated-successor-v2.json')
knn=load(REPO/'candidates/kernel-self-generated/evolutionary-local-knn-successor-v1.json')
hier=load(REPO/'candidates/kernel-self-generated/evolutionary-hierarchical-residual-successor-v1.json')
parent_model=base['kernel_result']['model']
g=cal['generator']; gate=g['gate_model']; corr=g['corrector_model']; th=float(cal['selected_threshold'])

def orig(x):return tree_predict(parent_model,x)
def dists(model,x):
    out=[]
    for ls,c in model['centroids'].items():
        d=0.0
        for k in model['features']:
            s=max(float(model['scales'].get(k,1)),1e-12)
            d+=((float(x.get(k,0))-float(c[k]))/s)**2
        out.append((d,ls))
    return sorted(out)
def margin(model,x):
    z=dists(model,x);return 0 if len(z)<2 else z[1][0]-z[0][0]
def best(x):
    if centroid_predict(gate,x)!='PARENT_ERROR':return orig(x)
    if margin(gate,x)+1e-12<th:return orig(x)
    return centroid_predict(corr,x)

nonblind=[c for c in corpus['cases'] if c['bucket']>=18]
res=[c for c in nonblind if best(c['x'])!=c['y']]
ok=[c for c in nonblind if best(c['x'])==c['y']]

# Exact representation collisions.
groups={}
for c in nonblind:
    k=h(c['x']);groups.setdefault(k,[]).append(c)
conf=[]
for k,rows in groups.items():
    labels=sorted(set(str(r['y']) for r in rows))
    if len(labels)>1:conf.append({'x_digest':k,'count':len(rows),'labels':labels,'residual_count':sum(best(r['x'])!=r['y'] for r in rows)})
res_conf=sum(x['residual_count'] for x in conf)

# Residual label distribution and support in successful rows.
labels={}
for c in res:
    y=str(c['y']);labels.setdefault(y,{'residual':0,'nonblind_total':0,'correct':0})
    labels[y]['residual']+=1
for c in nonblind:
    y=str(c['y']);labels.setdefault(y,{'residual':0,'nonblind_total':0,'correct':0})
    labels[y]['nonblind_total']+=1
    labels[y]['correct']+=int(best(c['x'])==c['y'])

# Generic nearest-neighbor geometry using all numeric feature dimensions, on nonblind only.
keys=sorted({k for c in nonblind for k,v in c['x'].items() if isinstance(v,(int,float,bool))})
def vec(x):return [float(x.get(k,0)) for k in keys]
def dist(a,b):return math.sqrt(sum((x-y)**2 for x,y in zip(a,b)))
nearest=[]
for r in res:
    rv=vec(r['x']); candidates=[]
    for c in ok:
        candidates.append((dist(rv,vec(c['x'])),str(c['y']),c['key']))
    candidates.sort()
    nearest.append({'case_key':r['key'],'expected':str(r['y']),'parent_pred':str(best(r['x'])),
                    'nearest_correct_distance':None if not candidates else candidates[0][0],
                    'nearest_correct_label':None if not candidates else candidates[0][1],
                    'nearest_correct_same_label_distance':next((d for d,y,_ in candidates if y==str(r['y'])),None),
                    'source_count':r['x'].get('source_count'),'entropy':r['x'].get('evidence_entropy_proxy')})

# Kernel chooses parent/op using latest variants.
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'yado_representation_diagnosis_control.sqlite'))
try:
    records=[
      {'variant_id':'EXECUTABLE_PARENT','parent_id':None,'lineage_id':'G2_SELECTOR_LINEAGE','artifact_digest':'parent',
       'task_scores':{'fresh_blind':.8043478260869565,'retention':1.0,'repair':0.0},
       'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},'traits':{'bounded':1.0},'failure_tags':['repair'],'status':'EVALUATED'},
      {'variant_id':'CALIBRATED_CHILD_V2','parent_id':'EXECUTABLE_PARENT','lineage_id':'G2_SELECTOR_LINEAGE','artifact_digest':cal['candidate_digest'],
       'task_scores':{'fresh_blind':float(cal['metrics']['fresh_blind_successor']),'retention':1.0,'repair':float(cal['metrics']['parent_error_repair_rate'])},
       'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},'traits':{'bounded':1.0,'calibrated':1.0},'failure_tags':['repair'],'status':'EVALUATED'},
      {'variant_id':'HIERARCHICAL_CHILD_V1','parent_id':'CALIBRATED_CHILD_V2','lineage_id':'G2_SELECTOR_LINEAGE','artifact_digest':hier['candidate_digest'],
       'task_scores':{'fresh_blind':float(hier['metrics']['fresh_blind_successor']),'retention':float(hier['metrics']['parent_correct_retention']),'repair':float(hier['metrics']['parent_error_repair_rate'])},
       'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},'traits':{'bounded':1.0},'failure_tags':['zero_gain','retention'],'status':'EVALUATED'},
      {'variant_id':'LOCAL_KNN_CHILD_V1','parent_id':'CALIBRATED_CHILD_V2','lineage_id':'G2_SELECTOR_LINEAGE','artifact_digest':knn['candidate_digest'],
       'task_scores':{'fresh_blind':float(knn['metrics']['fresh_blind_successor']),'retention':float(knn['metrics']['parent_correct_retention']),'repair':float(knn['metrics']['parent_error_repair_rate'])},
       'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},'traits':{'bounded':1.0,'local':1.0},'failure_tags':['zero_gain','repair'],'status':'EVALUATED'}
    ]
    parent=k.select_evolution_parent(records,'fresh_blind')
    op=k.propose_evolution_operation(records,parent['variant_id'],'fresh_blind')
finally:k.close()

# Evidence-driven diagnosis (no blind data).
diagnosis=[]
if res_conf:
    diagnosis.append('EXACT_REPRESENTATION_COLLISION')
if all(v['nonblind_total']>=5 for v in labels.values()) and not res_conf:
    diagnosis.append('NOT_EXACT_COLLISION')
if any(v['residual'] and v['correct'] for v in labels.values()):
    diagnosis.append('LABELS_HAVE_SAME_LABEL_SUCCESS_SUPPORT')
if len(res)<=10:
    diagnosis.append('SPARSE_RESIDUAL_REGIME')
same_label_ds=[x['nearest_correct_same_label_distance'] for x in nearest if x['nearest_correct_same_label_distance'] is not None]
other_ds=[x['nearest_correct_distance'] for x in nearest if x['nearest_correct_distance'] is not None]
geometry={
 'mean_nearest_correct_distance':statistics.mean(other_ds) if other_ds else None,
 'mean_nearest_same_label_distance':statistics.mean(same_label_ds) if same_label_ds else None,
 'same_label_neighbor_available':sum(x['nearest_correct_same_label_distance'] is not None for x in nearest),
}
out={'schema':'yado.g2.local_residual_representation_diagnosis.v1','status':'PASS',
 'kernel_parent':parent,'kernel_operation':op,
 'nonblind_count':len(nonblind),'residual_count':len(res),'exact_collision_groups':conf,'residuals_in_exact_collision_groups':res_conf,
 'label_support':labels,'numeric_feature_count':len(keys),'numeric_features':keys,'residual_geometry':nearest,'geometry_summary':geometry,
 'diagnosis':diagnosis,'blind_inspected':False}
(ROOT/'yado_g2_local_residual_representation_diagnosis_receipt.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
print(json.dumps({'kernel_parent':parent,'kernel_operation':op,'residual_count':len(res),'exact_collisions':len(conf),'residuals_in_collisions':res_conf,'label_support':labels,'geometry_summary':geometry,'diagnosis':diagnosis},indent=2))
