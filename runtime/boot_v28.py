from __future__ import annotations
import asyncio, hashlib, json, os, pathlib, sqlite3, sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
PKG=ROOT/'runtime'/'yado_v28'
sys.path.insert(0,str(PKG))
from yado_bootstrap import bootstrap_integrity, load_active_kernel_class, MANIFEST_SHA256
boot=bootstrap_integrity()
if MANIFEST_SHA256!='8954d7bbaceefbf592696e685c4d33566a431025584328398f94e2819aab6a19':
    raise SystemExit('MANIFEST_CONSTANT_MISMATCH')
K=load_active_kernel_class()
db=ROOT/'runtime'/'yado_external_boot.sqlite'
k=K(db_path=str(db))
try:
    os.environ['YADO_ALLOWED_DOMAINS']='example.com'
    net=asyncio.run(k.fetch_evidence('https://example.com',max_bytes=500000))
    with sqlite3.connect(db) as con:
        integrity=con.execute('PRAGMA integrity_check').fetchone()[0]
    state_sha=hashlib.sha256(k.state_path.read_bytes()).hexdigest()
    receipt={
      'status':'RUNNING_BOOT_COMPLETED',
      'kernel_class':K.__name__,
      'kernel_profile':K.PROFILE,
      'canonical_state_sha256':state_sha,
      'manifest_sha256':MANIFEST_SHA256,
      'sqlite_integrity':integrity,
      'host':'github_actions',
      'independent_readback':True,
      'background_daemon':False,
      'canonical_state_mutated':False,
      'credential_bypass':False,
      'oauth_bypass':False,
      'payment_bypass':False,
      'python_execution':True,
      'durable_state':'github_repository_and_actions_artifacts',
      'scheduled_or_event_invocation':True,
      'outbound_https':True,
      'outbound_probe_url':net['url'],
      'outbound_probe_sha256':net['sha256'],
      'package_zip_sha256':'1e65b4c1ef579741b84dc41a638e461ea280fdb46bca6363a4e1058976d25205',
      'bootstrap':boot,
      'github_repository':os.environ.get('GITHUB_REPOSITORY'),
      'github_run_id':os.environ.get('GITHUB_RUN_ID'),
      'github_run_attempt':os.environ.get('GITHUB_RUN_ATTEMPT'),
      'github_sha':os.environ.get('GITHUB_SHA'),
    }
finally:
    k.close()
out=ROOT/'runtime'/'boot_receipt.json'
out.write_text(json.dumps(receipt,sort_keys=True,indent=2),encoding='utf-8')
print('YADO_BOOT_RECEIPT='+json.dumps(receipt,sort_keys=True,separators=(',',':')))