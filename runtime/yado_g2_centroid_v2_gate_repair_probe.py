from pathlib import Path
import ast,json,hashlib,sys
ROOT=Path(__file__).resolve().parent; PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
hits=[]
explicit_classes={'SkillCandidate'}
for p in sorted(PKG.glob('*.py')):
    txt=p.read_text(encoding='utf-8')
    try:t=ast.parse(txt)
    except Exception:continue
    for n in ast.walk(t):
        if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
            name=getattr(n,'name','')
            seg=ast.get_source_segment(txt,n) or ''
            blob=(name+' '+seg[:12000]).lower()
            if (isinstance(n,ast.ClassDef) and name in explicit_classes) or any(k in blob for k in ('calibrat','confidence','margin','abstain','threshold select','distance ratio')):
                if len(seg)<=18000:
                    hits.append({'kind':type(n).__name__,'name':name,'module':p.stem,'path':str(p.relative_to(ROOT.parent)),
                                 'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'source':seg})
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'yado_centroid_v2_operation_probe.sqlite'))
try:
    records=[
      {'variant_id':'EXECUTABLE_PARENT','parent_id':None,'lineage_id':'G2_SELECTOR_LINEAGE',
       'artifact_digest':'parent',
       'task_scores':{'fresh_blind':0.8043478260869565,'parent_correct_retention':1.0,'parent_error_repair_rate':0.0},
       'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},
       'traits':{'executable':1.0,'bounded':1.0},'failure_tags':['parent_error_repair_rate'],'status':'EVALUATED'},
      {'variant_id':'CENTROID_CHILD_V1','parent_id':'EXECUTABLE_PARENT','lineage_id':'G2_SELECTOR_LINEAGE',
       'artifact_digest':'016cbe8a791b6c1089f016d0047283109b16cf48cd28598752904d98b35fe384',
       'task_scores':{'fresh_blind':0.717391304347826,'parent_correct_retention':0.8648648648648649,'parent_error_repair_rate':0.1111111111111111},
       'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},
       'traits':{'executable':1.0,'bounded':1.0,'continuous':1.0},
       'failure_tags':['parent_error_repair_rate','gate_false_positive_regression'],'status':'EVALUATED'}
    ]
    parent=k.select_evolution_parent(records,'fresh_blind')
    op=k.propose_evolution_operation(records,parent['variant_id'],'fresh_blind')
finally:k.close()
out={'schema':'yado.g2.centroid_v2_gate_repair_probe.v1','status':'PASS','kernel_parent':parent,'kernel_operation':op,'source_hits':hits}
(ROOT/'yado_g2_centroid_v2_gate_repair_probe_receipt.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
print(json.dumps({'kernel_parent':parent,'kernel_operation':op,'hit_count':len(hits),
 'hits':[{'kind':x['kind'],'name':x['name'],'module':x['module']} for x in hits]},indent=2))
