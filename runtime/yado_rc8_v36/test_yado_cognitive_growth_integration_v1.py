import os,tempfile,unittest
from itertools import product
from yado_core_v3_0_rc7_deep_integrity import UnifiedYADOKernelV30RC7DeepIntegrity
from yado_cognitive_growth_runtime_v1 import planning_accuracy, centroid_accuracy

class TestCognitiveGrowthIntegration(unittest.TestCase):
    def setUp(self):
        f=tempfile.NamedTemporaryFile(suffix='.sqlite',delete=False);self.path=f.name;f.close()
        self.k=UnifiedYADOKernelV30RC7DeepIntegrity(self.path)
    def tearDown(self):
        self.k.close()
        try: os.unlink(self.path)
        except OSError: pass
    def test_snapshot_advertises_bounded_growth(self):
        c=self.k.unified_snapshot()['cognitive_growth']
        self.assertEqual(c['status'],'ACTIVE_BOUNDED_COGNITIVE_GROWTH_V1')
        self.assertTrue(c['fallback_preserved'])
        self.assertFalse(c['replaces_existing_organs'])
    def test_logic_growth_six_variable_parity(self):
        cases=[]
        for bits in product([False,True],repeat=6):
            x=dict(zip('abcdef',bits)); y=False
            for b in bits: y ^= b
            cases.append((x,y))
        r=self.k.logic_growth_synthesize(cases,max_nodes=15,max_signatures=524288)
        self.assertEqual(r['accuracy'],1.0)
        self.assertEqual(r['meta']['backend'],'BITSET')
    def test_thinking_growth_and_intelligence_growth(self):
        orders={(False,False):['OBSERVE','MODEL','TEST','ACT'],(True,False):['MODEL','OBSERVE','TEST','ACT'],(False,True):['OBSERVE','TEST','MODEL','ACT'],(True,True):['TEST','MODEL','OBSERVE','ACT']}
        train=[];episodes=[];i=0
        for key,order in orders.items():
            for _ in range(3):
                ctx={'urgent':key[0],'uncertain':key[1]};train.append((ctx,order))
                actions=[{'id':f'{i}-{j}','role':r} for j,r in enumerate(reversed(order))];episodes.append((ctx,actions,order));i+=1
        m=self.k.thinking_growth_learn(train,max_context_keys=2)
        self.assertEqual(planning_accuracy(m,episodes),1.0)
        fit=[];val=[]
        for i in range(60):
            label='A' if i%2==0 else 'B';s=-2.0 if label=='A' else 2.0
            fit.append(({'signal':s+(i%3)*.03,'noise':float((i*13)%19)-9},label))
        for i in range(20):
            label='A' if i%2==0 else 'B';s=-2.1 if label=='A' else 2.1
            val.append(({'signal':s,'noise':float((i*17)%23)-11},label))
        out=self.k.intelligence_growth_fit(fit,val,fit+val)
        self.assertEqual(centroid_accuracy(out['model'],val),1.0)

if __name__=='__main__':unittest.main()
