from __future__ import annotations
from collections import Counter,defaultdict
from dataclasses import dataclass
import math,re,hashlib,json

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()

def words(text):
    return re.findall(r"[a-zA-Z0-9_]+",str(text).lower())

def char_ngrams(text,n=4):
    s=" ".join(words(text))
    if len(s)<n:return [s] if s else []
    return [s[i:i+n] for i in range(len(s)-n+1)]

@dataclass
class RawTaskRepresentationSpecV1:
    family:str
    labels:list[str]
    payload:dict

    def predict(self,text):
        if self.family=="WORD_NB":
            toks=words(text)
            best=[]
            for label in self.labels:
                pri=self.payload["label_docs"][label]
                total=self.payload["label_totals"][label]
                vocab=self.payload["vocab_size"]
                counts=self.payload["counts"][label]
                score=math.log((pri+1)/(self.payload["doc_count"]+len(self.labels)))
                for t in toks:
                    score+=math.log((counts.get(t,0)+1)/(total+vocab))
                best.append((score,label))
            best.sort(key=lambda x:(-x[0],x[1]));return best[0][1]
        if self.family=="CHAR_NGRAM_CENTROID":
            feats=Counter(char_ngrams(text,self.payload["n"]))
            norm=math.sqrt(sum(v*v for v in feats.values())) or 1.0
            best=[]
            for label in self.labels:
                c=self.payload["centroids"][label]
                dot=sum(v*c.get(k,0.0) for k,v in feats.items())
                score=dot/norm
                best.append((score,label))
            best.sort(key=lambda x:(-x[0],x[1]));return best[0][1]
        if self.family=="WORD_OVERLAP_CENTROID":
            feats=set(words(text));best=[]
            for label in self.labels:
                c=set(self.payload["tokens"][label])
                score=len(feats&c)/max(1,len(feats|c))
                best.append((score,label))
            best.sort(key=lambda x:(-x[0],x[1]));return best[0][1]
        raise ValueError("UNKNOWN_FAMILY")

class RawTaskRepresentationLearnerV1:
    FAMILIES=("WORD_NB","CHAR_NGRAM_CENTROID","WORD_OVERLAP_CENTROID")

    @staticmethod
    def fit(rows,family):
        labels=sorted({y for _,y in rows})
        if family=="WORD_NB":
            counts={l:Counter() for l in labels};docs=Counter();tot=Counter();vocab=set()
            for text,y in rows:
                ts=words(text);counts[y].update(ts);docs[y]+=1;tot[y]+=len(ts);vocab.update(ts)
            return RawTaskRepresentationSpecV1(family,labels,{
              "counts":{l:dict(counts[l]) for l in labels},"label_docs":dict(docs),
              "label_totals":dict(tot),"vocab_size":max(1,len(vocab)),"doc_count":len(rows)
            })
        if family=="CHAR_NGRAM_CENTROID":
            n=4;sums={l:Counter() for l in labels};cnt=Counter()
            for text,y in rows:
                f=Counter(char_ngrams(text,n));norm=math.sqrt(sum(v*v for v in f.values())) or 1
                for k,v in f.items():sums[y][k]+=v/norm
                cnt[y]+=1
            cent={}
            for l in labels:
                c={k:v/max(1,cnt[l]) for k,v in sums[l].items()}
                norm=math.sqrt(sum(v*v for v in c.values())) or 1
                cent[l]={k:v/norm for k,v in c.items()}
            return RawTaskRepresentationSpecV1(family,labels,{"n":n,"centroids":cent})
        if family=="WORD_OVERLAP_CENTROID":
            tok={l:Counter() for l in labels}
            for text,y in rows:tok[y].update(set(words(text)))
            return RawTaskRepresentationSpecV1(family,labels,{"tokens":{l:[k for k,v in tok[l].items() if v>=1] for l in labels}})
        raise ValueError("UNKNOWN_FAMILY")

    @classmethod
    def select(cls,train,validation):
        results=[]
        for fam in cls.FAMILIES:
            spec=cls.fit(train,fam)
            acc=sum(spec.predict(x)==y for x,y in validation)/max(1,len(validation))
            results.append({"family":fam,"validation":acc,"spec":spec})
        results.sort(key=lambda x:(-x["validation"],x["family"]))
        return results[0],results
