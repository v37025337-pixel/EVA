from __future__ import annotations
from pathlib import Path
from itertools import combinations
import hashlib,json

RUNTIME=Path(__file__).resolve().parent
REPO=RUNTIME.parent

from yado_cognitive_growth_runtime_v1 import knn_predict

def _load(path:Path):
    return json.loads(path.read_text(encoding='utf-8'))

def _sha(path:Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

class CanonicalHighScaleBindingRuntimeV4:
    """
    Binding-only runtime for the G2 high-scale V4 candidate.
    It does not learn or select a new threshold. The activation boundary is read
    from the already selected V4 candidate metadata.
    Below that boundary it preserves the V2 parent model; at/above it it executes
    the V4 kernel-selected triple-interaction KNN model.
    """
    def __init__(self,binding:dict|None=None,repo_root:Path|None=None):
        self.repo=Path(repo_root or REPO)
        self.binding=dict(binding or _load(self.repo/'canonical/yado-native-selector-canonical-binding-v4.json'))
        for rel,expected in self.binding['artifact_sha256'].items():
            p=self.repo/rel
            if not p.exists():raise RuntimeError('BOUND_ARTIFACT_MISSING:'+rel)
            actual=_sha(p)
            if actual!=expected:raise RuntimeError('BOUND_ARTIFACT_DIGEST_MISMATCH:'+rel)

        self.parent=_load(self.repo/self.binding['branch_artifacts']['parent_v2'])
        self.v4=_load(self.repo/self.binding['branch_artifacts']['high_scale_v4'])
        self.corpus=_load(self.repo/self.binding['branch_artifacts']['corpus'])
        if self.parent.get('state')!='SHADOW_SUPPORTED':raise RuntimeError('PARENT_V2_NOT_SUPPORTED')
        if self.v4.get('state')!='SHADOW_SUPPORTED':raise RuntimeError('V4_NOT_SUPPORTED')
        if self.v4.get('selected_skill_id')!='HIGH_ONLY_TRIPLE_KNN_V4':raise RuntimeError('V4_SELECTION_DRIFT')

        ps=self.parent.get('selected_spec') or {}
        vs=self.v4.get('selected_spec') or {}
        if ps.get('family')!='KNN' or int(ps.get('order',-1))!=2:raise RuntimeError('PARENT_SPEC_UNEXPECTED')
        if int(vs.get('order',-1))!=3:raise RuntimeError('V4_SPEC_UNEXPECTED')
        self.activation_min_size=int(vs.get('activation_min_size',-1))
        if self.activation_min_size!=10:raise RuntimeError('V4_ACTIVATION_BOUNDARY_UNEXPECTED')

        self.parent_model=self.parent.get('selected_model')
        self.v4_model=self.v4.get('selected_model')
        if not isinstance(self.parent_model,dict) or not isinstance(self.v4_model,dict):raise RuntimeError('MODEL_MISSING')

        self.source_ids=sorted(str(x['id']) for x in self.corpus['source_digests'])
        self.source_pairs=list(combinations(self.source_ids,2))
        self.source_triples=list(combinations(self.source_ids,3))

    def route(self,case:dict):
        size=int(round(float(case['x']['source_count'])))
        return 'V4_HIGH' if size>=self.activation_min_size else 'V2_PARENT'

    def _augment(self,key:str,x:dict,order:int):
        z=dict(x);present=set(str(key).split('|'))
        for sid in self.source_ids:z['src::'+sid]=1.0 if sid in present else 0.0
        if order>=2:
            for a,b in self.source_pairs:z['srcpair::'+a+'&&'+b]=1.0 if a in present and b in present else 0.0
        if order>=3:
            for a,b,c in self.source_triples:z['srctri::'+a+'&&'+b+'&&'+c]=1.0 if a in present and b in present and c in present else 0.0
        return z

    def predict(self,case:dict):
        route=self.route(case)
        if route=='V2_PARENT':
            return knn_predict(self.parent_model,self._augment(case['key'],case['x'],2))
        if route=='V4_HIGH':
            return knn_predict(self.v4_model,self._augment(case['key'],case['x'],3))
        raise RuntimeError('UNKNOWN_ROUTE:'+str(route))

    def __enter__(self):
        return self

    def __exit__(self,*args):
        return False

    def snapshot(self):
        return {
          'schema':'yado.g2.canonical_high_scale_binding_runtime.v4',
          'activation_min_size':self.activation_min_size,
          'parent_candidate_digest':self.parent.get('candidate_digest'),
          'v4_candidate_digest':self.v4.get('candidate_digest'),
          'v4_selected_skill_id':self.v4.get('selected_skill_id'),
          'binding_digest':self.binding.get('binding_digest'),
        }
