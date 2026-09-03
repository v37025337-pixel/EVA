from __future__ import annotations
import hashlib, json, sqlite3
from pathlib import Path
from datetime import datetime, timezone
from yado_bootstrap import bootstrap_integrity, load_active_kernel_class, active_contract

ROOT = Path(__file__).resolve().parent
DUMP = ROOT / "state" / "yado_rc7_live_state.sql"
LIVE_DB = ROOT / "state" / "yado_rc7_live_runtime.sqlite"
REPORT = ROOT / "yado_github_boot_report.json"

def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def restore_live_db():
    if LIVE_DB.exists(): LIVE_DB.unlink()
    sql=DUMP.read_text(encoding='utf-8')
    with sqlite3.connect(LIVE_DB) as db:
        db.executescript(sql)
        integrity=db.execute('PRAGMA integrity_check').fetchone()[0]
    if integrity!='ok': raise RuntimeError(f'LIVE_DB_RESTORE_INTEGRITY:{integrity}')

def main():
    integrity=bootstrap_integrity()
    restore_live_db()
    contract=active_contract()
    cls=load_active_kernel_class()
    kernel=cls(db_path=str(LIVE_DB))
    snapshot=kernel.unified_snapshot()
    with sqlite3.connect(LIVE_DB) as db:
        sqlite_integrity=db.execute('PRAGMA integrity_check').fetchone()[0]
        memory_events=kernel.memory_count()
    report={
      'schema':'yado.github_boot_report.v1',
      'started_at_utc':datetime.now(timezone.utc).isoformat(),
      'status':'RUNNING_BOOT_COMPLETED',
      'bootstrap_integrity':integrity,
      'active_contract':contract,
      'kernel_class':cls.__name__,
      'kernel_profile':getattr(cls,'PROFILE',None),
      'sqlite_integrity':sqlite_integrity,
      'memory_events':memory_events,
      'live_db_sha256':sha256(LIVE_DB),
      'live_state_dump_sha256':sha256(DUMP),
      'snapshot':snapshot,
      'host':'github_actions',
      'background_daemon':False,
      'canonical_durable_mutation':False,
    }
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    print(json.dumps({k:report[k] for k in ['status','kernel_class','kernel_profile','sqlite_integrity','memory_events','live_state_dump_sha256']},ensure_ascii=False))

if __name__=='__main__': main()
