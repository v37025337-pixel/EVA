from __future__ import annotations
from pathlib import Path
from itertools import combinations
import hashlib,json

RUNTIME=Path(__file__).resolve().parent
REPO=RUNTIME.parent
from yado_cognitive_growth_runtime_v1 import knn_predict

def _load(path:Path):return json.loads(path.read_text(encoding='utf-8'))
def _sha(path:Path):return hashlib.sha256(path.read_bytes()).hexdigest()

class CanonicalHighScaleBindingRuntimeV5:
    """Binding adapter whose route semantics are selected by the G2 V5 repair."""
    def __init__(self,binding:dict|None=None,repo_root:Path|None=None):
        self.repo=Path(repo_root or REPO)
        self.binding=dict(binding or _load(self.repo/'canonical/yado-native-selector-canonical-binding-v5.json'))
        for rel,expected in self.binding['artifact_sha256'].items():
            p=self.repo/rel
            if not p.exists():raise RuntimeError('BOUND_ARTIFACT_MISSING:'+rel)
            if _sha(p)!=expected:raise RuntimeError('BOUND_ARTIFACT_DIGEST_MISMATCH:'+rel)
        self.parent=_load(self.repo/self.binding['branch_artifacts']['parent_v2'])
        self.v4=_load(self.repo/self.binding['branch_artifacts']['high_scale_v4'])
        self.corpus=_load(self.repo/self.binding['branch_artifacts']['corpus'])
        if self.parent.get('state')!='SHADOW_SUPPORTED':raise RuntimeError('PARENT_V2_NOT_SUPPORTED')
        if self.v4.get('state')!='SHADOW_SUPPORTED' or self.v4.get('selected_skill_id')!='HIGH_ONLY_TRIPLE_KNN_V4':
            raise RuntimeError('V4_SELECTION_DRIFT')
        self.activation_min_size=int(self.v4['selected_spec']['activation_min_size'])
        self.route_strategy=str(self.binding['route_semantics']['selected_strategy'])
        self.normalization_denominator=float(self.binding['route_semantics'].get('normalization_denominator',3.0))
        self.parent_model=self.parent['selected_model'];self.v4_model=self.v4['selected_model']
        self.source_ids=sorted(str(x['id']) for x in self.corpus['source_digests'])
        self.source_pairs=list(combinations(self.source_ids,2));self.source_triples=list(combinations(self.source_ids,3))

    def __enter__(self):return self
    def __exit__(self,*args):return False

    def cardinality(self,case:dict)->int:
        if self.route_strategy=='KEY_CARDINALITY':
            key=str(case.get('key',''))
            return 0 if not key else len([x for x in key.split('|') if x])
        if self.route_strategy=='INVERT_NORMALIZED_SOURCE_COUNT':
            return int(round(float(case['x']['source_count'])*self.normalization_denominator))
        raise RuntimeError('UNKNOWN_ROUTE_STRATEGY:'+self.route_strategy)

    def route(self,case:dict):
        return 'V4_HIGH' if self.cardinality(case)>=self.activation_min_size else 'V2_PARENT'

    def _augment(self,key,x,order):
        z=dict(x);present=set(str(key).split('|'))
        for sid in self.source_ids:z['src::'+sid]=1.0 if sid in present else 0.0
        if order>=2:
            for a,b in self.source_pairs:z['srcpair::'+a+'&&'+b]=1.0 if a in present and b in present else 0.0
        if order>=3:
            for a,b,c in self.source_triples:z['srctri::'+a+'&&'+b+'&&'+c]=1.0 if a in present and b in present and c in present else 0.0
        return z

    def predict(self,case):
        if self.route(case)=='V2_PARENT':return knn_predict(self.parent_model,self._augment(case['key'],case['x'],2))
        return knn_predict(self.v4_model,self._augment(case['key'],case['x'],3))

    def snapshot(self):
        return {'schema':'yado.g2.canonical_high_scale_binding_runtime.v5','route_strategy':self.route_strategy,
                'activation_min_size':self.activation_min_size,'binding_digest':self.binding.get('binding_digest'),
                'v4_candidate_digest':self.v4.get('candidate_digest')}
