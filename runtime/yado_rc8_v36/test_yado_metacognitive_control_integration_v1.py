import tempfile,unittest
from pathlib import Path
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
class TestMetaControlIntegration(unittest.TestCase):
 def test_kernel_uses_history_to_withhold_overconfident_weak_task(self):
  with tempfile.TemporaryDirectory() as td:
   k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(Path(td)/'x.db'))
   obs=[{'capability':'MATH','difficulty':.8,'success':False} for _ in range(30)]
   p=k.build_capability_boundary_profile(obs)
   try:
    d=k.metacognitive_decide({'task_id':'x','capability':'MATH','difficulty':.8,'verbal_confidence':.95,'evidence_coverage':.9,'novelty':.7,'framework_conflict':False},p)
    self.assertEqual(d.action,'WITHHOLD')
   finally:
    k.close()
