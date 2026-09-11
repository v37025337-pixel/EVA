from __future__ import annotations
import json,time
from pathlib import Path
from yado_g2_openapi_readonly_executor_v1 import G2OpenAPIReadOnlyExecutorV1

CANDIDATES=[
 ('Google','dns.google','https://dns.google','/resolve',{'name':'example.com','type':'A'}),
 ('Cloudflare','cloudflare-dns.com','https://cloudflare-dns.com','/dns-query',{'name':'example.com','type':'A'}),
]

def plan(host,path):
 return {'action':'ALLOW','read_only_candidate':True,'method':'GET','network_execute':False,'path':path,'contract_id':'YADO-PUBLIC-DNS-RESEARCH-V1-'+host,'required_slots':{'query':[{'name':'name'},{'name':'type'}]}}

def main():
 out=[]
 for provider,host,base,path,q in CANDIDATES:
  t=time.monotonic()
  try:
   ex=G2OpenAPIReadOnlyExecutorV1([host],max_bytes=262144,timeout=10)
   r=ex.execute(plan(host,path),base,query=q,headers={'Accept':'application/dns-json, application/json'})
   body=r.pop('body_text','')
   parsed=json.loads(body) if body else {}
   out.append({'provider':provider,'host':host,'reachable':True,'latency_ms':round((time.monotonic()-t)*1000,2),'dns_status':parsed.get('Status'),'answer_count':len(parsed.get('Answer',[]) or []),'execution':r})
  except Exception as e:
   out.append({'provider':provider,'host':host,'reachable':False,'latency_ms':round((time.monotonic()-t)*1000,2),'error':type(e).__name__+':'+str(e)})
 report={'schema':'yado.public_dns_research.v1','status':'PASS_READONLY_RESEARCH' if any(x['reachable'] for x in out) else 'WITHHOLD_NO_REACHABLE_DOH','purpose':'Research public DNS-over-HTTPS endpoints; DNS is name resolution, not compute/hosting.','credentials_used':False,'mutation':False,'results':out}
 p=Path('candidates/network/yado-public-dns-research-v1.json');p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
 print(json.dumps(report,indent=2,sort_keys=True))
if __name__=='__main__':main()
