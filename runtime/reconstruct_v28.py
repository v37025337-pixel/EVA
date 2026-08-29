from __future__ import annotations
import base64, hashlib, pathlib, zipfile, sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
CHUNKS=ROOT/'runtime'/'chunks'
OUT=ROOT/'runtime'/'yado_v28.zip'
EXPECTED_SHA256='1e65b4c1ef579741b84dc41a638e461ea280fdb46bca6363a4e1058976d25205'
parts=[]
for p in sorted(CHUNKS.glob('v28.part*.b64')):
    parts.append(p.read_text(encoding='ascii').strip())
if not parts:
    raise SystemExit('NO_V28_CHUNKS')
raw=base64.b64decode(''.join(parts),validate=True)
actual=hashlib.sha256(raw).hexdigest()
if actual!=EXPECTED_SHA256:
    raise SystemExit(f'ZIP_SHA256_MISMATCH:{actual}')
OUT.write_bytes(raw)
extract=ROOT/'runtime'/'yado_v28'
if extract.exists():
    import shutil; shutil.rmtree(extract)
extract.mkdir(parents=True)
with zipfile.ZipFile(OUT) as z:z.extractall(extract)
print('YADO_V28_ZIP_SHA256='+actual)
print('YADO_V28_EXTRACT='+str(extract))