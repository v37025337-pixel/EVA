from __future__ import annotations
from pathlib import Path
from typing import Any
import hashlib,json,re,urllib.request,urllib.error

def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o): return hashlib.sha256(canon(o).encode()).hexdigest()
def sha_bytes(b): return hashlib.sha256(b).hexdigest()

class YADOGoalActionBindingV1:
    COMPONENT_ID='CTRL-G2-GOAL-ACTION-BINDING-V1'

    ACTIONS=(
      {
        'action_id':'LIVE_RESOURCE_EVIDENCE_RECHECK',
        'contract':('live','resource','evidence','external','availability','content','comprehension','conflict','resolution','re-check','recheck'),
      },
      {
        'action_id':'EXPERIENCE_EVIDENCE_REVIEW',
        'contract':('experience','memory','provenance','history','evidence','retrieval','legacy'),
      },
      {
        'action_id':'GENOME_EVOLUTION',
        'contract':('logic','thinking','intelligence','code','genome','evolution','mechanism','architecture','repair'),
      },
    )

    def __init__(self,repo_root:Path):
        self.repo=Path(repo_root)

    @staticmethod
    def _tokens(text:str):
        return [x for x in re.findall(r'[a-z0-9]+',str(text).lower()) if len(x)>=3]

    @classmethod
    def select_action(cls,priority:dict[str,Any]):
        code=cls._tokens(priority.get('code',''))
        area=cls._tokens(priority.get('area',''))
        rec=cls._tokens(priority.get('recommended_action',''))
        weighted={}
        for t in code: weighted[t]=weighted.get(t,0)+3
        for t in area: weighted[t]=weighted.get(t,0)+2
        for t in rec: weighted[t]=weighted.get(t,0)+1
        rows=[]
        for a in cls.ACTIONS:
            contract=set(cls._tokens(' '.join(a['contract'])))
            score=sum(w for t,w in weighted.items() if t in contract)
            rows.append({'action_id':a['action_id'],'score':score,'matched_tokens':sorted(t for t in weighted if t in contract)})
        rows.sort(key=lambda x:(-x['score'],x['action_id']))
        if not rows or rows[0]['score']<=0:
            return {'status':'WITHHOLD_NO_RELEVANT_ACTION','selected_action':None,'ranking':rows}
        return {'status':'ACTION_SELECTED','selected_action':rows[0]['action_id'],'ranking':rows}

    @staticmethod
    def _fetch(url,timeout=20,max_bytes=300000):
        req=urllib.request.Request(url,headers={'User-Agent':'YADO-G2-Goal-Action-Binding/1.0','Accept':'application/vnd.github+json,text/plain,*/*'})
        try:
            with urllib.request.urlopen(req,timeout=timeout) as r:
                body=r.read(max_bytes)
                return {'ok':True,'http_status':int(getattr(r,'status',200) or 200),'body':body,'sha256':sha_bytes(body),'bytes':len(body)}
        except urllib.error.HTTPError as e:
            body=e.read(min(max_bytes,100000))
            return {'ok':False,'http_status':int(e.code),'error':'HTTPError','sha256':sha_bytes(body),'bytes':len(body)}
        except Exception as e:
            return {'ok':False,'http_status':None,'error':type(e).__name__+':'+str(e)[:300]}

    @staticmethod
    def _parse_sources_js(src:str):
        providers={}
        in_sources=False
        current=None
        for line in src.splitlines():
            if re.search(r'export\s+const\s+sources\s*=\s*\{',line):
                in_sources=True; continue
            if not in_sources: continue
            if current is None and re.match(r'^\s*}\s*;?\s*$',line):
                break
            m=re.match(r"^\s*(?:'([^']+)'|([A-Za-z0-9_-]+))\s*:\s*\{\s*$",line)
            if m:
                key=m.group(1) or m.group(2); current={'provider_key':key};providers[key]=current;continue
            if current is None: continue
            if re.match(r'^\s*}\s*,?\s*$',line):
                current=None;continue
            mm=re.match(r"^\s*name\s*:\s*['\"]([^'\"]*)['\"]",line)
            if mm: current['name']=mm.group(1)
            mm=re.match(r"^\s*url\s*:\s*['\"]([^'\"]*)['\"]",line)
            if mm: current['url']=mm.group(1)
            if re.match(r'^\s*noKeyNeeded\s*:\s*true',line): current['no_key_needed']=True
        return providers

    def _live_resource_evidence_recheck(self):
        prior_path=self.repo/'candidates/kernel-self-generated/g2-fcm-external-coding-resource-study-v1.json'
        if not prior_path.exists():
            return {'status':'WITHHOLD_NO_PRIOR_EXTERNAL_RESOURCE_EVIDENCE','direct_priority_evidence':False}
        prior=json.loads(prior_path.read_text(encoding='utf-8'))
        repo_name=((prior.get('upstream') or {}).get('repository') or '').strip()
        if '/' not in repo_name:
            return {'status':'WITHHOLD_PRIOR_RESOURCE_IDENTITY_MISSING','direct_priority_evidence':False}
        api='https://api.github.com/repos/'+repo_name+'/commits/main'
        raw='https://raw.githubusercontent.com/'+repo_name+'/main/'
        commit=self._fetch(api)
        files={name:self._fetch(raw+name) for name in ('README.md','sources.js','package.json')}
        commit_json={}
        if commit.get('ok'):
            try: commit_json=json.loads(commit['body'].decode('utf-8','replace'))
            except Exception: commit_json={}
        live_commit=commit_json.get('sha')
        readme_text=files['README.md'].get('body',b'').decode('utf-8','replace') if files['README.md'].get('ok') else ''
        sources_text=files['sources.js'].get('body',b'').decode('utf-8','replace') if files['sources.js'].get('ok') else ''
        package_text=files['package.json'].get('body',b'').decode('utf-8','replace') if files['package.json'].get('ok') else ''
        providers=self._parse_sources_js(sources_text) if sources_text else {}
        no_key=sorted(k for k,v in providers.items() if v.get('no_key_needed'))
        package={}
        try: package=json.loads(package_text) if package_text else {}
        except Exception: package={}
        title=''
        for line in readme_text.splitlines():
            if line.lstrip().startswith('#'):
                title=line.lstrip('#').strip();break
        prior_up=prior.get('upstream') or {}
        prior_files=prior_up.get('file_evidence') or {}
        prior_catalog=prior.get('catalog') or {}
        conflicts=[]
        prior_commit=((prior_up.get('commit') or {}).get('sha'))
        if prior_commit and live_commit and prior_commit!=live_commit:
            conflicts.append({'field':'commit_sha','prior':prior_commit,'live':live_commit,'resolution':'LIVE_SUPERSEDES_PRIOR_MUTABLE_STATE'})
        for name,row in files.items():
            psha=(prior_files.get(name) or {}).get('sha256')
            lsha=row.get('sha256')
            if psha and lsha and psha!=lsha:
                conflicts.append({'field':'file_sha256:'+name,'prior':psha,'live':lsha,'resolution':'LIVE_SUPERSEDES_PRIOR_MUTABLE_STATE'})
        if prior_catalog.get('provider_count') is not None and providers and int(prior_catalog['provider_count'])!=len(providers):
            conflicts.append({'field':'provider_count','prior':prior_catalog['provider_count'],'live':len(providers),'resolution':'LIVE_PARSED_CATALOG_SUPERSEDES_PRIOR'})
        prior_no_key=sorted(prior_catalog.get('no_key_provider_keys') or [])
        if prior_no_key and no_key and prior_no_key!=no_key:
            conflicts.append({'field':'no_key_provider_keys','prior':prior_no_key,'live':no_key,'resolution':'LIVE_PARSED_CATALOG_SUPERSEDES_PRIOR'})
        required_fetch=commit.get('ok') and all(files[x].get('ok') for x in ('README.md','sources.js','package.json'))
        comprehension={
          'repository_commit_identity_extracted':bool(live_commit),
          'readme_title_extracted':bool(title),
          'package_identity_extracted':bool(package.get('name')),
          'provider_catalog_extracted':len(providers)>0,
          'no_key_provider_set_extracted':len(no_key)>0,
          'cross_file_provider_mentions':sum(1 for k in no_key if k.lower() in readme_text.lower()),
        }
        comprehension_pass=all([
          comprehension['repository_commit_identity_extracted'],
          comprehension['readme_title_extracted'],
          comprehension['package_identity_extracted'],
          comprehension['provider_catalog_extracted'],
          comprehension['no_key_provider_set_extracted'],
        ])
        conflict_resolution_pass=all(x.get('resolution') for x in conflicts) if conflicts else True
        passed=bool(required_fetch and comprehension_pass and conflict_resolution_pass)
        out={
          'status':'PASS_DIRECT_LIVE_RESOURCE_EVIDENCE_RECHECK' if passed else 'WITHHOLD_DIRECT_LIVE_RESOURCE_EVIDENCE_RECHECK',
          'direct_priority_evidence':passed,
          'resource_repository':repo_name,
          'live_commit_sha':live_commit,
          'fetch':{
            'commit':{k:v for k,v in commit.items() if k!='body'},
            'files':{n:{k:v for k,v in row.items() if k!='body'} for n,row in files.items()},
          },
          'comprehension':comprehension,
          'live_semantic_extract':{
            'readme_title':title,
            'package_name':package.get('name'),
            'package_version':package.get('version'),
            'provider_count':len(providers),
            'no_key_provider_keys':no_key,
          },
          'prior_vs_live_conflicts':conflicts,
          'conflict_resolution_policy':'WHEN LIVE FETCH AND PARSE SUCCEED, CURRENT CONTENT-ADDRESSED LIVE EVIDENCE SUPERSEDES PRIOR MUTABLE CATALOG CLAIMS',
          'conflict_resolution_pass':conflict_resolution_pass,
          'canonical_mutation':False,
        }
        out['evidence_digest']=digest(out)
        return out

    def execute(self,priority:dict[str,Any],core):
        sel=self.select_action(priority)
        action=sel.get('selected_action')
        if action is None:
            return {'selection':sel,'status':'WITHHOLD_GOAL_ACTION_BINDING','direct_priority_evidence':False}
        if action=='LIVE_RESOURCE_EVIDENCE_RECHECK':
            result=self._live_resource_evidence_recheck()
        elif action=='EXPERIENCE_EVIDENCE_REVIEW':
            tokens=self._tokens(priority.get('code','')+' '+priority.get('recommended_action',''))
            rows=core.experience_search(tokens or ['experience','evidence'],limit=8)
            result={'status':'PASS_DIRECT_EXPERIENCE_EVIDENCE_REVIEW' if rows else 'WITHHOLD_EXPERIENCE_EVIDENCE_REVIEW',
                    'direct_priority_evidence':bool(rows),'rows':rows,'canonical_mutation':False}
        elif action=='GENOME_EVOLUTION':
            evo=core.evolve_cognitive_code_genome()
            result={'status':'PASS_DIRECT_GENOME_EVOLUTION' if evo.get('selection')=='CHILD' else 'WITHHOLD_GENOME_EVOLUTION',
                    'direct_priority_evidence':evo.get('selection')=='CHILD','native_evolution_result':evo,'canonical_mutation':False}
        else:
            result={'status':'WITHHOLD_UNKNOWN_ACTION','direct_priority_evidence':False}
        return {'selection':sel,'selected_action':action,'result':result,
                'direct_priority_evidence':bool(result.get('direct_priority_evidence')),
                'component_id':self.COMPONENT_ID,
                'semantic_boundary':'HOST-CREATED GENERIC GOAL-TO-ACTION BINDER ADDED ONLY AFTER THREE OBSERVED PRIORITY/ACTION MISMATCHES. ACTION CHOICE IS CONTRACT-SCORED; EVIDENCE EXECUTION REMAINS BOUNDED AND CANONICAL-IMMUTABLE.'}

__all__=['YADOGoalActionBindingV1']
