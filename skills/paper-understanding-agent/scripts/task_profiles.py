"""Project a reviewed paper scope into screen/evidence/full tasks without losing sources."""
from copy import deepcopy


MODES = ("screen", "evidence", "full")


def project(inp, manifest, mode="full", unit_ids=(), appendix_ids=(), request_reason=None):
    if mode not in MODES:
        raise ValueError("Unknown task mode")
    source, plan = deepcopy(inp), deepcopy(manifest)
    paper, scope = source["papers"][0], plan["scope"]
    units = {u["unit_id"]: u for u in paper["units"]}
    body = list(scope["main_unit_ids"])
    excluded = {u["unit_id"]: u["reason"] for u in scope["excluded_units"]}
    # Appendix ownership is explicitly declared; a heading heuristic is never approval.
    declared_appendix = set(plan.get("appendix_unit_ids", []))
    if not declared_appendix <= set(excluded):
        raise ValueError("appendix_unit_ids must identify retained excluded units")
    if not set(appendix_ids) <= declared_appendix:
        raise ValueError("Requested appendix units must be declared in appendix_unit_ids")
    if appendix_ids and not (request_reason or "").strip():
        raise ValueError("Appendix activation requires --request-reason")
    if not set(unit_ids) <= set(body):
        raise ValueError("--unit-id must select declared body units; use --appendix-unit-id for appendices")
    if any(units[u].get("source_type", "paper") != "paper" for u in appendix_ids):
        raise ValueError("Appendix evidence must belong to this paper")

    abstract_ids = [s["unit_id"] for s in scope["original_abstract_spans"]]
    metadata_ids = list(scope.get("metadata_source_unit_ids", []))
    if not metadata_ids:
        # A reviewed frontmatter group is preferred; otherwise only the first declared page.
        front = [g for g in scope["sections"] if g["section_id"].lower() in {"frontmatter", "metadata"}]
        metadata_ids = [u for g in front for u in g["unit_ids"]]
        if not metadata_ids and scope["pages"]:
            metadata_ids = list(scope["pages"][0]["unit_ids"])
        metadata_ids += abstract_ids + scope.get("metadata_unit_ids", [])
    metadata_ids = list(dict.fromkeys(metadata_ids))
    if not set(metadata_ids) <= set(body + scope.get("metadata_unit_ids", [])):
        raise ValueError("Metadata scope must be inside body/metadata units")
    selected = set(unit_ids) if unit_ids else (set(plan.get("screen_unit_ids", metadata_ids)) if mode == "screen" else set(body))
    if not selected <= set(body + scope.get("metadata_unit_ids", [])):
        raise ValueError("Screen source scope is not inside this paper")
    selected.update(u for u in metadata_ids if u in body)
    selected.update(abstract_ids)
    selected.update(appendix_ids)
    active = [u for u in body if u in selected] + list(dict.fromkeys(appendix_ids))
    scope["main_unit_ids"] = active
    scope["metadata_source_unit_ids"] = metadata_ids
    scope["excluded_units"] = [u for u in scope["excluded_units"] if u["unit_id"] not in appendix_ids]
    scope["excluded_units"] += [{"unit_id": u, "reason": "Outside this requested task; retained in canonical input"}
                                for u in body if u not in selected]
    for field in ("pages", "sections"):
        scope[field] = [{**g, "unit_ids": [u for u in g["unit_ids"] if u in selected]}
                        for g in scope[field] if any(u in selected for u in g["unit_ids"])]
    appendix_order = [u for u in units if u in set(appendix_ids)]
    appendix_pages = {}
    for uid in appendix_order:
        page_id = "appendix-page-" + str(units[uid].get("locator", {}).get("page", uid))
        appendix_pages.setdefault(page_id, []).append(uid)
    scope["pages"] += [{"page_id": pid, "unit_ids": ids} for pid, ids in appendix_pages.items()]
    owned = set()
    for group in plan.get("appendix_sections", []):
        ids = [u for u in group["unit_ids"] if u in appendix_order]
        if set(ids) & owned:
            raise ValueError("Appendix section groups overlap")
        if ids:
            scope["sections"].append({"section_id": "appendix-" + group["section_id"], "title": group["title"], "unit_ids": ids})
            owned.update(ids)
    remaining = [u for u in appendix_order if u not in owned]
    if remaining:
        scope["sections"].append({"section_id": "appendix-requested", "title": "Requested appendix evidence", "unit_ids": remaining})
    unread = [u for u in plan.get("appendix_unit_ids", []) if u not in appendix_ids]
    source["options"]["profile"] = "comprehensive"  # Runtime envelope; task completion is reported separately.
    if mode == "full" and (set(body) - selected or unread):
        paper["coverage"] = "partial"
    plan["task"] = {"mode": mode, "body_available_unit_ids": body, "body_selected_unit_ids": [u for u in body if u in selected],
                    "appendix_indexed_unit_ids": plan.get("appendix_unit_ids", []),
                    "appendix_selected_unit_ids": list(dict.fromkeys(appendix_ids)), "appendix_unread_unit_ids": unread,
                    "request_reason": request_reason, "not_read_is_not_absent": True}
    # The projected manifest no longer classifies activated appendix units as excluded.
    plan["appendix_unit_ids"] = unread
    return source, plan


def default_stages(mode):
    return {"screen": ["metadata", "page"], "evidence": ["understanding"], "full": None}[mode]


def repair_plan(specs, issues, limit=2, counts=None):
    """Route source/semantic problems and invalidate only the dependency closure."""
    counts = counts or {}
    ids = {s.stage_id for s in specs}
    selected, pending, routes = set(), [], []
    for issue in issues:
        if not issue.get("issue_id") or not issue.get("reason"):
            raise ValueError("Each issue requires issue_id and reason")
        kind, sid = issue.get("kind"), issue.get("stage_id")
        if kind not in {"parse", "visual", "source_missing", "extraction", "unsupported", "comparison"}:
            raise ValueError("Unknown repair issue kind")
        if kind in {"parse", "visual", "source_missing", "comparison"}:
            routes.append({**issue, "action": {"parse": "reparse_source", "visual": "inspect_page_image",
                           "source_missing": "retain_pending_or_search", "comparison": "revise_topic_comparison"}[kind]})
            continue
        if sid not in ids:
            raise ValueError("Unknown repair stage: " + str(sid))
        if counts.get(issue["issue_id"], 0) >= limit:
            pending.append({**issue, "action": "budget_exhausted_keep_pending"})
        else:
            selected.add(sid)
            routes.append({**issue, "action": "rerun_stage"})
    changed = True
    while changed:
        previous = set(selected)
        selected.update(s.stage_id for s in specs if set(s.dependencies) & selected)
        changed = previous != selected
    return {"rerun_stage_ids": [s.stage_id for s in specs if s.stage_id in selected],
            "routes": routes, "pending": pending, "max_attempts_per_issue": limit}
