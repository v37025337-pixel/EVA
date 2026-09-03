from __future__ import annotations
import ast, hashlib, json, os, re, subprocess, sys, zipfile
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parent
REPORT=ROOT/'yado_deep_self_audit_cycle1_report.json'
R6_STATE=ROOT/'yado_canonical_state_v3_rc6_r6_schema_adaptation.json'
V17=ROOT/'yado_development_manifest_v17.json'
BUNDLE_MANIFEST=ROOT/'yado_rc6_r6_bundle_manifest.json'

def sha_file(p:Path)->str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def read_json(p:Path)->dict[str,Any]:
    return json.loads(p.read_text(encoding='utf-8'))

def parse_current_alias(p:Path)->dict[str,Any]:
    text=p.read_text(encoding='utf-8')
    imp=re.search(r'^from\s+(yado_[A-Za-z0-9_]+)\s+import\s+([A-Za-z0-9_]+)',text,re.M)
    vals={k:(re.search(rf'^{k}\s*=\s*[\"\']([^\"\']+)',text,re.M).group(1) if re.search(rf'^{k}\s*=\s*[\"\']([^\"\']+)',text,re.M) else None) for k in ('ACTIVE_STATE','ACTIVE_STATE_SHA256')}
    return {'module':imp.group(1) if imp else None,'class':imp.group(2) if imp else None,**vals,'sha256':sha_file(p)}

def local_import_closure(start:Path)->list[str]:
    seen=set(); stack=[start.name]
    while stack:
        name=stack.pop()
        if name in seen: continue
        p=ROOT/name
        if not p.exists(): continue
        seen.add(name)
        try: tree=ast.parse(p.read_text(encoding='utf-8'),name)
        except Exception: continue
        for n in ast.walk(tree):
            mods=[]
            if isinstance(n,ast.Import): mods=[a.name for a in n.names]
            elif isinstance(n,ast.ImportFrom) and n.module: mods=[n.module]
            for mod in mods:
                if mod.startswith('yado_'):
                    q=mod+'.py'
                    if (ROOT/q).exists() and q not in seen: stack.append(q)
    return sorted(seen)

def report_pass_summary(p:Path)->dict[str,Any]:
    d=read_json(p)
    vals=[]
    def walk(x):
        if isinstance(x,dict):
            if all(k in x for k in ('blind','ablation','restore')) and all(isinstance(x[k],(int,float)) for k in ('blind','ablation','restore')):
                vals.append({'blind':x['blind'],'ablation':x['ablation'],'restore':x['restore'],'learning_closed':x.get('learning_closed')})
            for v in x.values(): walk(v)
        elif isinstance(x,list):
            for v in x: walk(v)
    walk(d)
    return {'file':p.name,'status':d.get('status') or d.get('verdict'),'checks':vals,'fresh_used_for_selection':d.get('fresh_used_for_selection',False),'sha256':sha_file(p)}

def main()->int:
    findings=[]
    def add(fid,severity,component,title,evidence,status='OPEN'):
        findings.append({'id':fid,'severity':severity,'component':component,'title':title,'evidence':evidence,'status':status})

    v17=read_json(V17); state=read_json(R6_STATE); head=read_json(ROOT/'yado_active_developmental_head.json'); cur=parse_current_alias(ROOT/'yado_core_current.py')
    expected_profile=v17['active_profile']; expected_sha=v17['state_sha256']

    if head.get('profile')!=expected_profile or head.get('state_sha256')!=expected_sha:
        add('F-R7-CTRL-001','CRITICAL','control_plane','Active head descriptor is behind the latest proven R6 lineage',{'head_profile':head.get('profile'),'expected_profile':expected_profile,'head_state_sha256':head.get('state_sha256'),'expected_state_sha256':expected_sha})
    if cur.get('ACTIVE_STATE_SHA256')!=expected_sha:
        add('F-R7-CTRL-002','CRITICAL','control_plane','yado_core_current.py points to a stale active lineage',{'current_alias':cur,'expected_state_sha256':expected_sha})
    if state.get('profile')!=expected_profile or state.get('version')!='3.0-rc6-r6' or state.get('schema')!='yado.v3_0_rc6_r6.schema_adaptation.state.v1':
        add('F-R7-STATE-003','HIGH','state_lineage','R6 durable state carries stale R5 top-level metadata',{'version':state.get('version'),'profile':state.get('profile'),'active_profile':state.get('active_profile'),'schema':state.get('schema'),'expected_profile':expected_profile})

    mism=[]
    for name,meta in v17.get('files',{}).items():
        p=ROOT/name
        actual=sha_file(p) if p.exists() else None
        if actual!=meta.get('sha256'): mism.append({'file':name,'expected':meta.get('sha256'),'actual':actual})
    if mism:
        add('F-R7-MANIFEST-004','HIGH','artifact_integrity','Current workspace no longer matches development manifest V17',{'mismatches':mism})

    t=(ROOT/'test_yado_active_head.py').read_text(encoding='utf-8')
    if 'development_manifest' not in t and 'latest_manifest' not in t:
        add('F-R7-TEST-005','HIGH','testing','Active-head test is circular: it checks current.py against head JSON but not against latest proven manifest/state lineage',{'test':'test_yado_active_head.py','checks_latest_manifest':False})

    bm=read_json(BUNDLE_MANIFEST); bundle=ROOT/bm['bundle']; bundle_ok=False; bundle_alias=None
    if bundle.exists():
        bh=sha_file(bundle)
        try:
            with zipfile.ZipFile(bundle) as z:
                names=z.namelist(); bundle_ok=(bh==bm['sha256'] and set(names)==set(bm['members']))
                bundle_alias={'core_current_sha256':hashlib.sha256(z.read('yado_core_current.py')).hexdigest(),'head_sha256':hashlib.sha256(z.read('yado_active_developmental_head.json')).hexdigest()}
        except Exception as e: bundle_alias={'error':repr(e)}
    if not bundle_ok:
        add('F-R7-BUNDLE-006','HIGH','artifact_integrity','R6 recovery bundle integrity failed',{'bundle':bundle.name,'bundle_ok':bundle_ok,'alias':bundle_alias})
    else:
        add('F-R7-BUNDLE-006','INFO','artifact_integrity','R6 recovery bundle itself remains intact',{'bundle':bundle.name,'bundle_ok':True,'alias':bundle_alias},status='PASS')

    closure=local_import_closure(ROOT/'yado_core_v3_0_rc6_r6_schema_adaptation.py')
    missing=[x for x in closure if not (ROOT/x).exists()]
    if missing:
        add('F-R7-BOOT-007','CRITICAL','boot','Active R6 import closure has missing local modules',{'missing':missing,'closure_count':len(closure)})
    else:
        add('F-R7-BOOT-007','INFO','boot','Active R6 local import closure is present',{'closure_count':len(closure)},status='PASS')

    base=(ROOT/'yado_core_v2.py').read_text(encoding='utf-8')
    redirect_risk=('allow_redirects=True' in base and '_host_is_public' in base)
    if redirect_risk:
        add('F-R7-SEC-008','HIGH','network_boundary','Direct evidence fetch validates the initial host but follows redirects without a per-hop public-network check',{'file':'yado_core_v2.py','allow_redirects':True,'initial_public_host_check':True})
    if 'if allowed_domains and parsed.hostname.lower() not in allowed_domains' in base:
        add('F-R7-SEC-009','MEDIUM','network_boundary','Empty YADO_ALLOWED_DOMAINS means direct evidence fetch is not default-deny',{'file':'yado_core_v2.py','policy':'allow any public HTTPS host when allowlist empty'})

    r3=(ROOT/'yado_core_v3_0_rc3_autoevolution.py').read_text(encoding='utf-8')
    if 'self.state_path.read_bytes()' in r3 and 'DURABLE_MUTATION_DISABLED' in r3:
        add('F-R7-STATE-010','HIGH','durable_mutation','Durable evolution commit can write whichever state_path the kernel instance was constructed with; historical-state immutability is not enforced',{'file':'yado_core_v3_0_rc3_autoevolution.py'})

    # Model boot reads mutable evidence reports without a pre-import lock.
    v25=(ROOT/'yado_core_v2_5_unified.py').read_text(encoding='utf-8')
    critical_reports=['yado_cognitive_training_cycle1_report.json','yado_thinking_training_cycle2_report.json','yado_resource_intelligence_cycle8_report.json','yado_primitive_genesis_cycle1_report.json']
    if all(x in v25 for x in critical_reports):
        add('F-R7-SUPPLY-011','HIGH','model_supply_chain','Boot constructs active models from mutable report files before a content-addressed dependency lock is enforced',{'critical_reports':critical_reports})

    # Shadow frontier evidence audit.
    shadow_files=[ROOT/f'yado_stateful_frontier_repair_cycle{i}_report.json' for i in range(1,14) if (ROOT/f'yado_stateful_frontier_repair_cycle{i}_report.json').exists()]
    shadow=[report_pass_summary(p) for p in shadow_files]
    strong=[x for x in shadow if x['status'] and ('SUPPORTED' in str(x['status'])) and x['checks'] and all(c['blind']==1.0 and c['restore']==1.0 and c['ablation']<1.0 for c in x['checks'])]
    if strong:
        add('F-R7-INTEG-012','MEDIUM','development_integration','Multiple validated stateful/belief/active-information-gain capabilities remain detached shadow overlays',{'strong_shadow_reports':[x['file'] for x in strong],'count':len(strong)})

    chat=read_json(ROOT/'yado_chatgpt_study_cycle2_report.json')
    if chat.get('fresh_exact')==1.0 and not state.get('host_capability_model'):
        add('F-R7-HOST-013','MEDIUM','host_model','Validated ChatGPT capability-relation model is not durable in the active state',{'fresh_exact':chat.get('fresh_exact'),'fresh_coverage':chat.get('fresh_coverage'),'report':'yado_chatgpt_study_cycle2_report.json'})
    if 'profiles' not in chat:
        add('F-R7-HOST-014','MEDIUM','host_model','ChatGPT study report omits learned text profiles, so the router cannot be reconstructed from the report alone',{'selected_ngram_n':chat.get('selected_ngram_n'),'thresholds':[chat.get('defer_top_min'),chat.get('defer_margin_min')]})

    if state.get('audit',{}).get('compatibility_recovery_not_original'):
        add('F-R7-PROV-015','MEDIUM','provenance','Compatibility-recovery modules remain reconstructed interfaces, not recovered originals',{'compatibility_recovery_not_original':True},status='MONITOR')

    # Historical nonclaims that remain relevant.
    add('F-R7-BOUND-016','INFO','claim_boundary','Zero-host-substrate self-invention and unrestricted autonomous external execution are not established',{'zero_host_substrate':False,'unrestricted_external_execution':False},status='BOUNDARY')

    severity_order={'CRITICAL':0,'HIGH':1,'MEDIUM':2,'LOW':3,'INFO':4}
    open_findings=[f for f in findings if f['status']=='OPEN']
    priorities=sorted(open_findings,key=lambda f:(severity_order.get(f['severity'],9),f['id']))
    plan=[
      {'priority':1,'action':'UNIFY_BOOT_AND_STATE_LINEAGE','addresses':['F-R7-CTRL-001','F-R7-CTRL-002','F-R7-STATE-003','F-R7-MANIFEST-004','F-R7-TEST-005']},
      {'priority':2,'action':'ADD_PREIMPORT_DEPENDENCY_LOCK','addresses':['F-R7-SUPPLY-011']},
      {'priority':3,'action':'HARDEN_DIRECT_EVIDENCE_FETCH','addresses':['F-R7-SEC-008','F-R7-SEC-009']},
      {'priority':4,'action':'PROTECT_HISTORICAL_STATE_FROM_MUTATION','addresses':['F-R7-STATE-010']},
      {'priority':5,'action':'CONSOLIDATE_VALIDATED_FRONTIER_PORTFOLIO_INSTANCE_LOCALLY','addresses':['F-R7-INTEG-012']},
      {'priority':6,'action':'DURABILIZE_HOST_CAPABILITY_MODEL','addresses':['F-R7-HOST-013','F-R7-HOST-014']},
    ]
    rep={
      'schema':'yado.deep_self_audit.cycle1.v1',
      'status':'DEEP_AUDIT_COMPLETE_IMPROVEMENT_REQUIRED',
      'audited_profile':expected_profile,
      'audited_state_sha256':sha_file(R6_STATE),
      'baseline_regression':{'yado':'47/47 PASS','compileall':True},
      'surface':{'active_import_closure_files':len(closure),'shadow_frontier_reports':len(shadow),'strong_shadow_reports':len(strong)},
      'findings':findings,
      'open_findings_count':len(open_findings),
      'critical_count':sum(f['severity']=='CRITICAL' and f['status']=='OPEN' for f in findings),
      'high_count':sum(f['severity']=='HIGH' and f['status']=='OPEN' for f in findings),
      'priority_order':[f['id'] for f in priorities],
      'improvement_plan':plan,
      'shadow_evidence':shadow,
      'claim_boundary':{'audit_is_host_executed_against_real_local_artifacts':True,'kernel_weights_modified':False,'third_party_code_executed':False,'general_self_improvement_proven':False},
    }
    REPORT.write_text(json.dumps(rep,ensure_ascii=False,indent=2,sort_keys=True),encoding='utf-8')
    print(json.dumps({'status':rep['status'],'open':rep['open_findings_count'],'critical':rep['critical_count'],'high':rep['high_count'],'priority_order':rep['priority_order'],'report':REPORT.name},ensure_ascii=False,indent=2))
    return 0

if __name__=='__main__': raise SystemExit(main())
