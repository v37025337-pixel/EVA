from pathlib import Path
import ast,json,hashlib
ROOT=Path(__file__).resolve().parent;PKG=ROOT/'yado_rc8_v36'
targets={'detect_deficits','set_goal','add_goal','register_goal','create_goal','register_capability','__init__','_restore_development_state','_restore_state'}
hits=[]
for p in sorted(PKG.glob('*.py')):
    txt=p.read_text(encoding='utf-8')
    try:t=ast.parse(txt)
    except Exception:continue
    for n in ast.walk(t):
        if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
            name=getattr(n,'name','')
            seg=ast.get_source_segment(txt,n) or ''
            blob=(name+' '+seg[:14000]).lower()
            cond=(name in targets) or (isinstance(n,ast.ClassDef) and name in {'DevelopmentalExecutive','DevelopmentalExecutiveV22','UnifiedCognitiveSystem','UnifiedCognitiveSystemV22','GoalState','DeficitState'})
            if cond and len(seg)<=26000:
                hits.append({'kind':type(n).__name__,'name':name,'module':p.stem,'path':str(p.relative_to(ROOT.parent)),
                             'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'source':seg})
out={'schema':'yado.g2.rc8_goal_deficit_commit_path_probe.v1','status':'PASS','hits':hits}
(ROOT/'yado_g2_rc8_goal_deficit_commit_path_probe_receipt.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
print(json.dumps({'hits':[{'name':x['name'],'module':x['module'],'kind':x['kind']} for x in hits]},indent=2))
