from pathlib import Path
import ast,json,hashlib
ROOT=Path(__file__).resolve().parent;PKG=ROOT/'yado_rc8_v36'
terms=('synth','repair','rewrite','mutation','registry','commit','install','skill','selector','artifact','patch','code')
hits=[]
for p in sorted(PKG.glob('*.py')):
    txt=p.read_text(encoding='utf-8')
    try:t=ast.parse(txt)
    except Exception:continue
    for n in ast.walk(t):
        if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
            name=getattr(n,'name','');seg=ast.get_source_segment(txt,n) or ''
            blob=(name+' '+seg[:14000]).lower()
            if any(term in blob for term in terms):
                score=sum(term in blob for term in ('synth','repair','rewrite','mutation','registry','commit','skill','selector'))
                if score>=2 and len(seg)<=22000:
                    hits.append({'kind':type(n).__name__,'name':name,'module':p.stem,'path':str(p.relative_to(ROOT.parent)),
                                 'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'score':score,'source':seg})
hits.sort(key=lambda x:(-x['score'],x['module'],x['name']))
out={'schema':'yado.g2.selector_commit_genesis_source_probe.v1','status':'PASS','hits':hits[:160]}
(ROOT/'yado_g2_selector_commit_genesis_source_probe_receipt.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
print(json.dumps({'count':len(out['hits']),'hits':[{'name':x['name'],'module':x['module'],'kind':x['kind'],'score':x['score']} for x in out['hits']]},indent=2))
