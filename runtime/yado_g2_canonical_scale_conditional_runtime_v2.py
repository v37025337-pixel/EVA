from __future__ import annotations
from pathlib import Path
from itertools import combinations
import hashlib,json,shutil,sys,tempfile

RUNTIME=Path(__file__).resolve().parent
REPO=RUNTIME.parent
PKG=RUNTIME/'yado_rc8_v36'
if str(PKG) not in sys.path:sys.path.insert(0,str(PKG))

from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_organ_runtime_native_v1 import tree_predict
from yado_cognitive_growth_runtime_v1 import centroid_predict,knn_predict

def _load(path:Path):
    return json.loads(path.read_text(encoding='utf-8'))

def _sha(path:Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

class CanonicalScaleConditionalRuntimeV2:
    """
    Binding-only runtime V2.
    Routing is executed by the native COMMITTED DevelopmentalExecutiveV22 program.
    Low-scale behavior is the previously stable branch.
    High-scale behavior is the G2-selected PAIR_KNN repair V2.
    This class adds no learned threshold, label mapping, or model selection.
    """
    def __init__(self,binding:dict|None=None,repo_root:Path|None=None):
        self.repo=Path(repo_root or REPO)
        self.binding=dict(binding or _load(self.repo/'canonical/yado-native-selector-canonical-binding-v2.json'))
        for rel,expected in self.binding['artifact_sha256'].items():
            p=self.repo/rel
            if not p.exists():raise RuntimeError('BOUND_ARTIFACT_MISSING:'+rel)
            actual=_sha(p)
            if actual!=expected:raise RuntimeError('BOUND_ARTIFACT_DIGEST_MISMATCH:'+rel)

        registry=self.repo/self.binding['selector_registry']['path']
        tmp=tempfile.NamedTemporaryFile(prefix='yado-selector-registry-v2-',suffix='.sqlite',delete=False)
        tmp.close()
        self._tmp_db=Path(tmp.name)
        shutil.copy2(registry,self._tmp_db)
        self.kernel=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(self._tmp_db))
        active=dict(self.kernel.executive.active_program_by_capability)
        cap=self.binding['selector_registry']['capability']
        if active.get(cap)!=self.binding['selector_registry']['program_id']:
            self.close();raise RuntimeError('BOUND_SELECTOR_NOT_ACTIVE')

        self.base=_load(self.repo/self.binding['branch_artifacts']['base'])
        self.cal=_load(self.repo/self.binding['branch_artifacts']['calibrated'])
        self.local=_load(self.repo/self.binding['branch_artifacts']['local_knn'])
        self.high=_load(self.repo/self.binding['branch_artifacts']['high_scale_repair_v2'])
        self.corpus=_load(self.repo/self.binding['branch_artifacts']['corpus'])
        self.source_ids=sorted(str(x['id']) for x in self.corpus['source_digests'])
        self.source_pairs=list(combinations(self.source_ids,2))

        if self.high.get('state')!='SHADOW_SUPPORTED':
            self.close();raise RuntimeError('HIGH_SCALE_REPAIR_NOT_SUPPORTED')
        spec=self.high.get('selected_spec') or {}
        if spec.get('family')!='KNN' or int(spec.get('order',-1))!=2:
            self.close();raise RuntimeError('HIGH_SCALE_REPAIR_SPEC_UNEXPECTED')
        self.high_model=self.high.get('selected_model')
        if not isinstance(self.high_model,dict):
            self.close();raise RuntimeError('HIGH_SCALE_REPAIR_MODEL_MISSING')

    def close(self):
        k=getattr(self,'kernel',None)
        if k is not None:
            try:k.close()
            finally:self.kernel=None
        p=getattr(self,'_tmp_db',None)
        if p is not None:
            p.unlink(missing_ok=True)
            for suffix in ('-wal','-shm'):
                Path(str(p)+suffix).unlink(missing_ok=True)
            self._tmp_db=None

    def __enter__(self):return self
    def __exit__(self,*args):self.close()

    def route(self,x:dict):
        return self.kernel.executive.execute_capability(
            self.binding['selector_registry']['capability'],
            {'source_count':float(x['source_count'])},
        )

    def _distances(self,model,x):
        rows=[]
        for label,center in model['centroids'].items():
            d=0.0
            for key in model['features']:
                scale=max(float(model['scales'].get(key,1.0)),1e-12)
                d+=((float(x.get(key,0.0))-float(center[key]))/scale)**2
            rows.append((d,label))
        return sorted(rows,key=lambda z:(z[0],z[1]))

    def _margin(self,model,x):
        rows=self._distances(model,x)
        return 0.0 if len(rows)<2 else max(0.0,rows[1][0]-rows[0][0])

    def _calibrated_parent(self,x):
        result=self.base['kernel_result'];parent_model=result['model']
        generator=self.cal['generator'];gate=generator['gate_model'];corr=generator['corrector_model']
        threshold=float(self.cal['selected_threshold'])
        base_pred=tree_predict(parent_model,x)
        if centroid_predict(gate,x)!='PARENT_ERROR':return base_pred
        if self._margin(gate,x)+1e-12<threshold:return base_pred
        return centroid_predict(corr,x)

    def _old_branch(self,x):
        sm=self.local.get('selected_model') or {}
        base=self._calibrated_parent(x)
        if not sm:return base
        return knn_predict(sm['corrector'],x) if knn_predict(sm['gate'],x)=='BASE_ERROR' else base

    def _augment_pair(self,key,x):
        z=dict(x);present=set(str(key).split('|'))
        for sid in self.source_ids:z['src::'+sid]=1.0 if sid in present else 0.0
        for a,b in self.source_pairs:z['srcpair::'+a+'&&'+b]=1.0 if a in present and b in present else 0.0
        return z

    def _high_branch(self,key,x):
        return knn_predict(self.high_model,self._augment_pair(key,x))

    def predict(self,case:dict):
        route=self.route(case['x'])
        if route==self.binding['branches']['low']:
            return self._old_branch(case['x'])
        if route==self.binding['branches']['high']:
            return self._high_branch(case['key'],case['x'])
        raise RuntimeError('UNKNOWN_SELECTOR_ROUTE:'+str(route))

    def snapshot(self):
        return {
          'schema':'yado.g2.canonical_scale_conditional_runtime.v2',
          'selector_program_id':self.binding['selector_registry']['program_id'],
          'selector_capability':self.binding['selector_registry']['capability'],
          'high_scale_candidate_digest':self.high.get('candidate_digest'),
          'binding_digest':self.binding.get('binding_digest'),
        }
