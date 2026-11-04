"""Offline portability and contract checks; no model or gateway calls."""
import argparse
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "runtime" / "scripts"))
import run_agent
import run_workflow
from validate_output import validate
from vpf_transport import DEFAULT_ENDPOINT, VPFTransport
from jsonschema import Draft202012Validator


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


class AgentPortabilityTests(unittest.TestCase):
    def setUp(self):
        self.input = load(ROOT / "examples" / "input.json")
        self.manifest = load(ROOT / "examples" / "manifest.json")
        self.schema = load(ROOT / "runtime" / "references" / "workflow-output.schema.json")

    def test_plan_only_cli_and_dependencies(self):
        result = subprocess.run(
            [sys.executable, "-B", str(ROOT / "scripts" / "run_agent.py"),
             "--input", str(ROOT / "examples" / "input.json"),
             "--manifest", str(ROOT / "examples" / "manifest.json"), "--plan-only"],
            capture_output=True, text=True, check=True,
        )
        plan = json.loads(result.stdout)
        self.assertTrue(plan["ok"])
        self.assertEqual(len(plan["stages"]), 9)
        stages = {stage["stage_id"]: stage for stage in plan["stages"]}
        self.assertEqual(stages["metadata"]["dependencies"], [])
        refs = [s for s in stages.values() if s["kind"] == "references"]
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0]["dependencies"], [])
        self.assertNotIn("assessment", stages["reading"]["dependencies"])
        self.assertEqual(stages["reading"]["specialist"], "paper-brief")

    def test_scope_rejects_missing_input_unit(self):
        bad = copy.deepcopy(self.manifest)
        bad["scope"]["main_unit_ids"].pop()
        with self.assertRaises(run_workflow.WorkflowError):
            run_workflow.validate_plan(self.input, bad, self.schema, Draft202012Validator)

    def test_document_version_mismatch_rejected(self):
        bad = copy.deepcopy(self.manifest)
        bad["document_version_id"] = "different-version"
        with self.assertRaisesRegex(run_workflow.WorkflowError, "identity mismatch"):
            run_workflow.validate_plan(self.input, bad, self.schema, Draft202012Validator)

    def test_all_specialist_resources_resolve(self):
        profiles = [run_agent.read_profile(kind) for kind in run_agent.ROLES]
        self.assertEqual(len(profiles), 7)
        self.assertEqual(len({p["skill"] for p in profiles}), 6)
        for profile in profiles:
            self.assertEqual(len(profile["sha256"]), 64)
            self.assertTrue(all(document["text"].strip() for document in profile["documents"]))

    def test_gateway_requires_explicit_configuration(self):
        self.assertEqual(DEFAULT_ENDPOINT, "")
        with self.assertRaisesRegex(ValueError, "endpoint"):
            VPFTransport(endpoint=DEFAULT_ENDPOINT, service_name="demo", caller_name="demo",
                         model="demo", timeout=1, generation_timeout=1, max_tokens=1)

    def test_bundled_example_output_validates(self):
        refs = ROOT / "runtime" / "references"
        self.assertEqual(validate(load(refs / "example.input.json"), load(refs / "example.output.json")), [])

    def test_bundled_schemas_are_valid(self):
        for name in ("output.schema.json", "workflow-output.schema.json"):
            Draft202012Validator.check_schema(load(ROOT / "runtime" / "references" / name))

    def test_supplemented_specialist_examples(self):
        for name in ("paper-brief", "paper-metadata", "paper-structured-summary", "paper-value-assessment"):
            with self.subTest(skill=name):
                folder = ROOT / "references" / "specialists" / name
                if name == "paper-value-assessment":
                    script = folder / "scripts" / "validate_assessment.py"
                    source = folder / "references" / "example.input.json"
                    output = folder / "references" / "example.output.json"
                else:
                    script = folder / "scripts" / "validate_contract.py"
                    source = folder / "examples" / "input.json"
                    output = folder / "examples" / "output.json"
                result = subprocess.run([sys.executable, "-B", str(script), str(source), str(output)],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_standalone_reference_cli_needs_no_optional_tokenizer_for_help(self):
        script = ROOT / "references" / "specialists" / "paper-reference-extract" / "scripts" / "extract_references.py"
        result = subprocess.run([sys.executable, "-B", str(script), "--help"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
