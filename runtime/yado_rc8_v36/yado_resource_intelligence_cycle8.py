from __future__ import annotations
import re, math, json, hashlib, itertools
from collections import defaultdict
from pathlib import Path

ROOT=Path('/mnt/data/yado_continue')
# Source-derived records from Furthir/awesome-useful-projects.
BASE=[('searxng/searxng','Internet metasearch engine'),('jlevy/the-art-of-command-line','Master the command line'),('chubin/cheat.sh','Cheatsheet for commands'),('orhun/binsider','Binary analyzer'),('GyulyVGC/sniffnet','Cross-platform network traffic monitor'),('rclone/rclone','rsync for cloud storage'),('nextcloud/server','Self-hosted cloud storage service'),('CorentinTh/it-tools','Collection of handy online tools'),('rustdesk/rustdesk','Remote desktop application'),('lissy93/awesome-privacy','List of privacy/security-focused software and services'),('wdhdev/free-for-life','Large collection of services that are free'),('DevToys-app/DevToys','Cross-platform bundle of tools for doing quick tasks')]
T1=[('BurntSushi/ripgrep','Fast line-oriented search tool'),('aristocratos/btop','System resource monitoring'),('sharkdp/hyperfine','Command line benchmarking tool'),('bleachbit/bleachbit','System cleaner for Windows and Linux'),('peazip/PeaZip','Cross-platform file and archive manager')]
T2=[('sharkdp/bat','Better cat'),('ajeetdsouza/zoxide','Smarter directory navigation based on z'),('fastfetch-cli/fastfetch','neofetch but fast, maintained, and more customizable'),('tmux/tmux','Terminal multiplexer'),('ActivityWatch/activitywatch','Automated activity time tracker'),('localsend/localsend','Cross-platform alternative to AirDrop'),('organicmaps/organicmaps','Offline maps app using OpenStreetMap'),('pbatard/rufus','USB formatting utility')]
T3=[('Slackadays/Clipboard','Smart clipboard manager'),('pacstall/pacstall','AUR-inspired package manager for Ubuntu'),('charmbracelet/freeze','Screenshot your terminal'),('qarmin/czkawka','Remove unnecessary files from your computer'),('AdnanHodzic/auto-cpufreq','Automatic CPU power optimizer'),('edisionnano/QDiskInfo','Disk drive analysis tool'),('gdzx/audiosource','Use an Android device as a USB microphone'),('wolfree','WolframAlpha but free')]
FRESH_DOCS=[('LizardByte/Sunshine','Self-hosted game stream host for Moonlight'),('pavlobu/deskreen','Turn web browser into a secondary screen'),('Jacalz/rymdport','Cross-platform file sharing between devices'),('upscayl/upscayl','Cross-platform AI image upscaler'),('H-M-H/Weylus','Use tablet as graphic tablet/touch screen'),('AntiMicroX/antimicrox','Map keyboard and mouse to gamepad controls'),('starship/starship','Custom shell prompt'),('HandBrake/HandBrake','Video transcoder')]

TR0=[('backup files to cloud sync between providers','rclone/rclone'),('inspect binary executable format analyze binary','orhun/binsider'),('monitor network traffic connections packets','GyulyVGC/sniffnet'),('learn command line shell terminal cli','jlevy/the-art-of-command-line'),('privacy security software list alternatives','lissy93/awesome-privacy'),('self hosted cloud storage server','nextcloud/server'),('internet research metasearch search engine external evidence','searxng/searxng'),('web meta search for independent research','searxng/searxng'),('quick command cheatsheet examples reference','chubin/cheat.sh'),('remote desktop control another computer','rustdesk/rustdesk'),('collection of free services','wdhdev/free-for-life'),('online toolbox utilities','CorentinTh/it-tools'),('meta search across internet engines','searxng/searxng'),('terminal command reference examples','chubin/cheat.sh'),('control another pc with remote desktop','rustdesk/rustdesk'),('directory of services available free','wdhdev/free-for-life'),('handy online utilities collection','CorentinTh/it-tools'),('cross platform utility bundle for quick tasks','DevToys-app/DevToys'),('fast unix command examples lookup','chubin/cheat.sh'),('learn bash shell command line fundamentals','jlevy/the-art-of-command-line'),('private web metasearch for research','searxng/searxng'),('transfer files among cloud storage providers','rclone/rclone'),('analyze executable binary internals','orhun/binsider'),('observe network traffic and connections','GyulyVGC/sniffnet'),('host my own cloud file storage','nextcloud/server'),('quick browser based utility collection','CorentinTh/it-tools'),('remote access another desktop computer','rustdesk/rustdesk'),('catalog of privacy focused software services','lissy93/awesome-privacy'),('instant shell command usage examples','chubin/cheat.sh'),('become fluent with bash command line','jlevy/the-art-of-command-line'),('independent privacy metasearch web engine','searxng/searxng'),('copy and synchronize data across cloud remotes','rclone/rclone'),('inspect binary executable structure','orhun/binsider'),('monitor live network bandwidth connections','GyulyVGC/sniffnet'),('run a private self hosted file cloud','nextcloud/server'),('collection of small handy web utilities','CorentinTh/it-tools'),('connect remotely to another computer desktop','rustdesk/rustdesk'),('curated privacy and security software list','lissy93/awesome-privacy'),('directory of no cost online services','wdhdev/free-for-life'),('bundle for quick developer utility tasks','DevToys-app/DevToys')]
TR1=[('quick recursive text search through files','BurntSushi/ripgrep'),('watch cpu memory and system resources','aristocrates/btop'),('measure performance of command line programs','sharkdp/hyperfine'),('clean junk files on linux and windows','bleachbit/bleachbit'),('manage compressed archive files across platforms','peazip/PeaZip')]
# Correct typo in source target if present in older note.
TR1=[(q, 'aristocratos/btop' if e=='aristocrates/btop' else e) for q,e in TR1]
TR2=[('view a file like cat with nicer output','sharkdp/bat'),('jump to frequently used directories faster','ajeetdsouza/zoxide'),('fast customizable system information display','fastfetch-cli/fastfetch'),('multiplex several terminal sessions','tmux/tmux'),('automatically track time spent on computer activity','ActivityWatch/activitywatch'),('send files to another device like airdrop','localsend/localsend'),('use maps offline with openstreetmap data','organicmaps/organicmaps'),('format a usb drive utility','pbatard/rufus')]
TR3=[('manage clipboard contents smartly','Slackadays/Clipboard'),('install aur style packages on ubuntu','pacstall/pacstall'),('capture a screenshot of terminal output','charmbracelet/freeze'),('remove unnecessary duplicate or junk files','qarmin/czkawka'),('automatically optimize cpu power usage','AdnanHodzic/auto-cpufreq'),('analyze disk drive information','edisionnano/QDiskInfo'),('use android phone as usb microphone','gdzx/audiosource'),('free alternative to wolfram alpha','wolfree')]
TRAIN=TR0+TR1+TR2+TR3
FRESH=[('host games for streaming to moonlight','LizardByte/Sunshine'),('use browser as a second monitor screen','pavlobu/deskreen'),('share files between different devices','Jacalz/rymdport'),('upscale images using ai across platforms','upscayl/upscayl'),('turn tablet into touch screen graphics tablet','H-M-H/Weylus'),('map keyboard and mouse controls to a gamepad','AntiMicroX/antimicrox'),('customize my shell prompt','starship/starship'),('transcode video files','HandBrake/HandBrake')]

STOP=set('a an the and or of to for in on with from by is are be as at this that these those it its your you we our their app apps tool tools project projects software service services cross platform based using use useful open source'.split())

def tokenize(s:str,camel:bool):
    if camel:
        s=re.sub(r'(?<=[a-z0-9])(?=[A-Z])',' ',s)
    return [x for x in re.findall(r'[a-z0-9]+',s.lower()) if len(x)>1 and x not in STOP]

def grams_from_tokens(ts):
    s=' '.join(ts)
    return {s[i:i+3] for i in range(max(0,len(s)-2))}

def build_model(camel:bool):
    supported=BASE+T1+T2+T3
    all_docs=supported+FRESH_DOCS
    sset={r for r,_ in supported}
    desc={r:tokenize(d,camel) for r,d in all_docs}
    gr={r:grams_from_tokens(desc[r]) for r,_ in all_docs}
    pos=defaultdict(float); neg=defaultdict(float)
    for q,tgt in TRAIN:
        qs=set(tokenize(q,camel)); td=set(desc[tgt])
        for x in qs:
            for d in td: pos[(x,d)]+=1
            for r in sset:
                if r==tgt: continue
                for d in set(desc[r]): neg[(x,d)]+=1/(len(sset)-1)
    return supported,all_docs,sset,desc,gr,pos,neg

def run_candidate(camel:bool, gate_k:int, sem_weight:float):
    supported,all_docs,sset,desc,gr,pos,neg=build_model(camel)
    lex_weight=1-sem_weight
    def lexical(q,r):
        qt=tokenize(q,camel);qs=set(qt);ds=set(desc[r])
        token=len(qs&ds)/(len(qs) or 1)
        qg=grams_from_tokens(qt); tri=len(qg&gr[r])/(len(qg|gr[r]) or 1)
        return .5*(token+tri)
    def semantic(q,r):
        vals=[]
        for x in set(tokenize(q,camel)):
            best=0
            for d in set(desc[r]):
                p=pos[(x,d)];n=neg[(x,d)]
                if p: best=max(best,max(0,math.log((p+.5)/(n+.5))))
            vals.append(best)
        return sum(vals)/(len(vals) or 1)
    def rank(q):
        base=sorted(((lexical(q,r),r) for r,_ in all_docs),key=lambda z:(z[0],z[1]),reverse=True)
        gate=all(r in sset for _,r in base[:gate_k])
        if not gate:return base,False
        sr={r:semantic(q,r) for r in sset};mx=max(sr.values()) or 1
        rows=[]
        for b,r in base:
            if r in sset:rows.append((lex_weight*b+sem_weight*(sr[r]/mx),r))
            else:rows.append((b,r))
        return sorted(rows,key=lambda z:(z[0],z[1]),reverse=True),True
    def ev(cases):
        h=0;rr=0;details=[]
        for q,e in cases:
            rows,g=rank(q);ids=[r for _,r in rows];p=ids.index(e)+1;h+=p==1;rr+=1/p
            details.append({'query':q,'expected':e,'rank':p,'semantic_gate':g,'top3':[{'repo':r,'score':round(s,6)} for s,r in rows[:3]]})
        n=len(cases);return {'top1':h/n,'mrr':rr/n,'detail':details}
    return ev

def main():
    candidates=[]
    for camel in (False,True):
        for gate_k in (1,2,3):
            for sem_weight in (.25,.5,.75,1.0):
                ev=run_candidate(camel,gate_k,sem_weight)
                tr=ev(TRAIN)
                complexity=int(camel)+(gate_k>1)+1
                fit=tr['top1']+.20*tr['mrr']-.001*complexity
                candidates.append({'camel_split':camel,'gate_k':gate_k,'semantic_weight':sem_weight,'train_top1':tr['top1'],'train_mrr':tr['mrr'],'fitness':fit})
    candidates.sort(key=lambda c:(c['fitness'],-c['gate_k'],-c['semantic_weight'],not c['camel_split']),reverse=True)
    selected=candidates[0]
    frozen_payload={k:selected[k] for k in ('camel_split','gate_k','semantic_weight')}
    frozen_digest=hashlib.sha256(json.dumps(frozen_payload,sort_keys=True).encode()).hexdigest()
    ev=run_candidate(selected['camel_split'],selected['gate_k'],selected['semantic_weight'])
    fresh=ev(FRESH)
    # Ablation = remove char/semantic learned layers: token-only lexical on same frozen representation.
    # Implement separately for transparent causal comparison.
    supported=BASE+T1+T2+T3; all_docs=supported+FRESH_DOCS
    def token_only_eval(cases):
        camel=selected['camel_split'];desc={r:tokenize(d,camel) for r,d in all_docs}
        out=[];h=0;rr=0
        for q,e in cases:
            qs=set(tokenize(q,camel));rows=[]
            for r,_ in all_docs:
                ds=set(desc[r]);s=len(qs&ds)/(len(qs) or 1);rows.append((s,r))
            rows.sort(key=lambda z:(z[0],z[1]),reverse=True);ids=[r for _,r in rows];p=ids.index(e)+1;h+=p==1;rr+=1/p
            out.append({'query':q,'expected':e,'rank':p,'top3':[{'repo':r,'score':round(s,6)} for s,r in rows[:3]]})
        n=len(cases);return {'top1':h/n,'mrr':rr/n,'detail':out}
    ablation=token_only_eval(FRESH);restore=ev(FRESH)
    verdict='SHADOW_SUPPORTED_BOUNDED' if fresh['top1']==1.0 and restore['top1']==1.0 and fresh['top1']>ablation['top1'] else 'SHADOW_WITHHOLD'
    report={
      'schema':'yado.resource_intelligence.cycle8.v1','source':'github:Furthir/awesome-useful-projects',
      'developmental_training_cases':len(TRAIN),'supported_resources':len(BASE+T1+T2+T3),'fresh_unseen_resources':len(FRESH_DOCS),
      'candidate_configs_generated':len(candidates),'selected':{**selected,'frozen_before_fresh_blind':True,'frozen_digest':frozen_digest},
      'fresh_unseen_blind':fresh,'ablation_token_only':ablation,'restore':restore,'verdict':verdict,
      'provenance':{
        'task_specific_repo_rule_supplied':False,'candidate_config_generated_by_search':True,'fresh_blind_used_for_selection':False,
        'semantic_translation_learned_from_revealed_corrections':True,'support_boundary_active':True,'representation_candidates':['RAW_TOKENIZE','CAMEL_SPLIT_TOKENIZE'],
        'canonical_durable_head_modified':False,'shadow_only':True,
      },
      'claim_boundary':{
        'full_catalog_general_semantics_proven':False,'bounded_resource_selection_improved':fresh['top1']==1.0,
        'subjective_intelligence_or_consciousness_claimed':False,
      }
    }
    (ROOT/'yado_resource_intelligence_cycle8_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
