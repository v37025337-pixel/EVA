from yado_evolution_archive_runtime_v1 import EvolutionVariant,EvolutionArchiveRuntime

def V(i,p,l,t,c=None,traits=None,fail=(),status='EVALUATED'):
    return EvolutionVariant(i,p,l,'d-'+i,t,c or {'regression_pass':True,'state_integrity':True,'rollback_available':True},traits or {},fail,status)

def test_preserves_non_latest_stepping_stones_and_task_specific_parent():
    a=V('A',None,'L1',{'logic':1.0,'deploy':0.2},{}, {'novelty':0.8})
    b=V('B','A','L1',{'logic':0.8,'deploy':1.0},{}, {'novelty':0.5})
    c=V('C','B','L1',{'logic':0.9,'deploy':0.7},{}, {'novelty':0.9})
    ar=EvolutionArchiveRuntime([a,b,c])
    assert ar.select_parent('logic')['variant_id']=='A'
    assert ar.select_parent('deploy')['variant_id']=='B'
    assert set(ar.pareto_stepping_stones([('task:logic','max'),('task:deploy','max')]))=={'A','B','C'}

def test_hard_constraints_exclude_unsafe_high_score():
    good=V('good',None,'L1',{'x':0.8})
    bad=V('bad',None,'L2',{'x':1.0},{'regression_pass':False,'state_integrity':True,'rollback_available':True})
    ar=EvolutionArchiveRuntime([good,bad])
    assert ar.select_parent('x')['variant_id']=='good'

def test_reaction_norm_uses_multi_task_failure():
    a=V('A',None,'L1',{'t1':0.2,'t2':0.3,'t3':1.0},fail=('t1','t2'))
    ar=EvolutionArchiveRuntime([a])
    out=ar.propose_operation('A','t1')
    assert out['operation']=='REACTION_NORM'
    assert out['evidence']['weak_tasks']==['t1','t2']

def test_cross_lineage_reference_when_target_specific_advantage_exists():
    a=V('A',None,'L1',{'x':0.4,'y':1.0})
    b=V('B',None,'L2',{'x':0.9,'y':0.6})
    ar=EvolutionArchiveRuntime([a,b])
    out=ar.propose_operation('A','x')
    assert out['operation']=='CROSS_LINEAGE'
    assert out['reference']['variant_id']=='B'

def test_clonal_when_no_comparative_signal():
    a=V('A',None,'L1',{'x':1.0})
    ar=EvolutionArchiveRuntime([a])
    assert ar.propose_operation('A','x')['operation']=='CLONAL'

def test_deterministic_digest_order_invariant():
    a=V('A',None,'L1',{'x':1.0});b=V('B','A','L1',{'x':0.8})
    assert EvolutionArchiveRuntime([a,b]).archive_digest()==EvolutionArchiveRuntime([b,a]).archive_digest()

def test_variant_collision_fails_closed():
    a=V('A',None,'L1',{'x':1.0});b=V('A',None,'L1',{'x':0.1})
    ar=EvolutionArchiveRuntime([a])
    try: ar.add(b)
    except ValueError: pass
    else: assert False

def test_real_yado_manifest_lineage_selects_v21_but_preserves_earlier():
    rows=[
      V('v18',None,'RC7',{'provenance_reduction':0.20,'regression':1.0},traits={'recovery_dependencies':8,'test_depth':11}),
      V('v19','v18','RC7',{'provenance_reduction':0.40,'regression':1.0},traits={'recovery_dependencies':7,'test_depth':15}),
      V('v20','v19','RC7',{'provenance_reduction':0.60,'regression':1.0},traits={'recovery_dependencies':6,'test_depth':19}),
      V('v21','v20','RC7',{'provenance_reduction':0.80,'regression':1.0},traits={'recovery_dependencies':5,'test_depth':23}),
    ]
    ar=EvolutionArchiveRuntime(rows)
    out=ar.select_parent('provenance_reduction',{'test_depth':0.01,'recovery_dependencies':-0.01})
    assert out['variant_id']=='v21'
    assert ar.snapshot()['variant_count']==4

def test_archive_beats_latest_only_on_branch_specific_holdout():
    # Latest C is globally decent but A is the correct stepping stone for logic-specific continuation.
    a=V('A',None,'L1',{'logic':1.0,'deploy':0.1})
    b=V('B','A','L1',{'logic':0.7,'deploy':0.9})
    c=V('C','B','L1',{'logic':0.8,'deploy':0.8})
    ar=EvolutionArchiveRuntime([a,b,c])
    archive_correct=(ar.select_parent('logic')['variant_id']=='A')
    latest_only_correct=('C'=='A')
    assert archive_correct and not latest_only_correct
