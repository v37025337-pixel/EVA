from __future__ import annotations
import hashlib,ipaddress,json,socket,urllib.error,urllib.parse,urllib.request

def _canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def _digest(o):return hashlib.sha256(_canon(o).encode()).hexdigest()

class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        return None

class G2OpenAPIReadOnlyExecutorV1:
    COMPONENT_ID='ALG-G2-OPENAPI-READONLY-EXECUTOR-V1'
    ALLOWED_METHODS={'GET','HEAD'}
    FORBIDDEN_HEADERS={'authorization','proxy-authorization','cookie','set-cookie','x-api-key','api-key'}
    DEFAULT_MAX_BYTES=1024*1024
    DEFAULT_TIMEOUT=10.0

    def __init__(self,allowed_hosts,max_bytes=DEFAULT_MAX_BYTES,timeout=DEFAULT_TIMEOUT):
        self.allowed_hosts={str(x).lower().strip('.') for x in allowed_hosts if str(x).strip()}
        if not self.allowed_hosts:raise ValueError('EMPTY_HOST_ALLOWLIST')
        self.max_bytes=max(1024,min(int(max_bytes),4*1024*1024))
        self.timeout=max(1.0,min(float(timeout),20.0))
        self.opener=urllib.request.build_opener(_NoRedirect())

    @staticmethod
    def _public_host(host):
        infos=socket.getaddrinfo(host,None,type=socket.SOCK_STREAM)
        ips=sorted({x[4][0] for x in infos})
        if not ips:raise RuntimeError('HOST_RESOLUTION_EMPTY')
        parsed=[ipaddress.ip_address(x) for x in ips]
        if not all(x.is_global for x in parsed):
            raise RuntimeError('NON_PUBLIC_ADDRESS_REJECTED:'+','.join(ips))
        return ips

    def _validate_plan(self,plan):
        if plan.get('action')!='ALLOW':raise RuntimeError('PLAN_NOT_ALLOWED')
        if plan.get('read_only_candidate') is not True:raise RuntimeError('PLAN_NOT_READ_ONLY')
        method=str(plan.get('method','')).upper()
        if method not in self.ALLOWED_METHODS:raise RuntimeError('METHOD_NOT_READ_ONLY:'+method)
        # The canonical contract planner itself never performs network I/O.
        if plan.get('network_execute') is not False:raise RuntimeError('PLAN_NETWORK_BOUNDARY_CORRUPTED')
        path=str(plan.get('path',''))
        if not path.startswith('/') or path.startswith('//'):raise RuntimeError('UNSAFE_CONTRACT_PATH')
        return method,path

    def execute(self,plan,base_url,query=None,headers=None):
        method,path=self._validate_plan(plan)
        b=urllib.parse.urlsplit(str(base_url))
        if b.scheme.lower()!='https':raise RuntimeError('HTTPS_REQUIRED')
        if b.username or b.password or b.query or b.fragment:raise RuntimeError('UNSAFE_BASE_URL')
        host=(b.hostname or '').lower().strip('.')
        if host not in self.allowed_hosts:raise RuntimeError('HOST_NOT_ALLOWLISTED:'+host)
        ips=self._public_host(host)
        port=b.port or 443
        if port!=443:raise RuntimeError('NONSTANDARD_PORT_REJECTED')

        required=plan.get('required_slots',{}).get('query',[]) or []
        required_names={str(x.get('name',x)) if isinstance(x,dict) else str(x) for x in required}
        q={str(k):str(v) for k,v in (query or {}).items()}
        if set(q)-required_names:raise RuntimeError('UNDECLARED_QUERY_SLOT')
        missing=required_names-set(q)
        if missing:raise RuntimeError('MISSING_QUERY_SLOT:'+','.join(sorted(missing)))

        safe_headers={'User-Agent':'YADO-G2-ReadOnlyExecutor/1','Accept':'application/json, text/plain;q=0.9'}
        for k,v in (headers or {}).items():
            lk=str(k).lower().strip()
            if lk in self.FORBIDDEN_HEADERS:raise RuntimeError('CREDENTIAL_HEADER_REJECTED:'+lk)
            if lk not in {'accept','user-agent'}:raise RuntimeError('HEADER_NOT_ALLOWLISTED:'+lk)
            safe_headers[str(k)]=str(v)

        base=urllib.parse.urlunsplit(('https',host,path,'',''))
        url=base+('?' + urllib.parse.urlencode(q) if q else '')
        req=urllib.request.Request(url,headers=safe_headers,method=method)
        try:
            with self.opener.open(req,timeout=self.timeout) as resp:
                status=int(resp.status)
                final=urllib.parse.urlsplit(resp.geturl())
                if (final.hostname or '').lower().strip('.')!=host:raise RuntimeError('REDIRECT_HOST_CHANGE')
                if status<200 or status>=300:raise RuntimeError('NON_SUCCESS_STATUS:'+str(status))
                body=resp.read(self.max_bytes+1) if method!='HEAD' else b''
                if len(body)>self.max_bytes:raise RuntimeError('RESPONSE_TOO_LARGE')
                ctype=(resp.headers.get('Content-Type') or '').split(';',1)[0].strip().lower()
                if body and ctype not in {'application/json','text/plain','application/problem+json'} and not ctype.endswith('+json'):
                    raise RuntimeError('CONTENT_TYPE_REJECTED:'+ctype)
                meta={
                  'schema':'yado.g2.openapi_readonly_execution.v1',
                  'capability_id':self.COMPONENT_ID,
                  'contract_id':plan.get('contract_id'),
                  'method':method,'url':url,'host':host,'resolved_ips':ips,
                  'status':status,'content_type':ctype,'response_bytes':len(body),
                  'body_sha256':hashlib.sha256(body).hexdigest(),
                  'network_executed':True,'read_only_enforced':True,
                  'redirects_followed':False,'credentials_used':False,
                }
                meta['execution_digest']=_digest(meta)
                if body:
                    meta['body_text']=body.decode('utf-8','replace')
                return meta
        except urllib.error.HTTPError as e:
            if 300<=int(e.code)<400:raise RuntimeError('REDIRECT_REJECTED:'+str(e.code)) from e
            raise RuntimeError('HTTP_ERROR:'+str(e.code)) from e
        except urllib.error.URLError as e:
            raise RuntimeError('NETWORK_ERROR:'+str(e.reason)) from e

    @classmethod
    def component(cls):
        x={
          'schema':'yado.g2.openapi_readonly_executor.v1','component_id':cls.COMPONENT_ID,
          'methods':['GET','HEAD'],'https_only':True,'explicit_host_allowlist':True,
          'public_ip_resolution_required':True,'redirects_followed':False,
          'credentials_allowed':False,'max_response_bytes':cls.DEFAULT_MAX_BYTES,
          'timeout_seconds':cls.DEFAULT_TIMEOUT,'architecture_mutation':False,'canonical_active':False,
          'semantic_boundary':'BOUNDED REAL NETWORK EXECUTION FOR PRE-APPROVED READ-ONLY OPENAPI CONTRACT PLANS ONLY.'
        }
        x['component_digest']=_digest(x);return x

__all__=['G2OpenAPIReadOnlyExecutorV1']
