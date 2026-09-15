#!/usr/bin/env python3
from __future__ import annotations

import argparse, hashlib, json, re, sqlite3, ssl, urllib.error, urllib.parse, urllib.request
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

SCHEMA = "yado.database_programming_study.v1"
UA = "YADO-Public-Study/1.0"
ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
CANDIDATE = REPO / "candidates" / "cognitive" / "yado_database_web_usage_candidate_v1.py"

SQL = {
    "select": r"\bSELECT\b", "where": r"\bWHERE\b", "join": r"\bJOIN\b",
    "group_by": r"\bGROUP\s+BY\b", "order_by": r"\bORDER\s+BY\b",
    "insert": r"\bINSERT\b", "update": r"\bUPDATE\b", "delete": r"\bDELETE\b",
    "create_table": r"\bCREATE\s+TABLE\b", "create_index": r"\bCREATE\s+(?:UNIQUE\s+)?INDEX\b",
    "transaction": r"\bTRANSACTION\b|\bBEGIN\b", "commit": r"\bCOMMIT\b",
    "rollback": r"\bROLLBACK\b", "explain": r"\bEXPLAIN\b",
}
PYDB = {
    "sqlite3_connect": r"sqlite3\.connect\s*\(", "execute": r"\.execute\s*\(",
    "executemany": r"\.executemany\s*\(", "fetchall": r"\.fetchall\s*\(",
    "commit_method": r"\.commit\s*\(", "rollback_method": r"\.rollback\s*\(",
}
WEB = {
    "fetch_api": r"\bfetch\s*\(", "request": r"\bRequest\b", "response": r"\bResponse\b",
    "json": r"\bjson\b|\.json\s*\(", "headers": r"\bheaders?\b",
    "status": r"\bstatus\b", "get": r"\bGET\b", "query_parameters": r"\bquery\s+parameters?\b|\bURLSearchParams\b",
}

class Parser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.text_parts, self.code_parts, self.skip, self.in_code = [], [], 0, 0
    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in {"script","style","noscript","svg"}: self.skip += 1
        if tag in {"code","pre"}: self.in_code += 1
    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in {"script","style","noscript","svg"} and self.skip: self.skip -= 1
        if tag in {"code","pre"} and self.in_code: self.in_code -= 1
    def handle_data(self, data):
        if self.skip: return
        self.text_parts.append(data)
        if self.in_code: self.code_parts.append(data)
    def text(self): return re.sub(r"\s+", " ", " ".join(self.text_parts)).strip()
    def code(self): return re.sub(r"\s+", " ", " ".join(self.code_parts)).strip()

def canon(x): return json.dumps(x, sort_keys=True, separators=(",",":"), ensure_ascii=False)
def sha(x): return hashlib.sha256(canon(x).encode()).hexdigest()

def fetch(url: str, max_bytes: int, timeout: int, accept: str) -> dict[str, Any]:
    p = urllib.parse.urlparse(url)
    if p.scheme != "https" or not p.hostname:
        return {"status":"BLOCKED_NON_HTTPS","url":url}
    req = urllib.request.Request(url, headers={"User-Agent":UA,"Accept":accept}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ssl.create_default_context()) as r:
            final = urllib.parse.urlparse(r.geturl())
            if final.scheme != "https":
                return {"status":"BLOCKED_REDIRECT_NON_HTTPS","url":url}
            data = r.read(max_bytes + 1)[:max_bytes]
            enc = r.headers.get_content_charset() or "utf-8"
            return {
                "status":"FETCHED","url":url,"final_url":r.geturl(),"host":final.hostname,
                "http_status":getattr(r,"status",200),"content_type":(r.headers.get("Content-Type") or "").lower(),
                "bytes":len(data),"sha256":hashlib.sha256(data).hexdigest(),
                "_text":data.decode(enc, errors="replace"),
            }
    except urllib.error.HTTPError as e:
        return {"status":"HTTP_ERROR","url":url,"http_status":e.code,"error":str(e)}
    except Exception as e:
        return {"status":"FETCH_ERROR","url":url,"error":f"{type(e).__name__}:{e}"}

def detect(patterns: dict[str,str], text: str) -> dict[str,int]:
    return {k: len(re.findall(v, text, re.I | re.M)) for k,v in patterns.items()}

def sqlite_lab() -> dict[str, Any]:
    c = sqlite3.connect(":memory:")
    try:
        c.executescript("""
        PRAGMA foreign_keys=ON;
        CREATE TABLE users(id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE);
        CREATE TABLE orders(id INTEGER PRIMARY KEY, user_id INTEGER REFERENCES users(id), total REAL CHECK(total>=0));
        CREATE INDEX idx_orders_user_id ON orders(user_id);
        """)
        c.executemany("INSERT INTO users(id,name) VALUES (?,?)", [(1,"Ada"),(2,"Linus"),(3,"Grace")])
        c.executemany("INSERT INTO orders(id,user_id,total) VALUES (?,?,?)",
                      [(1,1,10.0),(2,1,20.0),(3,2,7.5),(4,3,100.0),(5,3,5.0)])
        c.commit()
        rows = c.execute("""
            SELECT u.name, COUNT(o.id), ROUND(SUM(o.total),2)
            FROM users u JOIN orders o ON o.user_id=u.id
            GROUP BY u.id,u.name HAVING SUM(o.total)>=?
            ORDER BY SUM(o.total) DESC,u.name
        """,(20.0,)).fetchall()
        aggregate_join = rows == [("Grace",2,105.0),("Ada",2,30.0)]
        plan = c.execute("EXPLAIN QUERY PLAN SELECT * FROM orders WHERE user_id=?", (1,)).fetchall()
        index_used = any("idx_orders_user_id" in " ".join(map(str,x)) for x in plan)
        before = c.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        c.execute("BEGIN"); c.execute("INSERT INTO orders(user_id,total) VALUES (?,?)",(2,999.0)); c.rollback()
        rollback = c.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == before
        hostile = "Eve'; DROP TABLE users;--"
        c.execute("INSERT INTO users(name) VALUES (?)",(hostile,)); c.commit()
        safe = c.execute("SELECT name FROM users WHERE name=?",(hostile,)).fetchone() == (hostile,)
        safe = safe and c.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='users'").fetchone()[0] == 1
        ok = aggregate_join and index_used and rollback and safe
        return {"status":"PASS" if ok else "FAIL","aggregate_join":aggregate_join,"index_used":index_used,
                "rollback":rollback,"parameterization":safe,
                "proved":["CREATE_TABLE","CREATE_INDEX","PARAMETERIZED_INSERT","SELECT","JOIN","GROUP_BY",
                          "HAVING","ORDER_BY","EXPLAIN_QUERY_PLAN","TRANSACTION_ROLLBACK","PARAMETERIZED_LOOKUP"]}
    finally:
        c.close()

def api_lab(url: str, max_bytes: int, timeout: int) -> dict[str, Any]:
    r = fetch(url,max_bytes,timeout,"application/json")
    if r.get("status") != "FETCHED":
        return {"status":"FAIL","transport":{k:v for k,v in r.items() if not k.startswith("_")}}
    try: payload = json.loads(r["_text"])
    except Exception as e: return {"status":"FAIL","error":f"JSON_PARSE:{type(e).__name__}"}
    if not isinstance(payload,dict): return {"status":"FAIL","error":"EXPECTED_OBJECT"}
    return {"status":"PASS" if {"id","title"}.issubset(payload) else "FAIL","host":r["host"],
            "http_status":r["http_status"],"sha256":r["sha256"],"keys":sorted(map(str,payload)),
            "raw_payload_persisted":False,"authenticated_access":False,"external_write":False}

def emit_candidate(study_digest: str, skills: list[str]) -> str:
    CANDIDATE.parent.mkdir(parents=True, exist_ok=True)
    src = f"""from __future__ import annotations
import re, sqlite3
from typing import Any
STUDY_DIGEST={study_digest!r}
LEARNED_SKILLS={skills!r}
_SAFE=re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')
def _ident(x):
    if not _SAFE.fullmatch(x): raise ValueError('unsafe identifier')
    return x
def select_where(conn: sqlite3.Connection, table: str, columns: list[str], where_column: str, value: Any):
    q=f\"SELECT {{', '.join(_ident(c) for c in columns)}} FROM {{_ident(table)}} WHERE {{_ident(where_column)}} = ?\"
    return conn.execute(q,(value,)).fetchall()
def summarize_json_shape(payload):
    if isinstance(payload,dict): return {{'type':'object','keys':sorted(map(str,payload)),'size':len(payload)}}
    if isinstance(payload,list): return {{'type':'array','size':len(payload)}}
    return {{'type':type(payload).__name__}}
def component():
    return {{'schema':'yado.database_web_usage_candidate.v1','study_digest':STUDY_DIGEST,
            'learned_skills':LEARNED_SKILLS,'development_candidate':True,'canonical_active':False,
            'remote_code_execution':False,'authenticated_access':False}}
"""
    compile(src,str(CANDIDATE),"exec"); CANDIDATE.write_text(src,encoding="utf-8")
    return hashlib.sha256(CANDIDATE.read_bytes()).hexdigest()

def run(cfg: dict[str,Any]) -> dict[str,Any]:
    lim=cfg["limits"]; rows=[]; sql=Counter(); pydb=Counter(); web=Counter(); code_pages=0
    for s in cfg["sources"][:int(lim["max_total_pages"])]:
        r=fetch(s["url"],int(lim["max_bytes_per_page"]),int(lim["timeout_seconds"]),"text/html,text/plain;q=0.9,*/*;q=0.1")
        out={k:v for k,v in r.items() if not k.startswith("_")}; out.update({"source_id":s["source_id"],"category":s["category"]})
        if r.get("status")=="FETCHED":
            p=Parser(); p.feed(r["_text"]); combined=p.text()+"\n"+p.code()
            a,b,d=detect(SQL,combined),detect(PYDB,combined),detect(WEB,combined)
            sql.update(a); pydb.update(b); web.update(d); code_pages += int(bool(p.code()))
            out["derived"]={"sql":sorted(k for k,v in a.items() if v),
                            "python_db":sorted(k for k,v in b.items() if v),
                            "web_http":sorted(k for k,v in d.items() if v),
                            "code_text_observed":bool(p.code()),"raw_text_persisted":False,"raw_code_persisted":False}
        rows.append(out)
    sl=sqlite_lab(); al=api_lab(cfg["public_api_lab"]["url"],int(lim["max_bytes_per_page"]),int(lim["timeout_seconds"]))
    sql_sk=sorted(k for k,v in sql.items() if v); py_sk=sorted(k for k,v in pydb.items() if v); web_sk=sorted(k for k,v in web.items() if v)
    fetched=sum(r.get("status")=="FETCHED" for r in rows)
    db=sum(r.get("status")=="FETCHED" and r.get("category")=="database" for r in rows)
    prog=sum(r.get("status")=="FETCHED" and r.get("category") in {"programming","web_programming"} for r in rows)
    gates=cfg["gates"]
    ok=(fetched>=gates["min_fetched_sources"] and db>=gates["min_database_sources"] and
        prog>=gates["min_programming_sources"] and len(sql_sk)>=gates["min_sql_skills"] and
        len(web_sk)>=gates["min_web_skills"] and sl["status"]=="PASS" and al["status"]=="PASS")
    skills=sorted({"LOCAL_SQLITE_LAB","PARAMETERIZED_SQL","TRANSACTION_ROLLBACK","READ_ONLY_JSON_API"} |
                  {f"SQL:{x}" for x in sql_sk}|{f"PYDB:{x}" for x in py_sk}|{f"WEB:{x}" for x in web_sk})
    grounding={"sources":[{"source_id":r.get("source_id"),"category":r.get("category"),"host":r.get("host"),
                           "sha256":r.get("sha256"),"status":r.get("status"),"derived":r.get("derived")} for r in rows],
               "sqlite_lab":sl,"api_lab":al,"skills":skills}
    sd=sha(grounding); cand=emit_candidate(sd,skills) if ok else None
    report={"schema":SCHEMA,"status":"PASS_DATABASE_PROGRAMMING_STUDY_V1" if ok else "WITHHOLD_DATABASE_PROGRAMMING_STUDY_V1",
            "goal":cfg["goal"],"study_digest":sd,"fetched_sources":fetched,"database_source_success":db,
            "programming_source_success":prog,"source_receipts":rows,
            "skill_coverage":{"sql":sql_sk,"python_database":py_sk,"web_http":web_sk,"learned_skill_count":len(skills)},
            "code_observation":{"pages_with_code_content":code_pages,"raw_code_persisted":False,"remote_code_executed":False},
            "local_database_lab":sl,"public_api_lab":al,
            "candidate":{"path":str(CANDIDATE.relative_to(REPO)) if cand else None,"sha256":cand,
                         "development_candidate":bool(cand),"canonical_active":False},
            "safety_boundary":{"public_https_read_only":True,"authenticated_access":False,"credential_discovery":False,
                               "credential_values_used":False,"remote_code_execution":False,"external_writes":False,
                               "raw_remote_text_persisted":False,"raw_remote_code_persisted":False,"canonical_mutation":False}}
    report["receipt_sha256"]=sha(report); return report

def self_test():
    r=sqlite_lab(); assert r["status"]=="PASS" and r["parameterization"] and r["rollback"],r
    x=detect(SQL,"SELECT a FROM t JOIN x ON x.id=t.id GROUP BY a ORDER BY a")
    assert x["select"] and x["join"] and x["group_by"] and x["order_by"],x
    print("PASS_DATABASE_PROGRAMMING_STUDY_SELF_TEST")

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--config",type=Path); ap.add_argument("--out",type=Path); ap.add_argument("--self-test",action="store_true")
    a=ap.parse_args()
    if a.self_test: self_test(); return
    if not a.config or not a.out: raise SystemExit("--config and --out required")
    r=run(json.loads(a.config.read_text(encoding="utf-8"))); a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(r,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"status":r["status"],"fetched_sources":r["fetched_sources"],"db":r["database_source_success"],
                      "programming":r["programming_source_success"],"skills":r["skill_coverage"],
                      "sqlite_lab":r["local_database_lab"]["status"],"api_lab":r["public_api_lab"]["status"],
                      "candidate_sha256":r["candidate"]["sha256"],"study_digest":r["study_digest"]},sort_keys=True))
    if r["status"]!="PASS_DATABASE_PROGRAMMING_STUDY_V1": raise SystemExit(2)

if __name__=="__main__": main()
