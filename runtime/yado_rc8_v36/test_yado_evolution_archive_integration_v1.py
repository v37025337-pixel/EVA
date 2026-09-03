from pathlib import Path
from yado_core_v3_0_rc7_deep_integrity import UnifiedYADOKernelV30RC7DeepIntegrity

def rows():
    base={'regression_pass':True,'state_integrity':True,'rollback_available':True}
    return [
      {'variant_id':'v18','parent_id':None,'lineage_id':'RC7','artifact_digest':'m18','task_scores':{'provenance_reduction':.2,'regression':1},'constraints':base,'traits':{'recovery_dependencies':8,'test_depth':11}},
      {'variant_id':'v19','parent_id':'v18','lineage_id':'RC7','artifact_digest':'m19','task_scores':{'provenance_reduction':.4,'regression':1},'constraints':base,'traits':{'recovery_dependencies':7,'test_depth':15}},
      {'variant_id':'v20','parent_id':'v19','lineage_id':'RC7','artifact_digest':'m20','task_scores':{'provenance_reduction':.6,'regression':1},'constraints':base,'traits':{'recovery_dependencies':6,'test_depth':19}},
      {'variant_id':'v21','parent_id':'v20','lineage_id':'RC7','artifact_digest':'m21','task_scores':{'provenance_reduction':.8,'regression':1},'constraints':base,'traits':{'recovery_dependencies':5,'test_depth':23}},
    ]

def test_kernel_exposes_archive_selection(tmp_path):
    k=UnifiedYADOKernelV30RC7DeepIntegrity(db_path=str(tmp_path/'ea.sqlite'))
    try:
        out=k.select_evolution_parent(rows(),'provenance_reduction',{'test_depth':.01,'recovery_dependencies':-.01})
        assert out['action']=='SELECT_PARENT'
        assert out['variant_id']=='v21'
        assert len(out['archive_digest'])==64
    finally:
        k.close()

def test_kernel_archive_does_not_mutate_canonical_state(tmp_path):
    state=Path(__file__).parent/'yado_canonical_state_v3_rc7_deep_integrity.json'
    import hashlib
    before=hashlib.sha256(state.read_bytes()).hexdigest()
    k=UnifiedYADOKernelV30RC7DeepIntegrity(db_path=str(tmp_path/'ea2.sqlite'))
    try:
        k.select_evolution_parent(rows(),'provenance_reduction')
    finally:
        k.close()
    after=hashlib.sha256(state.read_bytes()).hexdigest()
    assert before==after=='1bee35d94b6e853700b86fafbe7bce5e0199a167f9b918b31de547cfc83be52b'
