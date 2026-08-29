from __future__ import annotations
import base64,hashlib,pathlib,zipfile,shutil
ROOT=pathlib.Path(__file__).resolve().parents[1]
CHUNKS=ROOT/'runtime'/'chunks'
OUT=ROOT/'runtime'/'yado_v29.zip'
EXPECTED_SHA256='0db3328a95f2439cf5b534584d05cb5e0f1aefaf25bca217155e4c1c4087d5f7'
parts=[p.read_text(encoding='ascii').strip() for p in sorted(CHUNKS.glob('v29.part*.b64'))]
if not parts: raise SystemExit('NO_V29_CHUNKS')
raw=base64.b64decode(''.join(parts),validate=True)
actual=hashlib.sha256(raw).hexdigest()
if actual!=EXPECTED_SHA256: raise SystemExit(f'ZIP_SHA256_MISMATCH:{actual}')
OUT.write_bytes(raw)
extract=ROOT/'runtime'/'yado_v29'
if extract.exists(): shutil.rmtree(extract)
extract.mkdir(parents=True)
with zipfile.ZipFile(OUT) as z: z.extractall(extract)
print('YADO_V29_ZIP_SHA256='+actual)
print('YADO_V29_EXTRACT='+str(extract))