"""Bounded public source capture and benign Hoppscotch echo observations."""
import concurrent.futures
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import secrets
import sys
import urllib.error
import urllib.parse
import urllib.request

REPOS = {
    'hoppscotch/hoppscotch': [],
    'danielmiessler/SecLists': ['Fuzzing/special-chars.txt', 'Fuzzing/JSON.Fuzzing.txt'],
    'HackTricks-wiki/hacktricks': ['src/pentesting-web/json-xml-yaml-hacking.md'],
    'swisskyrepo/PayloadsAllTheThings': ['Encoding Transformations/README.md'],
}
HOSTS = {'api.github.com', 'raw.githubusercontent.com', 'echo.hoppscotch.io'}
MAX_BYTES = 1_000_000

def allowed(url):
    p = urllib.parse.urlsplit(url)
    if p.scheme != 'https' or p.hostname not in HOSTS or p.port not in (None,443) or p.username or p.password:
        raise ValueError('UNEXPECTED_PUBLIC_DESTINATION')
    if p.hostname == 'echo.hoppscotch.io' and p.path not in ('','/'):
        raise ValueError('ONLY_DEMONSTRATION_ECHO_ROOT')

class PublicRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        allowed(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)

def fetch(out, url, *, method='GET', data=None):
    allowed(url)
    if method not in ('GET','POST') or method == 'POST' and urllib.parse.urlsplit(url).hostname != 'echo.hoppscotch.io':
        raise ValueError('UNSUPPORTED_CAPTURE_METHOD')
    headers = {'User-Agent':'YADO-bounded-learning/1.0'}
    if data is not None:
        headers['Content-Type']='application/json'
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.build_opener(PublicRedirect()).open(request,timeout=20) as response:
        raw=response.read(MAX_BYTES+1)
        if len(raw)>MAX_BYTES:
            raise ValueError('SOURCE_BYTE_BUDGET')
        allowed(response.url)
        receipt={'url':url,'final_url':response.url,'status':response.status,'method':method,
                 'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),
                 'fetched_at':datetime.now(timezone.utc).isoformat(),
                 'transport':'ASSISTANT_AUTHORED_HOST_HTTPS','credentials_supplied':False}
    folder=out/'bytes';folder.mkdir(exist_ok=True)
    (folder/(receipt['sha256']+'.txt')).write_bytes(raw)
    return raw.decode('utf-8'),receipt

def capture_repo(out, repo, paths):
    raw,metadata_receipt=fetch(out,'https://api.github.com/repos/'+repo)
    metadata=json.loads(raw)
    raw,commit_receipt=fetch(out,'https://api.github.com/repos/'+repo+'/commits/'+metadata['default_branch'])
    revision=json.loads(raw)['sha']
    docs=[]
    for path in ['README.md',*paths]:
        url='https://raw.githubusercontent.com/'+repo+'/'+revision+'/'+urllib.parse.quote(path)
        text,receipt=fetch(out,url)
        docs.append({'path':path,**receipt})
    return {'repository':repo,'revision':revision,'status':'FETCHED_REAL_CONTENT',
            'metadata':metadata_receipt,'commit':commit_receipt,'documents':docs}

def echo(out, method, purpose):
    # Security corpus strings never enter these requests. Only fresh benign labels.
    label='yado-'+purpose+'-'+secrets.token_hex(8)
    request_object={'lesson':label}
    payload=json.dumps(request_object,separators=(',',':')).encode() if method=='POST' else None
    text,receipt=fetch(out,'https://echo.hoppscotch.io/?'+urllib.parse.urlencode(request_object),method=method,data=payload)
    obj=json.loads(text)
    assert obj['method']==method and obj['args']['lesson']==label and obj['path']=='/'
    assert obj['data']==(payload.decode() if payload else '')
    # Remove network routing/signature headers from the learner's input. The exact
    # raw response and its hash remain in the user's private checkpoint, not Git.
    projection={k:obj[k] for k in ('method','args','data','path')}
    return {'receipt':receipt,'purpose':purpose,'request_method':method,
            'request_data':payload.decode() if payload else '',
            'projection':projection,'projection_fields':list(projection),
            'raw_response_hash':receipt['sha256']}

def main(out):
    out.mkdir(parents=True,exist_ok=True)
    inventory=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        jobs={pool.submit(capture_repo,out,repo,paths):repo for repo,paths in REPOS.items()}
        for future in concurrent.futures.as_completed(jobs):
            try: inventory.append(future.result())
            except Exception as exc: inventory.append({'repository':jobs[future],'status':'WITHHOLD','error':type(exc).__name__+':'+str(exc)})
    (out/'sources.json').write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'sources_fetched':sum(x['status']=='FETCHED_REAL_CONTENT' for x in inventory),'sources_requested':len(REPOS)}),flush=True)
    if any(x['status']!='FETCHED_REAL_CONTENT' for x in inventory):
        raise ValueError('REQUIRED_SOURCE_UNAVAILABLE')
    observations=[]
    for index,method in enumerate(('GET','POST','POST','GET','POST','GET')):
        observations.append(echo(out,method,'training' if index<3 else 'validation' if index<5 else 'query'))
        (out/'echo-observations.json').write_text(json.dumps(observations,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({'echo':index+1,'method':method,'http_status':observations[-1]['receipt']['status']}),flush=True)

if __name__=='__main__':
    main(Path(sys.argv[1]).resolve())
