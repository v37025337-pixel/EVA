from pathlib import Path
import ast,json,hashlib,re
ROOT=Path(__file__).resolve().parent; PKG=ROOT/'yado_rc8_v36'
hits=[]
for p in sorted(PKG.glob('*.py')):
    txt=p.read_text(encoding='utf-8')
    try: tree=ast.parse(txt)
    except Exception: continue
    for n in ast.walk(tree):
        if isinstance(n,(ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef)):
            name=getattr(n,'name','')
            seg=ast.get_source_segment(txt,n) or ''
            blob=(name+' '+seg[:5000]).lower()
            if any(k in blob for k in ('threshold','stump','quantile','interval','numeric predicate','predicate synthes')):
                if len(seg)<=18000:
                    hits.append({'kind':type(n).__name__,'name':name,'module':p.stem,'path':str(p.relative_to(ROOT.parent)),
                                 'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'source':seg})
# dedup exact module/name/kind
seen=set();out_hits=[]
for x in hits:
    key=(x['module'],x['name'],x['kind'])
    if key in seen:continue
    seen.add(key);out_hits.append(x)
out={'schema':'yado.g2.bounded_threshold_constructor_source_probe.v1','status':'PASS','hit_count':len(out_hits),'hits':out_hits}
(ROOT/'yado_g2_bounded_threshold_constructor_source_probe_receipt.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
print(json.dumps({'hit_count':len(out_hits),'hits':[{'kind':x['kind'],'name':x['name'],'module':x['module']} for x in out_hits]},indent=2))
