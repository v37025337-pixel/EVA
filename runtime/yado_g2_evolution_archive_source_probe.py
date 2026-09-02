from pathlib import Path
import ast,json,hashlib
ROOT=Path(__file__).resolve().parent; PKG=ROOT/'yado_rc8_v36'
classes={}
for p in sorted(PKG.glob('*.py')):
    txt=p.read_text(encoding='utf-8')
    try:t=ast.parse(txt)
    except Exception:continue
    for n in t.body:
        if isinstance(n,ast.ClassDef) and ('EvolutionArchive' in n.name or 'ArchiveRuntime' in n.name):
            classes[n.name]={'module':p.stem,'path':str(p.relative_to(ROOT.parent)),
                'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
                'source':ast.get_source_segment(txt,n) or ''}
out={'schema':'yado.g2.evolution_archive_source_probe.v1','status':'PASS' if classes else 'WITHHOLD','classes':classes}
(ROOT/'yado_g2_evolution_archive_source_probe_receipt.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':out['status'],'classes':{k:v['module'] for k,v in classes.items()}},indent=2))
