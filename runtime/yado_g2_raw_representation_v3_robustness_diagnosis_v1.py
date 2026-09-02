from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,os,sys

ROOT=Path(__file__).resolve().parent;REPO=ROOT.parent;PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]
from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_bounded_capability_router_v1 import BoundedCapabilityRouterLearnerV1
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash

LEDGER=REPO/'architecture/evolution-ledger.json'
STRUCT=REPO/'resources/yado-raw-task-representation-v3-structural-fresh-holdout-v1.json'
V2AUD=REPO/'receipts/yado-g2-raw-representation-v2-post-admission-audit-v1-run-33670110185.json'
BURN=REPO/'receipts/yado-g2-raw-representation-v3-canonical-burnin-v1-run-33678904722.json'
OUT=ROOT/'yado_g2_raw_representation_v3_robustness_diagnosis_v1_receipt.json'

CAP_CONJ='ALG-CONJUNCTIVE-RULE-INDUCER-V1'
CAP_REL='ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1'
CAP_BUD='ALG-BUDGETED-STAGE-POLICY-V1'
CAP_RES='RESOURCE-PORTFOLIO-V1'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,o):p.write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
ledger,struct,v2aud,burn=map(load,[LEDGER,STRUCT,V2AUD,BURN]);validate_ledger_v2(ledger)
front='KERNEL_G2_RAW_REPRESENTATION_V3_ROBUSTNESS_SELF_EVOLUTION_V1'
if ledger.get('open_deficits')!=[front]:raise RuntimeError('UNEXPECTED_FRONTIER')

rows=[]
for i,label in enumerate([CAP_CONJ,CAP_REL,CAP_BUD,CAP_RES]*180):
    rows.append({'input':{'budget_limited':label==CAP_BUD,'quota_limited':False,'external_evidence_needed':label==CAP_RES,'relation_needed':label==CAP_REL,'disjunction_needed':False,'noise':i},'expected':label})
router=BoundedCapabilityRouterLearnerV1.synthesize(rows,rows,CAP_CONJ,min_support=8)
ucore=UnifiedYADOCoreV1(REPO)
base_cases=[{'text':r['text'],'expected':r['expected'],'source':'STRUCT'} for r in struct['rows']]
base_cases += [{'text':r['text'],'expected':r['expected'],'source':'V2_AUDIT'} for r in v2aud['canary_rows']]

def perturb(text,round_no,index):
    if round_no==1:return f"Case metadata {index%17}: "+text+f" [trace {1000+index}]"
    if round_no==2:
        t=text.upper() if index%2==0 else text.lower()
        return "Administrative note. "+t+" End note."
    t="  ".join(text.replace(";"," ; ").replace(","," , ").split())
    return f"Review item {index%23}. {t} [normal priority]"

errors=[];by_round={};confusions={}
for rn in (1,2,3):
    e=[];correct=0
    for i,row in enumerate(base_cases):
        pt=perturb(row['text'],rn,i)
        got=ucore.route_raw_task(pt,router)['selected_capability']
        ok=got==row['expected'];correct+=ok
        if not ok:
            rec={'round':rn,'index':i,'source':row['source'],'expected':row['expected'],'got':got,'base_text':row['text'],'perturbed_text':pt}
            e.append(rec);errors.append(rec)
            key=row['expected']+'->'+got;confusions[key]=confusions.get(key,0)+1
    by_round[str(rn)]={'accuracy':correct/len(base_cases),'error_count':len(e),'errors':e}

# Token/pivot diagnostics are generic descriptive statistics only.
def words(s):
    import re
    return re.findall(r"[A-Za-z0-9_]+",s.lower())
diag={
 'total_base_cases':len(base_cases),
 'total_errors':len(errors),
 'confusions':confusions,
 'error_expected_counts':{},
 'error_got_counts':{},
 'error_source_counts':{},
 'contains_selected_pivot_local':sum('local' in words(e['perturbed_text']) for e in errors),
 'contains_external':sum('external' in words(e['perturbed_text']) for e in errors),
 'contains_budget':sum('budget' in words(e['perturbed_text']) for e in errors),
 'contains_owner_or_ownership':sum(any(w in words(e['perturbed_text']) for w in ('owner','ownership')) for e in errors),
}
for e in errors:
    diag['error_expected_counts'][e['expected']]=diag['error_expected_counts'].get(e['expected'],0)+1
    diag['error_got_counts'][e['got']]=diag['error_got_counts'].get(e['got'],0)+1
    diag['error_source_counts'][e['source']]=diag['error_source_counts'].get(e['source'],0)+1

receipt={
 'schema':'yado.g2.raw_representation_v3_robustness_diagnosis.receipt.v1',
 'status':'PASS_G2_RAW_REPRESENTATION_V3_ROBUSTNESS_DIAGNOSIS_V1',
 'frontier':front,'burnin_receipt_sha256':burn['receipt_sha256'],
 'rounds':by_round,'diagnosis':diag,
 'uses_spent_burnin_data_only':True,
 'canonical_mutation':False,'architecture_mutation':False,'g3_genesis_performed':False,
 'next_required_capability':front
}
receipt['receipt_sha256']=h(receipt);write(OUT,receipt)
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_RAW_V3_ROBUSTNESS_DIAGNOSIS_V1",
 'event_type':'G2_RAW_REPRESENTATION_ROBUSTNESS_DIAGNOSIS','status':'PASS','generation':ledger['current_head'],'deficit':front,
 'effect':f"ERRORS={len(errors)}; CONFUSIONS={json.dumps(confusions,sort_keys=True)}; NEXT={front}",
 'source_path':f'receipts/yado-g2-raw-representation-v3-robustness-diagnosis-v1-run-{run_id}.json','source_digest':receipt['receipt_sha256'],'run_id':run_id,
 'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':False,'promotion_applied':False,'generation_transition':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash'];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n',encoding='utf-8')
print(json.dumps({'status':receipt['status'],'rounds':{k:{'accuracy':v['accuracy'],'error_count':v['error_count']} for k,v in by_round.items()},'diagnosis':diag},indent=2,sort_keys=True))
