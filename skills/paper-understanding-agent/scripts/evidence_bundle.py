"""Export task-scoped facts and a review queue; never turn a renderer into a verifier."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "runtime/scripts"))
from evidence_checks import measurement_errors


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def fact_fingerprint(paper, fact, evidence, units):
    return digest({"paper": paper, "fact": fact, "evidence": [evidence[e] for e in fact["evidence_ids"]],
                   "original_units": [units[u] for u in sorted({evidence[e]["unit_id"] for e in fact["evidence_ids"]})]})


def export_bundle(inp, stages, task=None, reviews=None, provenance=None):
    source = inp["papers"][0]
    identity = {k: source[k] for k in ("paper_id", "document_version_id")}
    units = {u["unit_id"]: u for u in source["units"]}
    evidence, facts, metadata, products = {}, {}, {}, {}
    read_ids = set()
    for stage in stages:
        if any(stage.get(k) != identity[k] for k in identity):
            raise ValueError("Stage identity differs from source")
        read_ids.update(stage["source_unit_ids"] + stage.get("context_unit_ids", []))
        for field, key, bank in (("evidence", "evidence_id", evidence), ("facts", "fact_id", facts)):
            for row in stage[field]:
                if row[key] in bank and bank[row[key]] != row:
                    raise ValueError("Conflicting " + key)
                bank[row[key]] = deepcopy(row)
        if stage["kind"] == "metadata":
            metadata = stage["data"]["metadata"]
        products[stage["stage_id"]] = stage["data"]
    errors = []
    for ev in evidence.values():
        unit = units.get(ev["unit_id"])
        if not unit or ev["quote"] not in unit["text"]:
            errors.append("Invalid source span: " + ev["evidence_id"])
        elif ev["unit_id"] not in read_ids:
            errors.append("Evidence outside task scope: " + ev["evidence_id"])
    for fact in facts.values():
        if not fact["evidence_ids"] or not set(fact["evidence_ids"]) <= evidence.keys():
            errors.append("Unresolved evidence: " + fact["fact_id"])
        else:
            errors.extend(measurement_errors(fact, evidence))
    if errors:
        raise ValueError("; ".join(errors))
    review_rows = (reviews or {}).get("reviews", [])
    if len({r["fact_id"] for r in review_rows}) != len(review_rows):
        raise ValueError("Duplicate fact review")
    review_map = {r["fact_id"]: r for r in review_rows}
    if not review_map.keys() <= facts.keys():
        raise ValueError("Review references unknown fact")
    checks, queue = [], []
    for fact in facts.values():
        fingerprint = fact_fingerprint(identity, fact, evidence, units)
        review = review_map.get(fact["fact_id"])
        if review:
            if review.get("fact_sha256") != fingerprint:
                raise ValueError("Stale review: " + fact["fact_id"])
            if review.get("status") not in {"supported", "unsupported", "uncertain"} or not review.get("reason"):
                raise ValueError("Review needs status and reason")
            if not review.get("reviewer") or not review.get("checked_fields"):
                raise ValueError("Review needs reviewer and checked_fields")
        checks.append({"fact_id": fact["fact_id"], "fact_sha256": fingerprint,
                       "source_status": "valid", "support_status": review["status"] if review else "unreviewed",
                       "review": review})
        if not review or review["status"] != "supported":
            ids = {evidence[e]["unit_id"] for e in fact["evidence_ids"]}
            queue.append({"fact": fact, "fact_sha256": fingerprint,
                          "evidence": [evidence[e] for e in fact["evidence_ids"]],
                          "original_units": [units[u] for u in units if u in ids],
                          "check": ["claim support", "subject/baseline attribution", "numbers and units", "conditions and qualifiers"]})
    return {"schema_version": "paper-evidence/1", "paper": identity, "paper_key": digest(identity),
            "metadata": metadata, "sources": [units[u] for u in units if u in read_ids],
            "evidence": list(evidence.values()), "facts": list(facts.values()), "products": products,
            "coverage": {"source_coverage": source["coverage"], "scoped_unit_ids": [u for u in units if u in read_ids],
                         "task": task or {}, "claim": "scoped extraction; unrequested/unread material is not absent"},
            "verification": {"mechanical_ok": True, "facts": checks, "review_queue": queue,
                             "semantic_guarantee": False}, "provenance": provenance or {}}


def from_run(run_dir, reviews=None):
    run_dir = Path(run_dir)
    report = load(run_dir / "runner-report.json")
    if not report["ok"]:
        raise ValueError("Cannot export a failed run as accepted evidence")
    stages = [load(run_dir / "stages" / (sid + ".json")) for sid in report["completed_stage_ids"]]
    plan = load(run_dir / "plan.source.json")
    return export_bundle(load(run_dir / "input.json"), stages, plan.get("task"), reviews,
                         {"input_sha256": report["input_sha256"], "execution_mode": report["execution_mode"],
                          "stage_ids": report["completed_stage_ids"], "cache_hit_stage_ids": report["cache_hit_stage_ids"]})


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", required=True, type=Path)
    ap.add_argument("--reviews", type=Path)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()
    protected = {args.run / name for name in ("input.json", "plan.source.json", "runner-plan.json", "runner-report.json", "paper-record.json")}
    protected.update((args.run / "stages").glob("*.json"))
    if args.reviews:
        protected.add(args.reviews)
    if args.output.resolve() in {p.resolve() for p in protected}:
        raise ValueError("Evidence export cannot overwrite sources, stages, run records or supplied reviews")
    bundle = from_run(args.run, load(args.reviews) if args.reviews else None)
    args.output.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "facts": len(bundle["facts"]), "pending_review": len(bundle["verification"]["review_queue"])}))


if __name__ == "__main__":
    main()
