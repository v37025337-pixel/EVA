from __future__ import annotations
import re, sqlite3
from typing import Any
STUDY_DIGEST='8cef87947637c9d64c7665edbe3090a4b56ff999d5e813a39e4990fb52d536cd'
LEARNED_SKILLS=['LOCAL_SQLITE_LAB', 'PARAMETERIZED_SQL', 'PYDB:commit_method', 'PYDB:execute', 'PYDB:executemany', 'PYDB:fetchall', 'PYDB:rollback_method', 'PYDB:sqlite3_connect', 'READ_ONLY_JSON_API', 'SQL:commit', 'SQL:create_table', 'SQL:delete', 'SQL:insert', 'SQL:join', 'SQL:order_by', 'SQL:rollback', 'SQL:select', 'SQL:transaction', 'SQL:update', 'SQL:where', 'TRANSACTION_ROLLBACK', 'WEB:fetch_api', 'WEB:get', 'WEB:headers', 'WEB:json', 'WEB:query_parameters', 'WEB:request', 'WEB:response', 'WEB:status']
_SAFE=re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')
def _ident(x):
    if not _SAFE.fullmatch(x): raise ValueError('unsafe identifier')
    return x
def select_where(conn: sqlite3.Connection, table: str, columns: list[str], where_column: str, value: Any):
    q=f"SELECT {', '.join(_ident(c) for c in columns)} FROM {_ident(table)} WHERE {_ident(where_column)} = ?"
    return conn.execute(q,(value,)).fetchall()
def summarize_json_shape(payload):
    if isinstance(payload,dict): return {'type':'object','keys':sorted(map(str,payload)),'size':len(payload)}
    if isinstance(payload,list): return {'type':'array','size':len(payload)}
    return {'type':type(payload).__name__}
def component():
    return {'schema':'yado.database_web_usage_candidate.v1','study_digest':STUDY_DIGEST,
            'learned_skills':LEARNED_SKILLS,'development_candidate':True,'canonical_active':False,
            'remote_code_execution':False,'authenticated_access':False}
