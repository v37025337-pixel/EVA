import copy
import unittest

from yado_self_directed_web_research_v1 import SelfDirectedWebResearchV1


SEARCH = "https://html.duckduckgo.com/html/?q=x"
HOSTS = ["alpha.example.com", "beta.example.net", "gamma.example.org", "delta.example.edu"]


def prepare(goal):
    return {
        "status": "PASS_CAUSAL_PREPARE",
        "thinking": {"status": "PASS_TRI_ORGAN_THINKING"},
        "logic": {"status": "PASS_TRI_ORGAN_LOGIC"},
        "intelligence": {"status": "PASS_TRI_ORGAN_INTELLIGENCE_ROUTE"},
        "action_plan": {"plan_digest": "a" * 64},
    }


def meta(evidence):
    return {"decision": "CONTINUE" if evidence.get("next_required_capability") else "COMMIT", "gate": "META_ACTION"}


def fake_fetch(url):
    if "duckduckgo.com" in url or "google.com/search" in url or "search.brave.com" in url:
        links = "".join(f"<a href='https://{h}/doc'>r</a>" for h in HOSTS)
        return {"content": f"<html>{links}</html>", "receipt": {"final_url": SEARCH, "final_host": "html.duckduckgo.com", "sha256": "s" * 64, "read_only": True}}
    host = url.split("/")[2]
    text = "alpha protocol evidence explains alpha protocol evidence behavior and verification across independent implementations. " * 3
    return {"content": f"<html><body>{text}</body></html>", "receipt": {
        "final_url": url, "final_host": host, "sha256": (host[0] * 64), "bytes": len(text),
        "read_only": True, "credentials_used": False, "external_write": False, "private_network_access": False,
    }}


def no_discover(content, base, limit):
    return []


class SelfDirectedWebResearchTests(unittest.TestCase):
    def test_two_independent_sources_are_compared_and_memory_is_written(self):
        c = SelfDirectedWebResearchV1(prepare, meta)
        r = c.research("alpha protocol evidence", fetch=fake_fetch, discover=no_discover, max_sources=2, closure_source_target=2)
        self.assertEqual(r["status"], "PASS_SELF_DIRECTED_WEB_RESEARCH_V1")
        self.assertEqual(r["comparison"]["current_independent_source_count"], 2)
        self.assertEqual(r["comparison"]["coverage_ratio"], 1.0)
        self.assertIsNone(r["next_goal"])
        self.assertEqual(r["memory_feedback"]["episode_count"], 1)

    def test_verified_deficit_creates_next_goal(self):
        c = SelfDirectedWebResearchV1(prepare, meta)
        r = c.research("alpha protocol evidence", fetch=fake_fetch, discover=no_discover, max_sources=2, closure_source_target=4)
        self.assertEqual(r["status"], "PASS_SELF_DIRECTED_WEB_RESEARCH_V1")
        self.assertIn("SOURCE_DIVERSITY_DEFICIT", r["deficits"])
        self.assertIn("additional independent", r["next_goal"].lower())

    def test_two_generations_use_memory_to_avoid_old_hosts_and_close_goal(self):
        c = SelfDirectedWebResearchV1(prepare, meta)
        r = c.run_generations(
            "alpha protocol evidence", fetch=fake_fetch, discover=no_discover,
            max_generations=3, max_sources_per_generation=2, closure_source_target=4,
        )
        self.assertEqual(r["status"], "PASS_BOUNDED_SELF_DIRECTED_WEB_RESEARCH_GENERATIONS_V1")
        self.assertEqual(r["generation_count"], 2)
        self.assertTrue(r["goal_closed"])
        self.assertEqual(len(r["independent_hosts_accumulated"]), 4)

    def test_state_roundtrip_and_tamper_detection(self):
        c = SelfDirectedWebResearchV1(prepare, meta)
        c.research("alpha protocol evidence", fetch=fake_fetch, discover=no_discover, max_sources=2, closure_source_target=2)
        state = c.export_state()
        d = SelfDirectedWebResearchV1(prepare, meta)
        snap = d.import_state(state)
        self.assertEqual(snap["episode_count"], 1)
        bad = copy.deepcopy(state)
        bad["episodes"][0]["objective"] = "tampered"
        with self.assertRaises(ValueError):
            d.import_state(bad)

    def test_restored_memory_allows_revalidation_of_known_hosts(self):
        c = SelfDirectedWebResearchV1(prepare, meta)
        urls = [f"https://{host}/doc" for host in HOSTS[:2]]
        c.research("alpha protocol evidence", fetch=fake_fetch, seed_urls=urls,
                   use_search=False, max_sources=2, closure_source_target=2)
        previous = c.export_state()
        restored = SelfDirectedWebResearchV1(prepare, meta)
        restored.import_state(previous)
        result = restored.research("alpha protocol evidence", fetch=fake_fetch,
            seed_urls=urls, use_search=False, max_sources=2, closure_source_target=2)
        self.assertEqual(result["status"], "PASS_SELF_DIRECTED_WEB_RESEARCH_V1")
        self.assertEqual(result["comparison"]["new_independent_host_count"], 0)
        self.assertEqual(result["comparison"]["revisited_hosts"], sorted(HOSTS[:2]))
        self.assertTrue(all(s["previously_observed_host"] for s in result["sources"]))
        self.assertEqual(restored.export_state()["episodes"][:1], previous["episodes"])

    def test_known_hosts_do_not_displace_available_new_hosts(self):
        c = SelfDirectedWebResearchV1(prepare, meta)
        urls = [f"https://{host}/doc" for host in HOSTS]
        c.research("alpha protocol evidence", fetch=fake_fetch, seed_urls=urls[:2],
                   use_search=False, max_sources=2, closure_source_target=4)
        result = c.research("alpha protocol evidence", fetch=fake_fetch, seed_urls=urls,
                            use_search=False, max_sources=2, closure_source_target=4)
        self.assertEqual({s["host"] for s in result["sources"]}, set(HOSTS[2:]))
        self.assertEqual(result["comparison"]["new_independent_host_count"], 2)

    def test_revisiting_one_host_cannot_fake_independent_corroboration(self):
        c = SelfDirectedWebResearchV1(prepare, meta)
        urls = [f"https://{HOSTS[0]}/{name}" for name in ("one", "two", "three")]
        for _ in range(2):
            result = c.research("alpha protocol evidence", fetch=fake_fetch,
                seed_urls=urls, use_search=False, max_sources=3, closure_source_target=2)
            self.assertEqual(result["status"], "WITHHOLD_SELF_DIRECTED_WEB_RESEARCH_V1")
            self.assertEqual(result["comparison"]["current_independent_source_count"], 1)


if __name__ == "__main__":
    unittest.main()
