from pathlib import Path
import base64,hashlib,json,zipfile,shutil
ROOT=Path(__file__).resolve().parent
meta=json.loads((ROOT/'package_meta.json').read_text())
raw=''.join(p.read_text() for p in sorted((ROOT/'chunks').glob('rc8v35.part*.b64')))
data=base64.b64decode(raw)
assert hashlib.sha256(data).hexdigest()==meta['package_sha256']
z=ROOT/'yado_rc8_v35.zip';z.write_bytes(data)
out=ROOT/'yado_rc8_v35'
if out.exists():shutil.rmtree(out)
out.mkdir();zipfile.ZipFile(z).extractall(out)
print(meta)