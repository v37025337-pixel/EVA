from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,os

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'receipts'/'yado-conjunctive-rule-inducer-v1-latest.json'
EXT=ROOT/'receipts'/'yado-conjunctive-rule-inducer-extended-transfer-v1-latest.json'
DEC=ROOT/'receipts'/'yado-g0-conjunctive-algorithm-readmission-v2-latest.json'
STATE=ROOT/'runtime'/'yado_rc8_v36'/'yado_canonical_state_v3_rc8_external_cognitive.json'
OUT=ROOT/'candidates'/'shadow-algorithm-bank'/'conjunctive-rule-inducer-v1.json'

def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def sha_file(p): return hashlib.sha256(p.read_bytes()).hexdigest()

base=json.loads(BASE.read_text())
ext=json.loads(EXT.read_text())
dec=json.loads(DEC.read_text())
before=sha_file(STATE)

if base.get('status')!='PASS_CONJUNCTIVE_RULE_INDUCER_V1':
    raise RuntimeError('BASE_EVIDENCE_NOT_PASS')
if dec.get('decision',{}).get('action')!='EXECUTE' or dec.get('admission_authorized') is not True:
    raise RuntimeError('G0_EXECUTE_AUTHORIZATION_REQUIRED')
if dec.get('canonical_parent_byte_identical') is not True:
    raise RuntimeError('PARENT_INTEGRITY_NOT_PROVEN')
if base.get('component',{}).get('component_digest')!='3b31c7d26e4e51db3a5135a58ac4fe764f45ce96bf4e80e016172bd212e43150':
    raise RuntimeError('COMPONENT_DIGEST_MISMATCH')

entry={
  'schema':'yado.shadow_algorithm_bank.entry.v1',
  'entry_id':'ALG-CONJUNCTIVE-RULE-INDUCER-V1',
  'organ':'LOGIC',
  'family':'CONJUNCTIVE_RULE_INDUCTION',
  'component_digest':base['component']['component_digest'],
  'component':base['component'],
  'algorithm_source_path':'runtime/yado_conjunctive_rule_inducer_v1.py',
  'admission':{
    'authority':'G0_METACOGNITIVE_EXECUTE',
    'decision_receipt_sha256':dec['receipt_sha256'],
    'decision':dec['decision'],
    'base_evidence_receipt_sha256':base['receipt_sha256'],
    'extended_transfer_receipt_sha256':ext['receipt_sha256'],
    'extended_transfer_summary':ext['summary'],
  },
  'scope':'SHADOW_ONLY',
  'canonical_active':False,
  'eligible_for_meta_selection':True,
  'known_limitations':[
    {
      'evidence':'ACCESS_CONTROL_TRANSFER',
      'validation':ext['results']['ACCESS_CONTROL_TRANSFER']['validation'],
      'fresh_blind':ext['results']['ACCESS_CONTROL_TRANSFER']['fresh_blind'],
      'interpretation':'STRICT_ADMISSION_THRESHOLD_NOT_MET; RETAIN_AS_COUNTEREXAMPLE',
    }
  ],
  'promotion_requirements':[
    'FRESH_META_SELECTION_VS_EXISTING_BANK',
    'NO_PROTECTED_CAPABILITY_REGRESSION',
    'ABLATION',
    'ROLLBACK',
    'FULL_REGRESSION',
  ],
  'developmental_head':'G0_RC8_V36',
  'canonical_parent_sha256':before,
  'canonical_mutation':False,
  'promotion_applied':False,
}
entry['entry_digest']=hashlib.sha256(canon(entry).encode()).hexdigest()

OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(entry,indent=2,sort_keys=True,default=str)+'\n')
after=sha_file(STATE)
if before!=after:
    raise RuntimeError('CANONICAL_PARENT_CHANGED')

report={
  'schema':'yado.shadow_algorithm_bank.admission.receipt.v1',
  'status':'PASS_SHADOW_ALGORITHM_BANK_ADMISSION_V1',
  'github_run_id':os.getenv('GITHUB_RUN_ID'),'github_sha':os.getenv('GITHUB_SHA'),
  'entry_id':entry['entry_id'],'entry_digest':entry['entry_digest'],
  'g0_decision':'EXECUTE',
  'canonical_parent_sha256_before':before,'canonical_parent_sha256_after':after,
  'canonical_parent_byte_identical':before==after,
  'canonical_mutation':False,'promotion_applied':False,
  'next_required_capability':'FRESH_META_SELECTION_NEW_ALGORITHM_VS_EXISTING_BANK_V1',
}
report['receipt_sha256']=hashlib.sha256(canon(report).encode()).hexdigest()
(ROOT/'runtime'/'yado_shadow_algorithm_bank_admission_v1_receipt.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
print(json.dumps(report,indent=2,sort_keys=True))
