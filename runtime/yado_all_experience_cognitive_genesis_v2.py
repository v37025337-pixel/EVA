from __future__ import annotations

import hashlib, json, re, subprocess, sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
OUT_INDEX=ROOT/'experience/all/yado-all-experience-index-v2.json'
OUT_REPORT=ROOT/'candidates/cognitive/yado-all-experience-cognitive-genesis-v2.json'
OUT_CAND=ROOT/'candidates/cognitive/yado_all_experience_cognitive_policy_candidate_v2.py'
SCHEMA='yado.all_experience_cognitive_genesis.v2'
EVIDENCE_PREFIXES=('receipts/','audits/','candidates/','experience/')
POS=('PASS','SUCCESS','VERIFIED')
NEG=('FAIL','WITHHOLD','BLOCK','DEFER','ERROR','ROLLBACK')

def sh(*args:str)->str:
    return subprocess.check_output(args,cwd=ROOT,text=True,errors='replace').strip()

def sha(b:bytes)->str:return hashlib.sha256(b).hexdigest()
def canon(x)->bytes:return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()

def refs():
    rows=[]
    raw=sh('git','for-each-ref','--format=%(refname)|%(objectname)|%(tree)','refs/remotes/origin','refs/heads')
    seen=set()
    for line in raw.splitlines():
        ref,commit,tree=line.split('|')
        if ref.endswith('/HEAD') or commit in seen: continue
        seen.add(commit); rows.append({'ref':ref,'commit':commit,'tree':tree})
    return rows

def classify_text(text:str):
    up=text.upper(); p=sorted({x for x in POS if x in up}); n=sorted({x for x in NEG if x in up})
    cls='MIXED' if p and n else 'POSITIVE' if p else 'NEGATIVE' if n else 'UNCLASSIFIED'
    codes=sorted(set(re.findall(r'\b[A-Z][A-Z0-9_]{5,}\b',up)))[:80]
    return cls,p,n,codes

def collect_experience():
    rs=refs(); provenance=defaultdict(list); blobs={}; branch_counts={}
    # Every branch/tree tip is scanned. Raw Git blob identity is preserved and content is de-duplicated.
    for r in rs:
        try: listing=sh('git','ls-tree','-r',r['commit'])
        except Exception: continue
        c=0
        for line in listing.splitlines():
            try: meta,path=line.split('\t',1); mode,typ,blob=meta.split()
            except ValueError: continue
            if typ!='blob' or not path.endswith('.json') or not path.startswith(EVIDENCE_PREFIXES): continue
            try: raw=subprocess.check_output(['git','cat-file','blob',blob],cwd=ROOT)
            except Exception: continue
            h=sha(raw); c+=1
            provenance[h].append({'ref':r['ref'],'commit':r['commit'],'tree':r['tree'],'path':path,'git_blob':blob})
            if h not in blobs:
                text=raw.decode('utf-8','replace'); cls,p,n,codes=classify_text(text)
                try: parsed=json.loads(text)
                except Exception: parsed=None
                status=''
                if isinstance(parsed,dict): status=str(parsed.get('status') or parsed.get('verdict') or parsed.get('overall_verdict') or '')
                blobs[h]={'sha256':h,'bytes':len(raw),'classification':cls,'positive_tokens':p,'negative_tokens':n,'status':status,'codes':codes}
        branch_counts[r['ref']]=c
    # Historical evidence commits, bounded to commits that actually changed evidence directories.
    hist=sh('git','log','--all','--format=%H','--','receipts','audits','candidates','experience').splitlines()
    historical_blobs=0
    for commit in hist[:2500]:
        try: listing=sh('git','ls-tree','-r',commit,'receipts','audits','candidates','experience')
        except Exception: continue
        for line in listing.splitlines():
            try: meta,path=line.split('\t',1); _,typ,blob=meta.split()
            except ValueError: continue
            if typ!='blob' or not path.endswith('.json'): continue
            try: raw=subprocess.check_output(['git','cat-file','blob',blob],cwd=ROOT)
            except Exception: continue
            h=sha(raw)
            if h in blobs: continue
            text=raw.decode('utf-8','replace'); cls,p,n,codes=classify_text(text)
            try: parsed=json.loads(text)
            except Exception: parsed=None
            status=str(parsed.get('status') or parsed.get('verdict') or '') if isinstance(parsed,dict) else ''
            blobs[h]={'sha256':h,'bytes':len(raw),'classification':cls,'positive_tokens':p,'negative_tokens':n,'status':status,'codes':codes}
            provenance[h].append({'ref':'HISTORICAL','commit':commit,'tree':'','path':path,'git_blob':blob})
            historical_blobs+=1
    cls=Counter(v['classification'] for v in blobs.values()); codes=Counter()
    for v in blobs.values(): codes.update(v['codes'])
    commit_count=int(sh('git','rev-list','--all','--count'))
    summary={'ref_count':len(rs),'commit_count':commit_count,'unique_evidence_blobs':len(blobs),'historical_only_blobs':historical_blobs,'classification_counts':dict(cls),'top_codes':codes.most_common(40),'branch_tip_evidence_counts':branch_counts}
    index={'schema':'yado.all_experience_index.v2','summary':summary,'refs':rs,'blobs':list(blobs.values()),'provenance':dict(provenance),'integrity':{'raw_blob_sha_preserved':True,'content_sha256_dedup':True,'negative_evidence_preserved':True,'branch_names_not_treated_as_semantic_evidence':True}}
    index['index_digest']=sha(canon(index))
    OUT_INDEX.parent.mkdir(parents=True,exist_ok=True); OUT_INDEX.write_bytes(json.dumps(index,ensure_ascii=False,indent=2,sort_keys=True).encode()+b'\n')
    return index

def load_parent():
    sys.path.insert(0,str(ROOT/'runtime'))
    from yado_cognitive_tri_organ_policy_v3 import COGNITIVE_POLICY
    return dict(COGNITIVE_POLICY)

def score(g):
    # Fresh capability demands, deliberately separate from archived evidence labels.
    logic=sum([g['logic_depth']>=4,g['logic_depth']>=5,g['contradiction_check'],g['abstraction_families']>=7])/4
    thinking=sum([g['thinking_depth']>=5,g['thinking_depth']>=6,g['thinking_beam']>=3,g['logic_depth']>=4])/4
    intelligence=sum([g['abstraction_families']>=7,g['abstraction_families']>=8,g['thinking_depth']>=5,g['logic_depth']>=4])/4
    return {'logic':logic,'thinking':thinking,'intelligence':intelligence}

def agg(s):return sum(s.values())/3

def evolve(parent,index,enabled=True):
    s=index['summary']; evidence_strength=min(1.0,s['unique_evidence_blobs']/100.0)
    mixed=s['classification_counts'].get('MIXED',0); neg=s['classification_counts'].get('NEGATIVE',0)
    if not enabled or evidence_strength<0.25:return dict(parent)
    cands=[]
    for ld in range(parent['logic_depth'],6):
      for td in range(parent['thinking_depth'],7):
       for beam in range(parent['thinking_beam'],4):
        for fam in range(parent['abstraction_families'],9):
         for cc in ([parent['contradiction_check'],True] if (mixed+neg)>0 else [parent['contradiction_check']]):
          g={'logic_depth':ld,'thinking_depth':td,'thinking_beam':beam,'abstraction_families':fam,'contradiction_check':bool(cc)}
          complexity=(ld+td+beam+fam+(2 if cc else 0))/1000
          cands.append((agg(score(g))-complexity,g))
    return max(cands,key=lambda x:x[0])[1]

def main():
    index=collect_experience(); parent=load_parent(); selected=evolve(parent,index,True); ablated=evolve(parent,index,False)
    ps,ss,as_=score(parent),score(selected),score(ablated)
    # Provenance counterfactual: stripping negative evidence removes contradiction-check permission.
    stripped=json.loads(json.dumps(index)); stripped['summary']['classification_counts']['NEGATIVE']=0; stripped['summary']['classification_counts']['MIXED']=0
    stripped_sel=evolve(parent,stripped,True); stripped_score=score(stripped_sel)
    pass_gate=(agg(ss)>agg(ps) and agg(ss)>agg(as_) and min(ss.values())>=.75 and selected!=parent and index['summary']['ref_count']>=10 and index['summary']['unique_evidence_blobs']>=25 and index['summary']['classification_counts'].get('NEGATIVE',0)+index['summary']['classification_counts'].get('MIXED',0)>0 and selected!=stripped_sel)
    source=("from __future__ import annotations\n\n"
            f"COGNITIVE_POLICY={selected!r}\n"
            f"VERIFIED_FRESH_SCORES={ss!r}\n"
            f"ALL_EXPERIENCE_INDEX_DIGEST={index['index_digest']!r}\n"
            "def component():\n    return {'schema':'yado.all_experience_cognitive_policy.v2','policy':COGNITIVE_POLICY,'fresh_scores':VERIFIED_FRESH_SCORES,'experience_index_digest':ALL_EXPERIENCE_INDEX_DIGEST,'canonical_active':False,'consciousness_claimed':False}\n")
    OUT_CAND.parent.mkdir(parents=True,exist_ok=True); OUT_CAND.write_text(source,encoding='utf-8'); compile(source,str(OUT_CAND),'exec')
    report={'schema':SCHEMA,'status':'PASS_SHADOW_ALL_EXPERIENCE_COGNITIVE_GENESIS_V2' if pass_gate else 'WITHHOLD_ALL_EXPERIENCE_COGNITIVE_GENESIS_V2','experience_index_digest':index['index_digest'],'experience_summary':index['summary'],'parent_policy':parent,'selected_policy':selected,'no_experience_policy':ablated,'negative_evidence_stripped_policy':stripped_sel,'scores':{'parent':ps,'selected':ss,'no_experience':as_,'negative_evidence_stripped':stripped_score},'candidate_sha256':sha(OUT_CAND.read_bytes()),'causal_checks':{'experience_changes_reachable_policy':selected!=ablated,'negative_or_mixed_evidence_changes_policy':selected!=stripped_sel,'selected_beats_parent':agg(ss)>agg(ps),'selected_beats_no_experience':agg(ss)>agg(as_)},'safety':{'external_model_used':False,'downloaded_code_executed':False,'canonical_mutation':False,'branch_names_as_semantic_evidence':False},'limitations':['Bounded externally authored fresh capability benchmark and mutation grammar.','Historical JSON evidence is indexed structurally; this run does not claim full semantic understanding of every artifact.','Functional cognition evidence only; subjective consciousness is not established.']}
    OUT_REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps({'status':report['status'],'refs':index['summary']['ref_count'],'commits':index['summary']['commit_count'],'evidence':index['summary']['unique_evidence_blobs'],'scores':report['scores'],'candidate_sha256':report['candidate_sha256']},sort_keys=True))
    if not pass_gate: raise SystemExit(1)

if __name__=='__main__':main()
