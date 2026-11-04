"""Audit paper-to-topic evidence bindings and plan bounded gap-directed discovery."""
import argparse
import hashlib
import json
from pathlib import Path


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def pointer(data, path):
    if not path.startswith("/"):
        raise ValueError("Binding needs a JSON pointer")
    value = data
    for part in path[1:].split("/"):
        part = part.replace("~1", "/").replace("~0", "~")
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value


def material_fields(topic):
    """Known scientific fields; narrative classification still belongs to the author/reviewer."""
    for i, branch in enumerate(topic.get("branches", [])):
        root = f"/branches/{i}"
        for field in ("case", "synthesis"):
            if branch.get(field):
                yield root + "/" + field
        for j, paper in enumerate(branch.get("papers", [])):
            prefix = root + f"/papers/{j}"
            for field in ("method", "boundary"):
                if paper.get(field):
                    yield prefix + "/" + field
            for k, _ in enumerate(paper.get("steps", [])):
                yield prefix + f"/steps/{k}"
            for k, row in enumerate(paper.get("results", [])):
                for field in ("conditions", "metric", "result", "baseline", "change"):
                    if row.get(field):
                        yield prefix + f"/results/{k}/{field}"


def comparison_status(left, right, cross_paper=True):
    fields = ("task", "dataset", "split", "metric", "unit", "direction")
    if not left or not right:
        return "insufficient", ["missing measurements"]
    missing = [f for f in fields if left.get(f) is None or right.get(f) is None]
    different = [f for f in fields if left.get(f) != right.get(f)]
    lc = {c["name"]: c["value"] for c in left.get("conditions", [])}
    rc = {c["name"]: c["value"] for c in right.get("conditions", [])}
    if cross_paper:
        missing += [f for f in ("model", "compute_budget", "evaluation_protocol") if not lc.get(f) or not rc.get(f)]
    if not lc or not rc:
        missing.append("conditions")
    if lc != rc:
        different.append("conditions")
    if missing:
        return "insufficient", sorted(set(missing))
    if different:
        return "not_comparable", different
    return "comparable", []


def read_bundles(research, base):
    bundles = {}
    for item in research.get("papers", []):
        path = (base / item["bundle"]).resolve()
        if not path.is_relative_to(base.resolve()):
            raise ValueError("Bundle must be inside the research directory")
        bundle = load(path)
        key = bundle["paper_key"]
        if bundle.get("schema_version") != "paper-evidence/1" or key != digest(bundle["paper"]):
            raise ValueError("Invalid paper evidence identity")
        if key in bundles or item["paper_key"] != key:
            raise ValueError("Duplicate/mismatched paper key")
        sources = {u["unit_id"]: u for u in bundle["sources"]}
        evidence = {e["evidence_id"]: e for e in bundle["evidence"]}
        facts = {f["fact_id"]: f for f in bundle["facts"]}
        if len(sources) != len(bundle["sources"]) or len(evidence) != len(bundle["evidence"]) or len(facts) != len(bundle["facts"]):
            raise ValueError("Duplicate evidence identifiers")
        for ev in evidence.values():
            if ev["unit_id"] not in sources or ev["quote"] not in sources[ev["unit_id"]]["text"]:
                raise ValueError("Broken evidence span in bundle")
        checks = {c["fact_id"]: c for c in bundle["verification"]["facts"]}
        for fid, fact in facts.items():
            if not fact["evidence_ids"] or not set(fact["evidence_ids"]) <= evidence.keys():
                raise ValueError("Unresolved fact evidence")
            fingerprint = digest({"paper": bundle["paper"], "fact": fact,
                                  "evidence": [evidence[e] for e in fact["evidence_ids"]],
                                  "original_units": [sources[u] for u in sorted({evidence[e]["unit_id"] for e in fact["evidence_ids"]})]})
            if checks.get(fid, {}).get("fact_sha256") != fingerprint:
                raise ValueError("Stale fact verification")
        bundles[key] = {"bundle": bundle, "facts": facts, "checks": checks}
    return bundles


def claim_fingerprint(claim, bundles):
    return digest({"claim": {k: v for k, v in claim.items() if k != "review"},
                   "support_versions": [{**r, "fact_sha256": bundles[r["paper_key"]]["checks"][r["fact_id"]]["fact_sha256"]}
                                        for r in claim.get("supports", [])]})


def audit(research, topic, base):
    errors, comparisons, review_queue = [], [], []
    if research.get("schema_version") != "topic-research/1":
        raise ValueError("Expected topic-research/1")
    bundles = read_bundles(research, Path(base))
    claims = {c["claim_id"]: c for c in research.get("claims", [])}
    if len(claims) != len(research.get("claims", [])):
        errors.append("Duplicate topic claim ID")
    candidates = research.get("candidates", [])
    if len({c["candidate_id"] for c in candidates}) != len(candidates):
        errors.append("Duplicate candidate ID")
    for candidate in candidates:
        if candidate.get("status") not in {"included", "pending", "excluded"} or not candidate.get("reason"):
            errors.append("Candidate requires inclusion state and reason")
    bindings = research.get("bindings", {})
    active_claims = set(bindings.values())
    for cid, claim in claims.items():
        if cid not in active_claims:
            continue
        kind = claim.get("kind")
        if kind not in {"report", "synthesis", "comparison", "teaching", "relation"} or not claim.get("text"):
            errors.append("Invalid claim: " + cid)
            continue
        references = claim.get("supports", [])
        if not references:
            errors.append("Claim lacks evidence: " + cid)
        for ref in references:
            info = bundles.get(ref.get("paper_key"), {})
            if ref.get("fact_id") not in info.get("facts", {}):
                errors.append("Unknown fact on " + cid)
            elif info["checks"][ref["fact_id"]]["support_status"] != "supported":
                errors.append("Unreviewed/unsupported fact on " + cid)
        if kind in {"synthesis", "relation"} and len({r["paper_key"] for r in references}) < 2:
            errors.append("Cross-paper claim requires at least two paper versions: " + cid)
        exact_report = kind == "report" and len(references) == 1 and (
            bundles.get(references[0].get("paper_key"), {}).get("facts", {}).get(references[0].get("fact_id"), {}).get("text") == claim["text"])
        if not exact_report:
            try:
                fingerprint = claim_fingerprint(claim, bundles)
            except KeyError:
                continue
            review = claim.get("review", {})
            if review.get("claim_sha256") != fingerprint or review.get("status") != "supported" or not review.get("reason") or not review.get("reviewer"):
                errors.append("Topic inference needs its own current support review: " + cid)
                review_queue.append({"claim_id": cid, "claim_sha256": fingerprint, "claim": claim,
                                     "instruction": "Verify inference, comparison conditions and scope against supporting facts and original sources"})
        if kind == "relation" and claim.get("relation") not in {"adopts", "extends", "compares", "complements", "different_constraints"}:
            errors.append("Relation needs an explicit supported type: " + cid)
        if kind == "comparison":
            pair = claim.get("measurements", [])
            if len(pair) != 2 or pair[0] == pair[1] or any(r not in references for r in pair):
                errors.append("Comparison needs two supported measurement refs: " + cid)
                continue
            try:
                observations = [bundles[r["paper_key"]]["facts"][r["fact_id"]].get("observation") for r in pair]
                status, reasons = comparison_status(*observations, cross_paper=pair[0]["paper_key"] != pair[1]["paper_key"])
            except KeyError:
                continue
            comparisons.append({"claim_id": cid, "status": status, "reasons": reasons})
            if status != "comparable":
                errors.append("Unconditional numeric comparison is not supported: " + cid + " (" + status + ")")
    bindings = research.get("bindings", {})
    for path in material_fields(topic):
        cid = bindings.get(path)
        if cid not in claims:
            errors.append("Missing evidence binding: " + path)
        elif pointer(topic, path) != claims[cid]["text"]:
            errors.append("Bound text differs from reviewed claim: " + path)
        elif path.endswith("/case") and claims[cid]["kind"] != "teaching":
            errors.append("Running example must be labelled teaching: " + path)
        elif path.endswith("/change") and claims[cid]["kind"] != "comparison":
            errors.append("Derived comparison must use comparison claim: " + path)
    included = {c.get("paper_key") for c in candidates if c.get("status") == "included"}
    for i, branch in enumerate(topic.get("branches", [])):
        for j, paper in enumerate(branch.get("papers", [])):
            if paper.get("paper_key") not in included:
                errors.append("Published entry must be an included candidate: " + paper.get("id", "?"))
            prefix = f"/branches/{i}/papers/{j}/"
            for path, cid in bindings.items():
                if path.startswith(prefix) and cid in claims and paper.get("paper_key") not in {r["paper_key"] for r in claims[cid].get("supports", [])}:
                    errors.append("Entry attributes another paper's claim: " + path)
            if paper.get("paper_key") not in bundles:
                errors.append("Topic entry lacks a fixed paper_key: " + paper.get("id", "?"))
    return {"ok": not errors, "errors": errors, "comparisons": comparisons, "review_queue": review_queue,
            "scope": "Identities, source spans, current support reviews, bound fields and comparison conditions; no scientific truth guarantee"}


def plan_gaps(research):
    budget = research.get("search_budget", {})
    history = research.get("search_history", [])
    rounds = {r["round_id"] for r in history}
    remaining = max(0, int(budget.get("max_queries", 0)) - len(history))
    can_search = research.get("source_policy") == "web" and len(rounds) < int(budget.get("max_rounds", 0)) and remaining > 0
    seen = {r["query"].strip().casefold() for r in history}
    gaps = sorted((g for g in research.get("gaps", []) if g.get("status") == "open"), key=lambda g: g.get("priority", 99))
    tasks = []
    for gap in gaps:
        query = gap.get("question", "").strip()
        if can_search and query and query.casefold() not in seen and len(tasks) < remaining:
            tasks.append({"gap_id": gap["gap_id"], "query": query, "reason": gap.get("reason", ""), "action": "discover_candidates_then_screen"})
            seen.add(query.casefold())
    return {"tasks": tasks, "remaining_queries": remaining,
            "stop_reason": None if tasks else ("local_only" if research.get("source_policy") != "web" else "budget_exhausted_or_no_new_gap"),
            "unresolved_gap_ids": [g["gap_id"] for g in gaps], "complete_topic": False}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)
    check = sub.add_parser("audit")
    check.add_argument("--research", type=Path, required=True)
    check.add_argument("--topic", type=Path, required=True)
    gaps = sub.add_parser("gaps")
    gaps.add_argument("--research", type=Path, required=True)
    for parser in (check, gaps):
        parser.add_argument("--output", type=Path)
    args = ap.parse_args()
    research = load(args.research)
    result = audit(research, load(args.topic), args.research.parent) if args.command == "audit" else plan_gaps(research)
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        if args.output.resolve() in {p.resolve() for p in (args.research, getattr(args, "topic", None)) if p}:
            raise ValueError("Output cannot overwrite research/topic inputs")
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0 if result.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
