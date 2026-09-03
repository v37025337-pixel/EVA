from __future__ import annotations
import hashlib,importlib,json,re
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parent
MANIFEST_NAME='yado_development_manifest_v36.json'
MANIFEST_SHA256='4850cc8718a698d9ab86364d5010f1e5543aff1168d96b45f8a410daedc7b9dd'

def _sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def _load_json(p:Path)->dict[str,Any]:return json.loads(p.read_text(encoding='utf-8'))

def _manifest()->dict[str,Any]:
    p=ROOT/MANIFEST_NAME
    if not p.exists():raise RuntimeError('ACTIVE_MANIFEST_MISSING')
    actual=_sha(p)
    if actual!=MANIFEST_SHA256:raise RuntimeError(f'ACTIVE_MANIFEST_HASH_MISMATCH:{actual}')
    return _load_json(p)

def _validate_file_table(table:dict[str,Any],label:str):
    failures=[]
    for name,meta in table.items():
        p=ROOT/name
        if not p.exists():failures.append({'file':name,'reason':'MISSING'});continue
        actual=_sha(p)
        if actual!=meta.get('sha256'):failures.append({'file':name,'reason':'HASH_MISMATCH','expected':meta.get('sha256'),'actual':actual})
    if failures:raise RuntimeError(f'{label}_INTEGRITY_FAILURE:{failures}')

def active_contract()->dict[str,Any]:
    m=_manifest(); _validate_file_table(m.get('critical_files') or {},'CRITICAL_DEPENDENCY'); _validate_file_table(m.get('files') or {},'ACTIVE_ARTIFACT')
    c=dict(m['active_contract']); head=_load_json(ROOT/c['head'])
    fields=('version','profile','implementation','kernel_class','state','state_sha256')
    mismatch={k:{'manifest':c.get(k),'head':head.get(k)} for k in fields if c.get(k)!=head.get(k)}
    if mismatch:raise RuntimeError(f'ACTIVE_HEAD_SPLIT_BRAIN:{mismatch}')
    state_path=ROOT/c['state']; actual=_sha(state_path)
    if actual!=c['state_sha256']:raise RuntimeError(f'ACTIVE_STATE_HASH_MISMATCH:{actual}')
    st=_load_json(state_path)
    sm={k:{'expected':v,'actual':st.get(k)} for k,v in {'version':c['version'],'profile':c['profile'],'active_profile':c['profile'],'schema':c['schema']}.items() if st.get(k)!=v}
    if sm:raise RuntimeError(f'ACTIVE_STATE_METADATA_MISMATCH:{sm}')
    return c

def load_active_kernel_class():
    c=active_contract(); modname=c['implementation'][:-3] if c['implementation'].endswith('.py') else c['implementation']
    if not re.fullmatch(r'yado_[A-Za-z0-9_]+',modname):raise RuntimeError('INVALID_ACTIVE_IMPLEMENTATION_NAME')
    clsname=c['kernel_class']
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',clsname):raise RuntimeError('INVALID_ACTIVE_KERNEL_CLASS')
    mod=importlib.import_module(modname); cls=getattr(mod,clsname)
    if getattr(cls,'PROFILE',None)!=c['profile']:raise RuntimeError('KERNEL_CLASS_PROFILE_MISMATCH')
    return cls

def bootstrap_integrity()->dict[str,Any]:
    c=active_contract(); return {'pass':True,'manifest':MANIFEST_NAME,'manifest_sha256':MANIFEST_SHA256,'profile':c['profile'],'state':c['state'],'state_sha256':c['state_sha256'],'implementation':c['implementation'],'critical_files':len(_manifest().get('critical_files') or {})}

__all__=['active_contract','load_active_kernel_class','bootstrap_integrity','MANIFEST_NAME','MANIFEST_SHA256']
