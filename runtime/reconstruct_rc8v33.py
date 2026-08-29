from pathlib import Path
import base64,hashlib,json,zipfile,shutil
ROOT=Path(__file__).resolve().parent
meta=json.loads((ROOT/'package_meta.json').read_text())
raw=''.join((ROOT/'chunks'/f'rc8v33.part{i:03d}.b64').read_text() for i in range(meta['parts']))
data=base64.b64decode(raw)
sha=hashlib.sha256(data).hexdigest()
if sha!=meta['zip_sha256']:raise SystemExit(f'ZIP_SHA_MISMATCH {sha}')
zp=ROOT/'yado_rc8_v33.zip';zp.write_bytes(data)
out=ROOT/'yado_rc8_v33';shutil.rmtree(out,ignore_errors=True);out.mkdir()
with zipfile.ZipFile(zp) as z:z.extractall(out)
print(f'YADO_RC8_V33_ZIP_SHA256={sha}')
print(f'YADO_RC8_V33_EXTRACT={out}')