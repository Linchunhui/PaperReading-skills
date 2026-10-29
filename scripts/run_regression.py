#!/usr/bin/env python3
"""Freeze repeatable generation tasks and verify independent paired review records."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def package_hash(root):
    records = {}
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if any(x in rel.parts for x in (".git", "__pycache__", "evals")):
            continue
        if path.is_file():
            records[str(rel)] = digest(path)
    return records

def prepare(args):
    candidate, baseline, run = map(lambda p: Path(p).resolve(),
                                   (args.candidate, args.baseline, args.run_dir))
    if run.exists():
        raise ValueError("run-dir already exists; use a fresh run directory")
    for root in (candidate, baseline):
        if not (root / "SKILL.md").is_file():
            raise ValueError(f"missing SKILL.md: {root}")
        if root == run or root in run.parents:
            raise ValueError("run-dir must be outside both skill packages")
    cases = json.loads((candidate / "evals/cases.json").read_text(encoding="utf-8"))
    run.mkdir(parents=True)
    shutil.copytree(candidate / "evals/fixtures", run / "fixtures")
    shutil.copy2(candidate / "evals/rubric.json", run / "rubric.json")
    manifest = {"suite_version": 1, "cases": cases, "packages": {},
                "sources": {p.name: digest(p) for p in (run / "fixtures").iterdir()},
                "rubric_sha256": digest(run / "rubric.json")}
    for version, root in (("baseline", baseline), ("candidate", candidate)):
        dest = run / "packages" / version
        shutil.copytree(root, dest, ignore=shutil.ignore_patterns(".git", "__pycache__", "evals"))
        manifest["packages"][version] = package_hash(dest)
        for case in cases:
            folder = run / version / case["id"]
            folder.mkdir(parents=True)
            text = (f"使用 {dest} 中的 $paper-studio。\n"
                    f"{case['prompt']}\n"
                    f"原始材料：{run / 'fixtures' / case['material']}\n"
                    f"将最终产物写入 {folder}，文件stem统一为 {case['id']}。\n"
                    "只读取指定skill及其引用资源和原始材料；不读取同级其他任务或产物。"
                    "这是只用给定材料的独立任务，不需要外部搜索。完成后报告文件位置。\n")
            (folder / "task.md").write_text(text, encoding="utf-8")
    write_json(run / "manifest.json", manifest)
    print(f"Prepared {len(cases) * 2} generation tasks in {run}")

def check(args):
    run = Path(args.run_dir).resolve()
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    rubric = json.loads((run / "rubric.json").read_text(encoding="utf-8"))
    errors, metrics = [], {}
    if digest(run / "rubric.json") != manifest["rubric_sha256"]:
        errors.append("rubric changed after freeze")
    for name, expected in manifest["sources"].items():
        if digest(run / "fixtures" / name) != expected:
            errors.append(f"fixture changed: {name}")
    ids = [c["id"] for c in manifest["cases"]]
    if len(ids) != len(set(ids)):
        errors.append("duplicate case IDs")
    for version in ("baseline", "candidate"):
        if package_hash(run / "packages" / version) != manifest["packages"][version]:
            errors.append(f"{version} package changed after freeze")
        review_path = run / f"{version}-review.json"
        if not review_path.is_file():
            errors.append(f"missing {version} review")
            continue
        review = json.loads(review_path.read_text(encoding="utf-8"))
        if review.get("version") != version or not review.get("evaluator"):
            errors.append(f"invalid {version} review identity")
        rows = review.get("cases", [])
        if sorted(r.get("id", "") for r in rows) != sorted(ids):
            errors.append(f"{version} case set mismatch")
        metrics[version] = {}
        for row in rows:
            cid = row.get("id", "")
            folder = run / version / cid
            hashes = row.get("artifact_hashes", {})
            expected = {f"{cid}.html", f"{cid}.wechat.md"} if cid == "radar" else {f"{cid}.md"}
            if not expected.issubset(hashes):
                errors.append(f"{version}/{cid}: missing required output hashes")
            for rel, expected_hash in hashes.items():
                artifact = (folder / rel).resolve()
                if folder.resolve() not in artifact.parents or not artifact.is_file():
                    errors.append(f"{version}/{cid}: missing or unsafe artifact {rel}")
                elif digest(artifact) != expected_hash:
                    errors.append(f"{version}/{cid}: changed artifact {rel}")
            checks = row.get("checks", {})
            if set(checks) != set(rubric["checks"]):
                errors.append(f"{version}/{cid}: check set mismatch")
            scores = {}
            for name in rubric["checks"]:
                item = checks.get(name, {})
                if type(item.get("pass")) is not bool or not isinstance(item.get("evidence"), str) or not item["evidence"].strip():
                    errors.append(f"{version}/{cid}/{name}: missing verdict or evidence")
                scores[name] = int(item.get("pass") is True)
                if version == "candidate" and not scores[name]:
                    errors.append(f"candidate/{cid}/{name}: failed")
            metrics[version][cid] = scores
    improved = []
    if all(v in metrics for v in ("baseline", "candidate")):
        for cid in ids:
            for name in rubric["checks"]:
                old = metrics["baseline"].get(cid, {}).get(name, 0)
                new = metrics["candidate"].get(cid, {}).get(name, 0)
                if new < old:
                    errors.append(f"regression: {cid}/{name}")
                elif new > old:
                    improved.append(f"{cid}/{name}")
    result = {"passed": not errors, "errors": errors, "improved_checks": improved,
              "interpretation": ("Not accepted; resolve errors before making a quality claim" if errors else
                                 "Observed paired improvement" if improved else
                                 "No observed regression in this suite; no measured gain"),
              "limits": "Verifies review records and artifacts, not semantic truth or general performance.",
              "metrics": metrics}
    write_json(run / "gate.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    for flag in ("baseline", "candidate", "run-dir"):
        prep.add_argument("--" + flag, required=True)
    gate = sub.add_parser("check")
    gate.add_argument("--run-dir", required=True)
    args = parser.parse_args()
    try:
        return prepare(args) or 0 if args.command == "prepare" else check(args)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(2, f"regression error: {exc}\n")

if __name__ == "__main__":
    raise SystemExit(main())
