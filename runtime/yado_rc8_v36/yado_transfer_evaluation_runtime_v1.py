from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Iterable, Mapping
import hashlib,json

NATIVE_PROVENANCE={
 'status':'NATIVE_BOUNDED_TRANSFER_EVALUATION_RUNTIME',
 'source':'ACTIVE_YADO_CONTRACTS_PLUS_CONTROLLED_STREAM_EVALUATION_PRINCIPLES',
 'principles':['CONTROLLED_REUSABLE_STREAMS','FORWARD_TRANSFER','NEGATIVE_TRANSFER_RATE','FORGETTING','HELDOUT_GAIN','FAIL_CLOSED_GENERALIZATION_CLAIM'],
 'external_code_copied_verbatim':False,
 'foundation_weights_modified':False,
}

def _canonical(x:Any)->str:return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False)
def _digest(x:Any)->str:return hashlib.sha256(_canonical(x).encode()).hexdigest()
def _mean(xs):return sum(xs)/len(xs) if xs else 0.0

@dataclass(frozen=True)
class TransferEvaluationCase:
    case_id:str
    relation:str  # REUSABLE / UNRELATED / HELDOUT
    baseline_score:float
    adapted_score:float
    prior_retained_before:float=1.0
    prior_retained_after:float=1.0
    metadata:Mapping[str,Any]|None=None
    def canonical(self):
        d=asdict(self);d['metadata']=dict(sorted((self.metadata or {}).items()));return d

class TransferEvaluationRuntime:
    def __init__(self, *, min_reusable_gain:float=.05, min_heldout_gain:float=.02, max_unrelated_drop:float=.02, max_negative_transfer_rate:float=.10, max_forgetting:float=.03):
        self.min_reusable_gain=float(min_reusable_gain);self.min_heldout_gain=float(min_heldout_gain);self.max_unrelated_drop=float(max_unrelated_drop);self.max_negative_transfer_rate=float(max_negative_transfer_rate);self.max_forgetting=float(max_forgetting)

    def evaluate(self,cases:Iterable[TransferEvaluationCase])->dict[str,Any]:
        xs=list(cases)
        by={k:[c for c in xs if str(c.relation).upper()==k] for k in ('REUSABLE','UNRELATED','HELDOUT')}
        gains={k:[float(c.adapted_score)-float(c.baseline_score) for c in v] for k,v in by.items()}
        neg=[c for c in xs if float(c.adapted_score)+1e-12<float(c.baseline_score)]
        forgetting=[max(0.0,float(c.prior_retained_before)-float(c.prior_retained_after)) for c in xs]
        metrics={
          'reusable_gain':_mean(gains['REUSABLE']),
          'unrelated_gain':_mean(gains['UNRELATED']),
          'heldout_gain':_mean(gains['HELDOUT']),
          'negative_transfer_rate':len(neg)/len(xs) if xs else 0.0,
          'mean_forgetting':_mean(forgetting),
          'case_count':len(xs),
          'reusable_cases':len(by['REUSABLE']),'unrelated_cases':len(by['UNRELATED']),'heldout_cases':len(by['HELDOUT']),
        }
        gates={
          'reusable_gain':metrics['reusable_gain']>=self.min_reusable_gain,
          'heldout_gain':metrics['heldout_gain']>=self.min_heldout_gain,
          'unrelated_harmlessness':metrics['unrelated_gain']>=-self.max_unrelated_drop,
          'negative_transfer':metrics['negative_transfer_rate']<=self.max_negative_transfer_rate,
          'forgetting':metrics['mean_forgetting']<=self.max_forgetting,
          'coverage':all(len(by[k])>0 for k in by),
        }
        passed=all(gates.values())
        return {
          'status':'PASS_BOUNDED_CONTROLLED_TRANSFER' if passed else 'WITHHOLD_TRANSFER_CLAIM',
          'pass':passed,'metrics':metrics,'gates':gates,
          'failed_gates':sorted(k for k,v in gates.items() if not v),
          'general_open_ended_transfer_proven':False,
          'evidence_digest':_digest([c.canonical() for c in sorted(xs,key=lambda x:x.case_id)]),
        }

__all__=['TransferEvaluationCase','TransferEvaluationRuntime','NATIVE_PROVENANCE']
