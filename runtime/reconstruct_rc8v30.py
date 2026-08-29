from pathlib import Path
import base64,hashlib,json,zipfile,shutil
ROOT=Path(__file__).resolve().parent
meta=json.loads((ROOT/'package_meta.json').read_text())
parts=sorted((ROOT/'chunks').glob('rc8v30.part*.b64'))
assert len(parts)==meta['chunks'],(len(parts),meta['chunks'])
raw=base64.b64decode(''.join(p.read_text().strip() for p in parts))
h=hashlib.sha256(raw).hexdigest(); assert h==meta['zip_sha256'],(h,meta['zip_sha256'])
z=ROOT/'yado_rc8_v30.zip'; z.write_bytes(raw)
d=ROOT/'yado_rc8_v30'
if d.exists(): shutil.rmtree(d)
d.mkdir()
with zipfile.ZipFile(z) as f:f.extractall(d)
print('YADO_RC8_V30_ZIP_SHA256='+h)
print('YADO_RC8_V30_EXTRACT='+str(d))