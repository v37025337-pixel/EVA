from __future__ import annotations
from pathlib import Path
import ast,copy,hashlib,json,re,subprocess,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path.insert(0,str(ROOT))
from yado_evolution_ledger_v2 import validate_ledger_v2

ACTIVE='yado-architecture-shadow-search'
FRONT='KERNEL_G2_RAW_REPRESENTATION_V5_CANONICAL_ADMISSION_V1'

def load(p):return json.loads(p.read_text(encoding='utf-8'))
def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def cdig(o,f):x=copy.deepcopy(o);x.pop(f,None);return h(x)

head=load(REPO/'canonical/yado-main-head-g2.json')
core=load(REPO/'canonical/yado-unified-core-v1.json')
exp=load(REPO/'canonical/yado-unified-experience-registry-v1.json')
prov=load(REPO/'canonical/yado-algorithm-provenance-registry-v1.json')
ledger=load(REPO/'architecture/evolution-ledger.json')
bind=load(REPO/'canonical/yado-g2-applied-experience-binding-v1.json')
qman=load(REPO/'quarantine/yado-g2-quarantine-manifest-v1.json')
validate_ledger_v2(ledger)

checks={}
checks['frontier_single']=ledger.get('open_deficits')==[FRONT] and head.get('current_frontier')==FRONT and core.get('current_frontier')==FRONT and prov.get('current_g2_binding',{}).get('frontier')==FRONT
checks['head_digest']=cdig(head,'canonical_head_digest')==head.get('canonical_head_digest')==ledger.get('current_head_digest')
checks['core_digest']=cdig(core,'core_digest')==core.get('core_digest')
checks['provenance_digest']=cdig(prov,'registry_digest')==prov.get('registry_digest')
checks['experience_digest']=cdig(exp,'registry_digest')==exp.get('registry_digest')==core.get('experience_registry_digest')==head.get('unified_core',{}).get('experience_registry_digest')
checks['binding_digest']=cdig(bind,'binding_digest')==bind.get('binding_digest')==core.get('applied_experience_binding',{}).get('binding_digest')
checks['quarantine_digest']=cdig(qman,'manifest_digest')==qman.get('manifest_digest')==core.get('quarantine',{}).get('manifest_digest')
checks['g3_closed']=head.get('g3_genesis_performed') is False and core.get('g3_genesis_performed') is False

branches=exp.get('branches',[])
active=[b for b in branches if b.get('mode')=='ACTIVE_LINEAGE']
legacy=[b for b in branches if b.get('mode')=='EXPERIENCE_ONLY']
checks['one_active_13_history']=len(active)==1 and active[0].get('branch')==ACTIVE and len(legacy)==13 and all(b.get('runtime_active') is False and b.get('history_only') is True and b.get('control_plane_quarantined') is True for b in legacy)

checks['all_planes_experience_bound']=len(bind.get('plane_bindings',{}))==len(core.get('planes',[]))==9 and all(p.get('experience_binding_digest')==bind.get('binding_digest') and p.get('experience_sources') for p in core.get('planes',[]))
checks['global_history_13']=len(bind.get('global_history',[]))==13 and bind.get('legacy_code_execution') is False and bind.get('mechanism_reuse_requires_fresh_admission') is True

hist={b.get('branch') for b in legacy}
bad_wf=[]
for p in list((REPO/'.github/workflows').glob('*.yml'))+list((REPO/'.github/workflows').glob('*.yaml')):
    text=p.read_text(encoding='utf-8',errors='replace')
    found=set()
    for m in re.finditer(r'branches:\s*\[([^\]]+)\]',text):
        for x in m.group(1).split(','):found.add(x.strip().strip("'\""))
    if ACTIVE not in found and found & hist:bad_wf.append(p.name)
checks['no_legacy_branch_workflows_active']=not bad_wf
checks['quarantined_workflows_exist']=qman.get('physical_quarantine',{}).get('count',0)>0 and all((REPO/x['quarantine']).exists() for x in qman.get('physical_quarantine',{}).get('legacy_workflows',[]))

active_sources=core.get('active_runtime_sources',[])
checks['active_runtime_not_quarantined']=all(not str(x).startswith('quarantine/') for x in active_sources)
missing=[x for x in active_sources if not (REPO/x).exists()]
checks['active_runtime_exists']=not missing

unsafe_imports=[]
legacy_markers=('v28','v29','rc8v30','rc8v33','rc8v35','v37_overlay')
for rel in active_sources:
    p=REPO/rel
    if not p.exists() or p.suffix!='.py':continue
    try:tree=ast.parse(p.read_text(encoding='utf-8'))
    except Exception as e:
        unsafe_imports.append({'path':rel,'error':repr(e)});continue
    for n in ast.walk(tree):
        names=[]
        if isinstance(n,ast.Import):names=[a.name for a in n.names]
        elif isinstance(n,ast.ImportFrom) and n.module:names=[n.module]
        for name in names:
            if any(m in name.lower() for m in legacy_markers):
                unsafe_imports.append({'path':rel,'import':name})
checks['no_legacy_runtime_imports']=not unsafe_imports

old_guard=subprocess.run([sys.executable,str(ROOT/'yado_canonical_invariant_guard_v1.py')],cwd=REPO,capture_output=True,text=True,timeout=60)
checks['canonical_guard']=old_guard.returncode==0

ok=all(checks.values())
report={
 'schema':'yado.g2.single_lineage_closure_guard.v1',
 'status':'PASS' if ok else 'FAIL',
 'checks':checks,
 'bad_legacy_workflows':bad_wf,
 'missing_active_runtime':missing,
 'unsafe_legacy_imports':unsafe_imports,
 'frontier':FRONT,
 'binding_digest':bind.get('binding_digest'),
 'quarantine_manifest_digest':qman.get('manifest_digest')
}
print(json.dumps(report,indent=2,sort_keys=True))
if not ok:raise SystemExit(1)
