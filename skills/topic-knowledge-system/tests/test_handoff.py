import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from topic_handoff import audit, comparison_status, digest, plan_gaps
from build_topic import build


def bundle():
    identity = {"paper_id": "synthetic-cache", "document_version_id": "v1"}
    unit = {"unit_id": "u1", "text": "Reuse results only when the document version is unchanged.", "locator": {"page": 1}}
    evidence = {"evidence_id": "e1", "unit_id": "u1", "quote": unit["text"]}
    fact = {"fact_id": "f1", "kind": "method", "text": "文档版本不变时复用结果。", "evidence_ids": ["e1"], "observation": None}
    fingerprint = digest({"paper": identity, "fact": fact, "evidence": [evidence], "original_units": [unit]})
    return {"schema_version": "paper-evidence/1", "paper": identity, "paper_key": digest(identity),
            "sources": [unit], "evidence": [evidence], "facts": [fact],
            "verification": {"facts": [{"fact_id": "f1", "fact_sha256": fingerprint, "support_status": "supported"}]}}


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.bundle = bundle()
        (self.base / "paper.json").write_text(json.dumps(self.bundle))
        key = self.bundle["paper_key"]
        self.topic = {"title": "缓存专题", "subtitle": "合成数据测试", "core": {"name": "缓存", "label": "结果复用", "description": "何时可以复用？"},
            "branches": [{"id": "validity", "title": "复用条件", "description": "何时复用？", "papers": [
                {"id": "cache", "paper_key": key, "name": "缓存", "url": "https://example.org/paper", "method": "文档版本不变时复用结果。"}]}]}
        self.research = {"schema_version": "topic-research/1", "source_policy": "local",
            "papers": [{"paper_key": key, "bundle": "paper.json"}],
            "candidates": [{"candidate_id": "c1", "paper_key": key, "status": "included", "reason": "直接涉及复用条件"}],
            "claims": [{"claim_id": "m1", "kind": "report", "text": "文档版本不变时复用结果。", "supports": [{"paper_key": key, "fact_id": "f1"}]}],
            "bindings": {"/branches/0/papers/0/method": "m1"}}

    def test_supported_binding_renders_and_changed_claim_is_rejected(self):
        self.assertTrue(audit(self.research, self.topic, self.base)["ok"])
        html, svg = build(self.topic, self.base)
        self.assertIn("文档版本不变", html)
        self.assertIn("<svg", svg)
        self.topic["branches"][0]["papers"][0]["method"] = "任何时候都复用结果。"
        self.assertFalse(audit(self.research, self.topic, self.base)["ok"])
        self.research["claims"][0]["text"] = "任何时候都复用结果。"
        self.assertFalse(audit(self.research, self.topic, self.base)["ok"])

    def test_unreviewed_fact_blocks_only_published_claim(self):
        self.bundle["verification"]["facts"][0]["support_status"] = "unreviewed"
        (self.base / "paper.json").write_text(json.dumps(self.bundle))
        self.assertFalse(audit(self.research, self.topic, self.base)["ok"])
        self.topic["branches"][0]["papers"] = []
        self.research["bindings"] = {}
        self.assertTrue(audit(self.research, self.topic, self.base)["ok"])

    def test_changed_source_context_invalidates_old_review(self):
        self.bundle["sources"][0]["text"] += " This condition excludes independent queries."
        (self.base / "paper.json").write_text(json.dumps(self.bundle))
        with self.assertRaisesRegex(ValueError, "Stale"):
            audit(self.research, self.topic, self.base)

    def test_comparison_unknown_settings_are_not_equal(self):
        observation = {"task": "qa", "dataset": "test", "split": "test", "metric": "accuracy", "unit": "%", "direction": "higher",
            "conditions": [{"name": "model", "value": "m"}, {"name": "compute_budget", "value": "100 steps"},
                           {"name": "evaluation_protocol", "value": "greedy"}]}
        self.assertEqual(comparison_status(observation, observation)[0], "comparable")
        changed = copy.deepcopy(observation)
        changed["conditions"][1]["value"] = "1000 steps"
        self.assertEqual(comparison_status(observation, changed)[0], "not_comparable")
        changed["conditions"] = []
        self.assertEqual(comparison_status(changed, changed)[0], "insufficient")

    def test_gap_plan_respects_source_policy_budget_and_query_history(self):
        state = {"source_policy": "local", "search_budget": {"max_queries": 2, "max_rounds": 2},
                 "gaps": [{"gap_id": "g1", "question": "Missing baseline", "status": "open", "priority": 1},
                          {"gap_id": "g2", "question": "Counterexample", "status": "open", "priority": 2}]}
        self.assertFalse(plan_gaps(state)["tasks"])
        state["source_policy"] = "web"
        state["search_history"] = [{"round_id": "r1", "query": "Missing baseline"}]
        self.assertEqual([t["gap_id"] for t in plan_gaps(state)["tasks"]], ["g2"])
        state["search_history"].append({"round_id": "r2", "query": "Counterexample"})
        self.assertFalse(plan_gaps(state)["tasks"])


if __name__ == "__main__":
    unittest.main()
