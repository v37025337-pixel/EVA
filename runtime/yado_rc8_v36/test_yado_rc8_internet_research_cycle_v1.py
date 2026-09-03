import unittest
from yado_rc8_internet_research_cycle_v1 import marker_evidence,URLS
class TestInternetResearchCycle(unittest.TestCase):
    def test_marker_evidence_is_bounded_and_deterministic(self):
        x=marker_evidence('Skill memory transfer benchmark verifier skill')
        self.assertEqual(x['skill'],2);self.assertEqual(x['memory'],1);self.assertGreaterEqual(x['transfer'],1);self.assertGreaterEqual(x['evaluation'],1);self.assertGreaterEqual(x['gate'],1)
    def test_sources_are_https_arxiv_only(self):
        self.assertGreaterEqual(len(URLS),5);self.assertTrue(all(u.startswith('https://arxiv.org/') for u in URLS))
if __name__=='__main__':unittest.main()
