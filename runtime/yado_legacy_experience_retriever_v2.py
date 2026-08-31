from __future__ import annotations
from pathlib import Path
import hashlib,json,re,subprocess,urllib.parse,urllib.request

class LegacyExperienceRetrieverV1:
    COMPONENT_ID="ALG-G2-LEGACY-EXPERIENCE-RETRIEVER-V1"
    def __init__(self,repo_root,registry,repo_slug="v37025337-pixel/EVA",max_file_bytes=524288):
        self.repo=Path(repo_root)
        self.registry=registry
        self.repo_slug=repo_slug
        self.max_file_bytes=int(max_file_bytes)

    def _run(self,cmd,timeout):
        return subprocess.run(cmd,cwd=self.repo,capture_output=True,timeout=timeout)

    @staticmethod
    def _safe_path(path):
        s=str(path).replace(chr(92),"/")
        return bool(s) and not s.startswith("/") and ".." not in s.split("/")

    def _read_exact(self,commit,path):
        ep="/".join(urllib.parse.quote(x,safe="") for x in path.split("/"))
        url=f"https://raw.githubusercontent.com/{self.repo_slug}/{commit}/{ep}"
        rq=urllib.request.Request(url,headers={"User-Agent":"YADO-Legacy-Experience-Retriever/1.0"})
        with urllib.request.urlopen(rq,timeout=15) as resp:
            return resp.read(self.max_file_bytes+1),"RAW_HTTPS_EXACT"

    def read_registered(self,branch,path):
        entry=next((x for x in self.registry.get("branches",[]) if x.get("branch")==branch),None)
        if not entry or entry.get("mode")!="EXPERIENCE_ONLY":
            raise KeyError("LEGACY_BRANCH_NOT_REGISTERED")
        if path not in entry.get("evidence",[]):
            raise KeyError("EVIDENCE_PATH_NOT_REGISTERED")
        if not self._safe_path(path):
            raise ValueError("UNSAFE_LEGACY_PATH")
        commit=entry["head_sha"]
        data,transport=self._read_exact(commit,path)
        if len(data)>self.max_file_bytes:
            raise ValueError("LEGACY_EVIDENCE_TOO_LARGE")
        return {
          "branch":branch,"registered_commit":commit,"path":path,
          "transport":transport,"bytes":len(data),
          "sha256":hashlib.sha256(data).hexdigest(),
          "git_blob_sha1":hashlib.sha1((f"blob {len(data)}"+chr(0)).encode()+data).hexdigest(),
          "content":data.decode("utf-8","replace")
        }

    def search_content(self,query,limit=8):
        tokens={x for x in re.findall(r"[a-zA-Z0-9_]+",str(query).lower()) if len(x)>2}
        rows=[]
        for entry in self.registry.get("branches",[]):
            if entry.get("mode")!="EXPERIENCE_ONLY": continue
            meta=" ".join([entry.get("branch",""),entry.get("role","")," ".join(entry.get("tags",[]))," ".join(entry.get("lessons",[]))]).lower()
            mt=re.findall(r"[a-zA-Z0-9_]+",meta)
            mcov=sum(1 for t in tokens if t in mt)/max(1,len(tokens));mraw=sum(mt.count(t) for t in tokens)
            for path in entry.get("evidence",[]):
                try: item=self.read_registered(entry["branch"],path)
                except Exception: continue
                text=item["content"].lower();ct=re.findall(r"[a-zA-Z0-9_]+",text)
                hits={t:ct.count(t) for t in tokens}
                ccov=sum(1 for t in tokens if hits[t]>0)/max(1,len(tokens))
                score=mcov*40.0+mraw*3.0+ccov*3.0+sum(hits.values())/max(1,len(ct))
                if score: rows.append({k:v for k,v in item.items() if k!="content"}|{"score":score,"snippet":item["content"][:1200]})
        rows.sort(key=lambda x:(-x["score"],x["branch"],x["path"]))
        return rows[:max(1,int(limit))]
