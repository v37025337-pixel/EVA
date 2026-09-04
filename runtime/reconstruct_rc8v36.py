from pathlib import Path
import base64,hashlib,json,zipfile,shutil,os

ROOT=Path(__file__).resolve().parent
meta=json.loads((ROOT/'package_meta.json').read_text())
target=ROOT/'yado_rc8_v36'

# Single-core rule:
# the checked-in runtime is authoritative for current G2 execution.
# The RC8/V36 archive is historical reconstruction memory and may only
# materialize the directory when it is missing, or when explicitly forced.
force_historical=os.getenv('YADO_FORCE_HISTORICAL_RC8_RECONSTRUCT')=='1'
if target.exists() and any(target.iterdir()) and not force_historical:
    print(json.dumps({
      'mode':'PRESERVE_CHECKED_IN_G2_RUNTIME',
      'historical_package_reconstruction':False,
      'target':str(target),
      'package_role':meta.get('package_role','HISTORICAL_RECONSTRUCTION_PACKAGE'),
      'current_runtime_authority':meta.get('current_runtime_authority','canonical/yado-unified-core-v1.json'),
    },sort_keys=True))
    raise SystemExit(0)

raw=b''.join(base64.b64decode((ROOT/'chunks'/n).read_text().strip()) for n in meta['parts'])
sha=hashlib.sha256(raw).hexdigest()
if sha!=meta['package_sha256']:
    raise SystemExit(f'PACKAGE_SHA_MISMATCH:{sha}')
z=ROOT/meta['package_name']
z.write_bytes(raw)
if target.exists():
    shutil.rmtree(target)
target.mkdir()
with zipfile.ZipFile(z) as archive:
    archive.extractall(target)
print(json.dumps({
  'mode':'HISTORICAL_RC8_RECONSTRUCTION',
  'historical_package_reconstruction':True,
  'package_sha256':sha,
  'manifest_sha256':meta['manifest_sha256'],
  'state_sha256':meta['state_sha256'],
  'parts':len(meta['parts']),
},sort_keys=True))
