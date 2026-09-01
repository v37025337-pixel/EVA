from pathlib import Path
import ast,json,hashlib
ROOT=Path(__file__).resolve().parent; PKG=ROOT/'yado_rc8_v36'
targets_classes={'UnifiedYADOKernelV30RC6MetaGrammar','MetaGrammarRegistry','MetaGrammarExtensionRegistry'}
targets_funcs={'meta_grammar_snapshot','meta_grammar_extension_registry','_operator','extend_meta_grammar','register_meta_grammar_extension'}
found_classes={};found_funcs=[];module_hits=[]
for p in sorted(PKG.glob('*.py')):
    txt=p.read_text(encoding='utf-8')
    if 'meta_grammar' in p.stem or 'MetaGrammar' in txt or 'meta_grammar_extension' in txt:
        module_hits.append({'module':p.stem,'path':str(p.relative_to(ROOT.parent)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    try: tree=ast.parse(txt)
    except Exception: continue
    for n in tree.body:
        if isinstance(n,ast.ClassDef) and (n.name in targets_classes or 'MetaGrammar' in n.name):
            found_classes[n.name]={'module':p.stem,'path':str(p.relative_to(ROOT.parent)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'source':ast.get_source_segment(txt,n) or ''}
        if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name in targets_funcs:
            found_funcs.append({'name':n.name,'module':p.stem,'path':str(p.relative_to(ROOT.parent)),'source':ast.get_source_segment(txt,n) or ''})
out={'schema':'yado.g2.meta_grammar_extension_source_probe.v1','status':'PASS','classes':found_classes,'functions':found_funcs,'modules':module_hits}
(ROOT/'yado_g2_meta_grammar_extension_source_probe_receipt.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
print(json.dumps({'classes':{k:v['module'] for k,v in found_classes.items()},'functions':[{'name':x['name'],'module':x['module']} for x in found_funcs],'modules':module_hits},indent=2))
