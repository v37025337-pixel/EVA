from pathlib import Path
import ast,json,hashlib
ROOT=Path(__file__).resolve().parent; PKG=ROOT/'yado_rc8_v36'
classes={'BoundedRuleSandbox','RuleSpec','RulePredicate','RuleProgram'}
found={}
exec_refs=[]
for p in sorted(PKG.glob('*.py')):
    txt=p.read_text(encoding='utf-8')
    try: tree=ast.parse(txt)
    except Exception: continue
    for n in tree.body:
        if isinstance(n,ast.ClassDef) and n.name in classes:
            found[n.name]={'module':p.stem,'path':str(p.relative_to(ROOT.parent)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'source':ast.get_source_segment(txt,n) or ''}
        if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)):
            seg=ast.get_source_segment(txt,n) or ''
            if 'RuleProgram' in seg or 'BoundedRuleSandbox' in seg:
                exec_refs.append({'name':n.name,'module':p.stem,'path':str(p.relative_to(ROOT.parent)),'source':seg})
out={'schema':'yado.g2.rule_program_executor_source_probe.v1','status':'PASS' if 'BoundedRuleSandbox' in found else 'WITHHOLD',
     'classes':found,'function_refs':exec_refs}
(ROOT/'yado_g2_rule_program_executor_source_probe_receipt.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':out['status'],'classes':{k:v['module'] for k,v in found.items()},
                  'function_refs':[{'name':x['name'],'module':x['module']} for x in exec_refs]},indent=2))
