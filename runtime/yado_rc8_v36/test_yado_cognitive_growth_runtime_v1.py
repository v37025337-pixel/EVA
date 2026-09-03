import unittest
from itertools import product

from yado_cognitive_growth_runtime_v1 import (
    synthesize_logic_minimal, synthesize_logic_exact_table, logic_accuracy,
    learn_multicontext_precedence, planning_accuracy,
    fit_centroid_strategy, centroid_accuracy, select_centroid_features,
)

class TestCognitiveGrowthRuntime(unittest.TestCase):
    def test_logic_four_way_parity(self):
        cases=[]
        for bits in product([False,True],repeat=4):
            x=dict(zip('abcd',bits)); y=bits[0]^bits[1]^bits[2]^bits[3]
            cases.append((x,y))
        m,meta=synthesize_logic_minimal(cases,max_nodes=11)
        self.assertEqual(logic_accuracy(m,cases),1.0)
        self.assertLessEqual(meta.get('nodes',999),11)

    def test_exact_table_fallback_refuses_incomplete(self):
        m,meta=synthesize_logic_exact_table([({'a':False},False)],max_vars=4)
        self.assertIsNone(m)
        self.assertEqual(meta['status'],'REJECT_INCOMPLETE_TABLE')

    def test_multicontext_planning(self):
        traces=[]; episodes=[]
        orders={
            (False,False):['OBSERVE','MODEL','TEST','ACT'],
            (True,False):['MODEL','OBSERVE','TEST','ACT'],
            (False,True):['OBSERVE','TEST','MODEL','ACT'],
            (True,True):['TEST','MODEL','OBSERVE','ACT'],
        }
        i=0
        for key,order in orders.items():
            for _ in range(3):
                ctx={'urgent':key[0],'uncertain':key[1]}; traces.append((ctx,order))
                actions=[{'id':f'{i}-{j}','role':r} for j,r in enumerate(reversed(order))]
                episodes.append((ctx,actions,order));i+=1
        m=learn_multicontext_precedence(traces,threshold=.75,min_support=2,max_context_keys=2)
        self.assertEqual(planning_accuracy(m,episodes),1.0)

    def test_centroid_filters_noise(self):
        fit=[];val=[]
        for i in range(40):
            label='LEFT' if i%2==0 else 'RIGHT'; sx=-2.0 if label=='LEFT' else 2.0
            fit.append(({'signal':sx+(i%5)*.02,'noise':float((i*17)%13)-6.0},label))
        for i in range(20):
            label='LEFT' if i%2==0 else 'RIGHT'; sx=-2.1 if label=='LEFT' else 2.1
            val.append(({'signal':sx,'noise':float((i*23)%17)-8.0},label))
        m,meta=select_centroid_features(fit,val)
        self.assertEqual(centroid_accuracy(m,val),1.0)
        self.assertGreaterEqual(meta['selected_features'],1)

if __name__=='__main__': unittest.main()
