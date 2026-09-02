from pathlib import Path
import ast,json,hashlib,re
ROOT=Path(__file__).resolve().parent;PKG=ROOT/'yado_rc8_v36'
terms=('commit','admit','promot','activat','install','register','skill','selector','mutation','canonical')
hits=[]
for p in sorted(PKG.glob('*.py')):
    txt=p.read_text(encoding='utf-8')
    try:t=ast.parse(txt)
    except Exception:continue
    for n in ast.walk(t):
        if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)):
            name=n.name.lower()
            if any(term in name for term in terms):
                seg=ast.get_source_segment(txt,n) or ''
                if len(seg)<=16000:
                    hits.append({'name':n.name,'module':p.stem,'path':str(p.relative_to(ROOT.parent)),
                                 'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'source':seg})
# keep methods most likely relevant to canonical/evolution/skills
ranked=[]
for x in hits:
    blob=(x['name']+' '+x['source'][:1500]).lower()
    score=sum(k in blob for k in ('canonical','skill','evolution','commit','promotion','mutation','registry','selector'))
    if score>=2:ranked.append((score,x))
ranked.sort(key=lambda z:(-z[0],z[1]['module'],z[1]['name']))
out={'schema':'yado.g2.native_selector_commit_surface_probe.v1','status':'PASS','hits':[x for _,x in ranked[:120]]}
(ROOT/'yado_g2_native_selector_commit_surface_probe_receipt.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
print(json.dumps({'count':len(out['hits']),'hits':[{'name':x['name'],'module':x['module']} for x in out['hits']]},indent=2))
