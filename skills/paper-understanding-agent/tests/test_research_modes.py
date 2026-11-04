"""Exercise real scheduler/assembly paths with explicitly synthetic model receipts."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "runtime/scripts"))
import run_agent as agent
from task_profiles import project, repair_plan
from evidence_bundle import export_bundle
from read_evidence import lookup
from validate_output import validate


def read(path):
    return json.loads(path.read_text())


def missing(path):
    return {"path": path, "reason": "partial_coverage", "detail": "Synthetic test has no generated scientific content."}


class FixtureTransport:
    def __init__(self):
        self.prompts = []

    def __call__(self, prompt, directory):
        self.prompts.append(prompt)
        task = json.JSONDecoder().raw_decode(prompt.split("TASK AND ORIGINAL SOURCES:\n", 1)[1])[0]
        spec = task["stage"]
        kind, group = spec["kind"], spec["group"]
        payload = {"status": "partial", "evidence": [], "facts": [], "missing_information": [],
                   "limitations": ["Synthetic fixture; no scientific assessment"], "data": {}}
        data, gaps = payload["data"], payload["missing_information"]
        if kind == "page":
            data.update(page_id=group["page_id"], metadata_candidates=[], summary=[], open_links=[])
            gaps.append(missing("/page_extractions"))
        elif kind == "section":
            data.update(section_id=group["section_id"], title=group["title"], summary=[], open_questions=[])
            gaps.append(missing("/section_summaries"))
        elif kind == "metadata":
            meta = {k: [] for k in ("authors", "affiliations", "dates", "identifiers", "resources", "references", "fact_ids")}
            meta.update(title=None, venue=None, original_abstract=None, references_scope="all_visible")
            data["metadata"] = meta
            gaps.extend(missing("/metadata/" + k) for k in meta if not meta[k])
        elif kind == "understanding":
            data["understanding"] = {k: [] for k in (*agent.workflow.FIELDS, "problem_signatures", "related_work")}
            gaps.extend(missing("/understanding/" + k) for k in agent.workflow.FIELDS)
        elif kind == "assessment":
            data["assessments"] = [{"dimension_id": d, "grade": None, "status": "insufficient", "judgment": "No assessment",
                "supporting_fact_ids": [], "counter_fact_ids": [], "conditions": [], "missing_evidence": ["Synthetic fixture"]}
                for d in agent.workflow.DIMS]
            data["assessment_summary"] = {"reading_tier": "insufficient_material", "summary": {"text": "No assessment", "fact_ids": []},
                "assessment_refs": [], "conditions": [], "missing_evidence": ["Synthetic fixture"]}
            data["recommendations"] = []
        elif kind == "reading":
            if "ORIGINAL SOURCE RESPONSE" not in prompt:
                payload = {"request_original_unit_ids": ["u3"], "reason": "Need the result context"}
            else:
                data.update(recommendations=[], reuse_cards=[], insight_rules=[], glossary=[],
                    display={"one_liner": {"text": "No reading", "fact_ids": []}, "highlight_item_ids": [], "recommendation_ids": []},
                    content_products={"abstract": [], "home_digest": [], "contribution_highlights": [], "deep_read": []})
                gaps.append(missing("/content_products/deep_read"))
        elif kind == "references":
            data.update(references=[], unparsed_segments=[], excluded_segments=[])
            gaps.append(missing("/metadata/references"))
        if kind in {"assessment", "reading"} and "data" in payload:
            fid, eid = spec["stage_id"] + "::f1", spec["stage_id"] + "::e1"
            original = read(ROOT / "examples/input.json")["papers"][0]["units"]
            quote = next(u["text"] for u in original if u["unit_id"] == "u3")
            payload["evidence"] = [{"evidence_id": eid, "unit_id": "u3", "quote": quote}]
            payload["facts"] = [{"fact_id": fid, "kind": "reported_result", "text": "本文中位延迟12ms。", "evidence_ids": [eid],
                "observation": {"subject": "cache", "role": "ours", "task": "重复查询", "dataset": "ToySet", "split": "test",
                                "metric": "median latency", "value": 12, "raw_value": "12 ms", "unit": "ms", "direction": "lower", "conditions": []}}]
            one = {"text": "本文中位延迟12ms。", "basis": "paraphrase", "fact_ids": [fid]}
            if kind == "assessment":
                data["assessment_summary"]["summary"] = one
            else:
                data["display"]["one_liner"] = one
        response = json.dumps(payload, ensure_ascii=False)
        call = "synthetic-" + uuid.uuid4().hex
        events = [{"type": "thread.started", "thread_id": call},
                  {"type": "item.completed", "item": {"type": "agent_message", "text": response}},
                  {"type": "turn.completed", "usage": {"input_tokens": 0, "output_tokens": 0}}]
        return agent.workflow.Invocation(argv=["synthetic-fixture"], returncode=0, elapsed_seconds=0,
            stdout=("\n".join(json.dumps(e) for e in events)).encode(), stderr=b"", synthetic_response=response)


class ResearchModesTests(unittest.TestCase):
    def setUp(self):
        self.inp = read(ROOT / "examples/input.json")
        self.plan = read(ROOT / "examples/manifest.json")

    def test_screen_scope_is_small_and_appendix_requires_explicit_activation(self):
        self.inp["papers"][0]["units"].append({"unit_id": "a1", "text": "Appendix proof", "source_type": "paper"})
        self.plan["scope"]["excluded_units"].append({"unit_id": "a1", "reason": "Appendix"})
        self.plan["appendix_unit_ids"] = ["a1"]
        _, screen = project(self.inp, self.plan, "screen")
        self.assertEqual(screen["scope"]["main_unit_ids"], ["u1", "u2"])
        self.assertEqual(screen["task"]["appendix_unread_unit_ids"], ["a1"])
        with self.assertRaises(ValueError):
            project(self.inp, self.plan, "evidence", appendix_ids=["a1"])
        source, selected = project(self.inp, self.plan, "evidence", appendix_ids=["a1"], request_reason="Proof prerequisite")
        agent.workflow.validate_plan(source, selected, read(ROOT / "runtime/references/workflow-output.schema.json"),
                                    agent.workflow.validator_class(ROOT / "runtime"))
        self.assertIn("a1", selected["scope"]["main_unit_ids"])
        self.assertEqual(source["papers"][0]["units"][-1]["source_type"], "paper")

    def test_wrong_measurement_is_rejected_without_changing_quotation(self):
        inp = read(ROOT / "runtime/references/example.input.json")
        out = read(ROOT / "runtime/references/example.output.json")
        self.assertEqual(validate(inp, out), [])
        fact = next(f for f in out["papers"][0]["facts"] if f["fact_id"] == "f4")
        fact["observation"].update(value=1, raw_value="1 ms")
        self.assertTrue(any("measurement" in e or "numeric" in e for e in validate(inp, out)))

    def test_full_assembly_on_demand_read_and_cross_scope_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inp, manifest = project(self.inp, self.plan)
            agent.workflow.dump(root / "input.json", inp)
            agent.workflow.dump(root / "plan.json", manifest)
            first = FixtureTransport()
            runner = agent.AgentRunner(input_path=root / "input.json", manifest_path=root / "plan.json", out=root / "one",
                shared_cache=root / "cache", execution_mode="synthetic_fixture", transport=first, quiet=True)
            result = runner.run()
            self.assertTrue(result["ok"], result["failures"])
            self.assertTrue((root / "one/paper-record.json").exists())
            self.assertEqual(len(first.prompts), len(runner.specs) + 1)
            assessment = next(p for p in first.prompts if '"stage_id":"assessment"' in p)
            task = json.JSONDecoder().raw_decode(assessment.split("TASK AND ORIGINAL SOURCES:\n")[1])[0]
            self.assertEqual(task["owned_original_units"], [])
            self.assertTrue(task["source_index"])
            # Adding unrelated excluded material must not rerun unchanged stage scopes.
            inp["papers"][0]["units"].append({"unit_id": "notice", "text": "Unrelated copyright notice"})
            manifest["scope"]["excluded_units"].append({"unit_id": "notice", "reason": "Copyright"})
            agent.workflow.dump(root / "input2.json", inp)
            agent.workflow.dump(root / "plan2.json", manifest)
            second = FixtureTransport()
            other = agent.AgentRunner(input_path=root / "input2.json", manifest_path=root / "plan2.json", out=root / "two",
                shared_cache=root / "cache", execution_mode="synthetic_fixture", transport=second, quiet=True)
            result2 = other.run()
            self.assertTrue(result2["ok"], result2["failures"])
            self.assertEqual(second.prompts, [])
            self.assertEqual(len(result2["cache_hit_stage_ids"]), len(other.specs))
            # Repair only an owned page and its consumers; independent references/metadata survive.
            owner = next(s.stage_id for s in other.specs if s.kind == "page")
            repair = repair_plan(other.specs, [{"issue_id": "i1", "kind": "extraction", "stage_id": owner, "reason": "Wrong attribution"}])
            self.assertNotIn("metadata", repair["rerun_stage_ids"])
            self.assertIn("reading", repair["rerun_stage_ids"])
            exhausted = repair_plan(other.specs, [{"issue_id": "i1", "kind": "extraction", "stage_id": owner, "reason": "Wrong attribution"}], counts={"i1": 2})
            self.assertFalse(exhausted["rerun_stage_ids"])
            self.assertTrue(exhausted["pending"])

    def test_lookup_reports_budget_gap_without_truncating_a_unit(self):
        found = lookup(self.inp, self.plan, unit_ids=["u1", "u2"], max_chars=len(self.inp["papers"][0]["units"][0]["text"]))
        self.assertTrue(found["budget_exhausted"])
        self.assertEqual(found["remaining_unit_ids"], ["u2"])
        self.assertEqual(found["units"][0], self.inp["papers"][0]["units"][0])


if __name__ == "__main__":
    unittest.main()
