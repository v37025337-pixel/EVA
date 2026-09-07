from __future__ import annotations
from pathlib import Path
import hashlib,json,math,random,socket,statistics,struct,time

REPO=Path(__file__).resolve().parents[1]
TASK=REPO/'resources/yado-public-dns-direct-probe-task-v1.json'
OUT=REPO/'candidates/kernel-self-generated/g2-public-dns-direct-probe-v1.json'
EXP=REPO/'experience/yado-public-dns-direct-probe-v1.json'

def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o): return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))

QTYPE={'A':1,'TXT':16}
QCLASS={'IN':1,'CH':3}

def enc_name(name:str)->bytes:
    out=b''
    for label in name.rstrip('.').split('.'):
        b=label.encode('ascii')
        if len(b)>63: raise ValueError('LABEL_TOO_LONG')
        out+=bytes([len(b)])+b
    return out+b'\x00'

def build_query(qname,qtype='A',qclass='IN',rd=True):
    qid=random.SystemRandom().randrange(0,65536)
    flags=0x0100 if rd else 0
    header=struct.pack('!HHHHHH',qid,flags,1,0,0,0)
    q=enc_name(qname)+struct.pack('!HH',QTYPE[qtype],QCLASS[qclass])
    return qid,header+q

def skip_name(buf,off):
    jumped=False
    seen=0
    while True:
        if off>=len(buf): raise ValueError('NAME_OOB')
        n=buf[off]
        if n==0:
            return off+1
        if n & 0xC0 == 0xC0:
            if off+1>=len(buf): raise ValueError('PTR_OOB')
            return off+2
        off+=1+n
        seen+=1
        if seen>128: raise ValueError('NAME_LOOP')

def parse_dns(buf,expected_id):
    if len(buf)<12: raise ValueError('SHORT_DNS')
    qid,flags,qd,an,ns,ar=struct.unpack('!HHHHHH',buf[:12])
    if qid!=expected_id: raise ValueError('ID_MISMATCH')
    off=12
    for _ in range(qd):
        off=skip_name(buf,off)
        if off+4>len(buf): raise ValueError('QUESTION_OOB')
        off+=4
    answers=[]
    for section,count in [('answer',an),('authority',ns),('additional',ar)]:
        for _ in range(count):
            off=skip_name(buf,off)
            if off+10>len(buf): raise ValueError('RR_OOB')
            typ,cls,ttl,rdlen=struct.unpack('!HHIH',buf[off:off+10]); off+=10
            if off+rdlen>len(buf): raise ValueError('RDATA_OOB')
            rdata=buf[off:off+rdlen]; off+=rdlen
            row={'section':section,'type':typ,'class':cls,'ttl':ttl,'rdlen':rdlen}
            if typ==1 and rdlen==4:
                row['a']='.'.join(str(x) for x in rdata)
            elif typ==16 and rdlen>0:
                parts=[]; p=0
                try:
                    while p<rdlen:
                        ln=rdata[p]; p+=1
                        parts.append(rdata[p:p+ln].decode('utf-8','replace')); p+=ln
                    row['txt']=''.join(parts)
                except Exception:
                    pass
            answers.append(row)
    return {
      'rcode':flags & 0xF,
      'qr':bool(flags & 0x8000),
      'aa':bool(flags & 0x0400),
      'tc':bool(flags & 0x0200),
      'rd':bool(flags & 0x0100),
      'ra':bool(flags & 0x0080),
      'ad':bool(flags & 0x0020),
      'cd':bool(flags & 0x0010),
      'question_count':qd,'answer_count':an,'authority_count':ns,'additional_count':ar,
      'answers':answers
    }

def udp_query(ip,qname,qtype='A',qclass='IN',timeout=2.5,rd=True):
    qid,msg=build_query(qname,qtype,qclass,rd)
    s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); s.settimeout(timeout)
    t=time.perf_counter()
    try:
        s.sendto(msg,(ip,53))
        data,addr=s.recvfrom(4096)
        ms=(time.perf_counter()-t)*1000
        parsed=parse_dns(data,qid)
        return {'ok':True,'transport':'UDP','peer':addr[0],'latency_ms':round(ms,3),**parsed}
    except Exception as e:
        return {'ok':False,'transport':'UDP','error':type(e).__name__+':'+str(e)[:180]}
    finally:
        s.close()

def recv_exact(s,n):
    parts=[]; got=0
    while got<n:
        b=s.recv(n-got)
        if not b: raise ConnectionError('EOF')
        parts.append(b); got+=len(b)
    return b''.join(parts)

def tcp_query(ip,qname,qtype='A',qclass='IN',timeout=3.5,rd=True):
    qid,msg=build_query(qname,qtype,qclass,rd)
    s=socket.socket(socket.AF_INET,socket.SOCK_STREAM); s.settimeout(timeout)
    t=time.perf_counter()
    try:
        s.connect((ip,53))
        s.sendall(struct.pack('!H',len(msg))+msg)
        ln=struct.unpack('!H',recv_exact(s,2))[0]
        data=recv_exact(s,ln)
        ms=(time.perf_counter()-t)*1000
        parsed=parse_dns(data,qid)
        return {'ok':True,'transport':'TCP','latency_ms':round(ms,3),**parsed}
    except Exception as e:
        return {'ok':False,'transport':'TCP','error':type(e).__name__+':'+str(e)[:180]}
    finally:
        s.close()

def summarize_ip(ip):
    repeated=[udp_query(ip,'example.com','A','IN') for _ in range(3)]
    tcp=tcp_query(ip,'example.com','A','IN')
    dnssec=udp_query(ip,'dnssec-failed.org','A','IN')
    nx=udp_query(ip,'yado-direct-probe.invalid','A','IN')
    chaos=udp_query(ip,'id.server','TXT','CH',rd=False)
    good=[x['latency_ms'] for x in repeated if x.get('ok')]
    return {
      'ip':ip,
      'udp_example_repeats':repeated,
      'udp_success_count':sum(bool(x.get('ok')) for x in repeated),
      'udp_latency_ms':{
        'samples':good,
        'median':round(statistics.median(good),3) if good else None,
        'min':round(min(good),3) if good else None,
        'max':round(max(good),3) if good else None
      },
      'tcp_example':tcp,
      'dnssec_failed_org':dnssec,
      'nxdomain_probe':nx,
      'chaos_id_server':chaos,
      'recursive_available_observed':any(x.get('ok') and x.get('ra') for x in repeated),
      'dnssec_validation_consistent':bool(dnssec.get('ok') and dnssec.get('rcode')==2),
      'nxdomain_behavior_observed':bool(nx.get('ok') and nx.get('rcode')==3),
      'chaos_identity_txt':[a.get('txt') for a in chaos.get('answers',[]) if a.get('txt')] if chaos.get('ok') else []
    }

task=load(TASK)
providers=[]
for p in task['providers']:
    rows=[summarize_ip(ip) for ip in p['ipv4']]
    medians=[x['udp_latency_ms']['median'] for x in rows if x['udp_latency_ms']['median'] is not None]
    providers.append({
      'provider_id':p['id'],'provider':p['name'],'addresses':rows,
      'provider_udp_reachable':any(x['udp_success_count']>0 for x in rows),
      'provider_tcp_reachable':any(x['tcp_example'].get('ok') for x in rows),
      'provider_dnssec_validation_consistent':any(x['dnssec_validation_consistent'] for x in rows),
      'provider_nxdomain_observed':any(x['nxdomain_behavior_observed'] for x in rows),
      'provider_runner_median_ms':round(statistics.median(medians),3) if medians else None
    })

provider_udp=sum(x['provider_udp_reachable'] for x in providers)
provider_tcp=sum(x['provider_tcp_reachable'] for x in providers)
dnssec_count=sum(x['provider_dnssec_validation_consistent'] for x in providers)
nxdomain_count=sum(x['provider_nxdomain_observed'] for x in providers)
address_rows=[a for p in providers for a in p['addresses']]
address_udp=sum(x['udp_success_count']>0 for x in address_rows)

ranked=[{'provider':p['provider'],'provider_id':p['provider_id'],'runner_median_ms':p['provider_runner_median_ms']} for p in providers if p['provider_runner_median_ms'] is not None]
ranked.sort(key=lambda x:x['runner_median_ms'])

checks={
  'at_least_four_of_five_providers_udp_reachable':provider_udp>=4,
  'at_least_four_of_five_providers_tcp_reachable':provider_tcp>=4,
  'at_least_eight_of_ten_addresses_udp_reachable':address_udp>=8,
  'at_least_four_dnssec_behaviors_determined':dnssec_count>=4,
  'at_least_four_nxdomain_behaviors_observed':nxdomain_count>=4,
  'no_system_resolver_reconfiguration':task['constraints']['no_system_resolver_reconfiguration'] is True,
  'only_port_53_declared':task['constraints']['allowed_ports']==[53],
  'canonical_mutation_false':task['constraints']['canonical_mutation'] is False,
  'automatic_promotion_false':task['constraints']['automatic_promotion'] is False,
  'g3_false':task['constraints']['g3_genesis'] is False
}
status='PASS_SHADOW_G2_PUBLIC_DNS_DIRECT_PROBE_V1' if all(checks.values()) else 'WITHHOLD_G2_PUBLIC_DNS_DIRECT_PROBE_V1'

experience={
  'schema':'yado.g2.public_dns_direct_probe.experience.v1',
  'status':status,'task_id':task['task_id'],
  'providers':providers,
  'aggregate':{
    'providers_udp_reachable':provider_udp,'providers_tcp_reachable':provider_tcp,
    'addresses_udp_reachable':address_udp,'dnssec_validation_consistent_providers':dnssec_count,
    'nxdomain_observed_providers':nxdomain_count,'runner_latency_ranking':ranked
  },
  'checks':checks,
  'causal_lessons':[
    {
      'id':'DNS-DIRECT-001',
      'rule':'DIRECT_RESOLVER_USE_MUST_BE_MEASURED_PER_TARGET_AND_PER_TRANSPORT',
      'evidence':'UDP_AND_TCP_PROBES_TO_EXACT_SCREENSHOT_IPS'
    },
    {
      'id':'DNS-DIRECT-002',
      'rule':'RUNNER_RELATIVE_LATENCY_IS_NOT_USER_RELATIVE_LATENCY',
      'evidence':'MEASUREMENTS_ORIGINATE_FROM_GITHUB_HOSTED_RUNNER'
    },
    {
      'id':'DNS-DIRECT-003',
      'rule':'DNSSEC_VALIDATION_CAN_BE_OBSERVED_WITH_A_KNOWN_BOGUS_DOMAIN_BUT_NOT_INFERRED_FROM_MARKETING',
      'evidence':'DNSSEC_FAILED_ORG_RESPONSE_CODE'
    },
    {
      'id':'DNS-DIRECT-004',
      'rule':'OPTIONAL_CHAOS_IDENTITY_NONRESPONSE_DOES_NOT_INVALIDATE_RESOLVER_FUNCTION',
      'evidence':'CHAOS_CLASS_ID_SERVER_IS_OPTIONAL'
    },
    {
      'id':'DNS-DIRECT-005',
      'rule':'NEXTDNS_RAW_ANYCAST_REACHABILITY_DOES_NOT_PROVE_PROFILE_SPECIFIC_FILTERING',
      'evidence':'DIRECT_IP_PROBE_HAS_NO_ACCOUNT_CONFIGURATION_CONTEXT'
    }
  ],
  'application_rule':'FUTURE_DNS_SELECTION_MUST_USE_DIRECT_MEASUREMENT_FOR_THE_CURRENT_EXECUTION_LOCATION_AND_MUST_KEEP_FEATURE_VARIANT_AND_PROFILE_CONTEXT_SEPARATE',
  'canonical_mutation':False,'automatic_promotion':False,'g3_genesis':False,
  'semantic_boundary':'DIRECT PUBLIC DNS QUERIES FROM A GITHUB-HOSTED RUNNER TO THE SCREENSHOT IP ADDRESSES ON PORT 53 ONLY. THIS IS NOT A PORT SCAN AND DOES NOT CLAIM USER-LOCAL PERFORMANCE.'
}
experience['experience_digest']=digest(experience)
report={
  'schema':'yado.g2.public_dns_direct_probe.v1','status':status,'task_id':task['task_id'],
  'aggregate':experience['aggregate'],'providers':providers,'checks':checks,
  'experience_digest':experience['experience_digest'],
  'next_required_capability':'APPLY_DIRECT_DNS_OBSERVATIONS_TO_CAUSAL_MEMORY' if status.startswith('PASS') else 'PUBLIC_DNS_DIRECT_PROBE_REPAIR_V2',
  'canonical_mutation':False,'automatic_canonical_promotion':False,'generation_transition':False,'g3_genesis_performed':False,
  'semantic_boundary':experience['semantic_boundary']
}
report['receipt_sha256']=digest(report)
EXP.parent.mkdir(parents=True,exist_ok=True); OUT.parent.mkdir(parents=True,exist_ok=True)
EXP.write_text(json.dumps(experience,indent=2,sort_keys=True)+'\n',encoding='utf-8')
OUT.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n',encoding='utf-8')
print(json.dumps({
  'status':status,'aggregate':report['aggregate'],'checks':checks,
  'next_required_capability':report['next_required_capability'],
  'experience_digest':report['experience_digest']
},indent=2,sort_keys=True))
if not status.startswith('PASS_'): raise SystemExit(2)
