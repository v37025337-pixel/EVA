from pathlib import Path
import base64,hashlib,json,zipfile,shutil
ROOT=Path(__file__).resolve().parent
meta=json.loads((ROOT/'package_meta.json').read_text())
raw=b''.join(base64.b64decode((ROOT/'chunks'/n).read_text().strip()) for n in meta['parts'])
sha=hashlib.sha256(raw).hexdigest()
if sha!=meta['package_sha256']:raise SystemExit(f'PACKAGE_SHA_MISMATCH:{sha}')
z=ROOT/meta['package_name'];z.write_bytes(raw)
target=ROOT/'yado_rc8_v36'
if target.exists():shutil.rmtree(target)
target.mkdir()
with zipfile.ZipFile(z) as f:f.extractall(target)
print(json.dumps({'package_sha256':sha,'manifest_sha256':meta['manifest_sha256'],'state_sha256':meta['state_sha256'],'parts':len(meta['parts'])},sort_keys=True))