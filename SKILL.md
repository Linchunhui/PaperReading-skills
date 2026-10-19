---
name: paper-studio
description: "Use whenever the user shares a research paper (arXiv, PDF, paper URL, or title), asks to read, analyze, compare, or consolidate papers, wants an AI research radar/digest/newsletter/recurring paper task, or asks to convert an existing research HTML into concise Markdown for a WeChat Official Account. Supports single, series, digest, radar, and HTML-to-WeChat-Markdown workflows, including the opt-in single-paper teaching feature 跟着 limu 解读 (single-limu). Digest and daily/weekly/monthly radar default to in-depth reading of every included paper, using concrete examples, stepwise mechanisms, and evidence boundaries. Produces a standalone HTML plus a concise `.wechat.md` companion by default; single-paper HTML preserves the source PDF basename exactly."
---

# PaperStudio

Turn research discovery and close reading into durable, self-contained HTML notes plus concise Markdown articles suitable for WeChat Official Account editors. Write for a smart reader who is new to the topic: concrete, conversational, evidence-backed, and detailed enough to recover the paper's core idea months later.

## Route the request

Choose in this order:

1. For an existing `.html` plus “转 Markdown / 公众号版 / 精简发布”, use **HTML-to-WeChat-Markdown**. Read [references/wechat-markdown.md](references/wechat-markdown.md), run the converter, then perform semantic shortening.
2. Honor an explicit `single`, `series`, `digest`, or `radar` mode; `single-limu` means `single` with the limu teaching workflow.
3. Use **radar** for “today/this week/this month, HF Daily Papers, AI daily/weekly/monthly report” without supplied papers.
4. Use **single** for one paper.
5. Use **series** for 2-6 papers with a clear inheritance or evolution line.
6. Use **digest** for 2-12 independent supplied papers.
7. If the relation is unclear, ask whether one can state: “what problem did the previous generation leave, and how did the next generation add, replace, or bypass it?” If yes, use series; otherwise use digest.

Within **single**, enable **跟着 limu 解读** only when requested (for example, “跟着 limu 解读”, “李沐式精读”, or “用 limu 的讲解方式”), or via `single-limu`. Ordinary “精读” keeps the standard single-paper workflow. This is an optional teaching workflow, not a fifth top-level mode; preserve explicit series/digest/radar requests and never reduce a multi-paper request to one paper because it mentions limu.

Always read [references/foundation.md](references/foundation.md) completely, then read the selected mode reference completely:

- Single: [references/single-paper.md](references/single-paper.md). When 跟着 limu 解读 is selected, also read [references/single-paper-limu.md](references/single-paper-limu.md) completely. It contains the built-in teaching method; no separate skill is required.
- Series: [references/series.md](references/series.md)
- Digest: [references/digest.md](references/digest.md) and [references/per-paper-deep-read.md](references/per-paper-deep-read.md), both completely.
- Radar: [references/radar.md](references/radar.md), [references/directions.md](references/directions.md), and [references/per-paper-deep-read.md](references/per-paper-deep-read.md), all completely.

Digest and radar apply the adapted limu teaching method to **every included paper by default**, without changing their multi-paper organization or requiring an extra keyword. The overview may be brief; each paper’s body must recover its problem, method, evidence, cost, and scope. Explicit user requests for a short version override the default; a mode/task title such as “速读” alone does not.

For every route that creates an HTML, also read [references/wechat-markdown.md](references/wechat-markdown.md) and create the concise companion Markdown unless the user explicitly requests HTML only.

Before drawing visuals, also read the relevant templates:

- Single/series: [references/svg-patterns.md](references/svg-patterns.md)
- Digest: [references/layout-patterns.md](references/layout-patterns.md), plus the bar-chart section in `svg-patterns.md`

## Execute the shared workflow

1. Resolve every source and record provenance. For a title or URL, browse to find and verify the primary paper/project page. For a local PDF, inspect the PDF directly. Prefer primary sources for technical claims and numbers.
2. Collect the title, authors, abstract, related-work context, method, key formulas needed to understand the mechanism, main experiments, ablations, limitations, and the figures that carry understanding.
3. Draft the route-specific structure. For 跟着 limu 解读, use the teaching sequence in `references/single-paper-limu.md` in place of the standard single-paper section order while retaining its coverage and delivery rules. Make reasoning visible: show how the evidence supports each conclusion. For digest/radar, complete the shared per-paper deep-read workflow for every included paper, with an example, stepwise transformations, located argument explanations, experimental controls, and a specific recall paragraph. Do not reserve depth for Top picks or compress later papers into short cards. In a paper deep-read, make the method recoverable rather than listing component names: give an end-to-end route, then 4–7 numbered stages that explain state transformations, design reasons, training signals, and inference behavior; use the selected mode reference's depth gate.
4. Copy [assets/style.css](assets/style.css) into the output `<style>` and adapt only the per-paper palette and route-specific needs. Generate accessible, responsive HTML directly with the available HTML/CSS tools.
5. Compress retained raster images, then embed all image dependencies:

   ```bash
   python3 scripts/embed_images.py "{output.html}" --in-place
   ```

6. Validate deterministic delivery rules:

   ```bash
   python3 scripts/validate_html.py "{output.html}" --source-pdf "{source.pdf}"  # single
   python3 scripts/validate_html.py "{output.html}"                              # other modes
   ```

7. Fix every validation failure. Open the final HTML and visually inspect figures, formula rendering, table of contents, accordion behavior, and mobile layout. For a standalone HTML, formulas must render without a remote runtime dependency: use native MathML or a fully embedded renderer.
8. Write `{HTML stem}.wechat.md` from the same evidence. Do not mechanically copy all HTML sections. Follow `references/wechat-markdown.md`: shorten the narrative, keep exact numbers and boundaries, retain only 1–3 load-bearing images, and move links to a final reference list.
9. If starting from an existing HTML, create the deterministic draft first:

   ```bash
   python3 scripts/html_to_markdown.py "{input.html}" --compact
   ```

   Then rewrite the draft semantically into mobile-friendly sections (usually 4–6; multi-paper coverage takes priority) and recheck it against the source HTML.
10. Deliver the validated HTML and `.wechat.md` companion, plus any `.wechat-assets/` directory. Report absolute paths, file sizes, and source coverage/status. Omit the Markdown only when the user explicitly asks for HTML alone.

For periodic radar runs, compute the report key and target filename before discovery. Reuse an existing same-name HTML only when it satisfies the current scope and per-paper depth requirements and no revision is requested; otherwise update the existing path after verifying missing evidence and expanding the content, without creating a duplicate. When the user constrains discovery to HF Daily Papers, treat that dated HF set as a hard candidate boundary and use arXiv/PDF/project pages only for verification. If HF date coverage must fall back, disclose the actual covered date or interval in the report subtitle.

## Preserve deterministic naming

For single-paper mode with a PDF, derive the output mechanically:

```python
html_path = pdf_path.with_suffix(".html")
```

Preserve spaces, punctuation, capitalization, and multiple dots. Do not slugify, translate, or replace the basename with a method name. Download URL/arXiv PDFs first, then derive the HTML path from that downloaded PDF.

For combined outputs, use:

- Series: `{series-name}.html`
- Digest: `{YYYY-MM-DD}-digest.html`
- Daily radar: `{YYYY-MM-DD}-radar.html` plus same-name `.json`
- Weekly radar: `{YYYY}-W{WW}-radar.html` plus same-name `.json`
- Monthly radar: `{YYYY}-M{M}-radar.html` plus same-name `.json`

The `.json` is a working provenance manifest, not a mandatory public artifact. If the user requests HTML only, keep discovery/intermediate manifests in a temporary directory and deliver only the HTML.

For every HTML above, name the companion `{HTML stem}.wechat.md`. When Markdown images are needed, store them in `{HTML stem}.wechat-assets/` beside the Markdown.

## Keep every image self-contained

Require every `<img src>`, SVG `<image href>`, `<source src/srcset>`, and CSS image URL to be a valid `data:image/...;base64,...` URI. Inline SVG is allowed. Ordinary source/PDF/project links may remain external `<a href>` links. Never deliver an HTML file with local, `file://`, or remote image dependencies.

The Markdown companion follows a different portability rule: do not embed base64. Extract 1–3 retained images into `.wechat-assets/` and use relative Markdown image paths so doocs/md, Wenyan, or another publisher can upload them.

## Enforce the writing red lines

1. Rewrite anything one would not say while explaining the work to a friend.
2. Explain each necessary term at first use in practical language.
3. Prefer short, concrete words over academic padding.
4. Let each sentence advance one idea.
5. Use visible nouns and active verbs.
6. Open Motivation with a concrete reason to care.
7. Delete filler such as “in recent years” and “it is worth noting.”
8. Trust the reader; do not repeat the same conclusion three ways.
9. State weaknesses, missing evidence, and uncertainty honestly.
10. Keep the key formulas that materially improve understanding of the paper's mechanism, objective, state update, routing, or inference rule. Follow every displayed formula immediately with a Chinese plain-language translation that explains symbols, optimization direction, and design intent. Do not add decorative formulas merely for a more technical appearance.
11. Make the problem, mechanism, and finding recoverable in 30 seconds six months later.
12. Prefer understanding over brevity; expand prerequisites when the reader needs them.

Also apply four principles: keep one concrete Motivation anchor throughout; expose the inference chain; show transformations rather than only definitions; and turn implications into executable actions when a real project connection exists.

## Protect evidence integrity

- Trace every reported number to a specific table, figure, or primary project page. Preserve the exact precision printed by the source.
- Distinguish open-source and closed-source comparison groups and whether higher or lower is better.
- Use an existing same-paper HTML note to preserve narrative consistency, but verify paper identity and all load-bearing numbers against the primary source.
- Do not present media summaries as paper claims. In radar mode, use media for discovery/context and primary papers/project pages for technical evidence.
- Keep direct quotations short and necessary. Prefer paraphrase; do not reproduce long copyrighted passages.
- Do not invent missing architecture details, dimensions, training data, results, or limitations. Label inference as inference.

## Run radar discovery

Run from the skill directory:

```bash
python3 scripts/fetch_content.py --range today -o /tmp/paperstudio-radar.json
python3 scripts/fetch_content.py --range week --top-k 40 -o /tmp/paperstudio-radar.json
python3 scripts/fetch_content.py --range month --all-items -o /tmp/paperstudio-radar.json
```

Treat `matched_directions` as broad recall only. Apply `references/directions.md` semantically, fill `keep`, `primary_direction`, `secondary_directions`, `why_match`, `why_read`, `evidence_level`, and `drop_reason`, and merge duplicate coverage into one card. Preserve explicit `ok`, `not_configured`, or `error` status for every requested source.

When the user requests a recurring task, create an automation if available using the complete task prompt in `references/radar.md`; otherwise provide a scheduler/cron command. Use the user's timezone, falling back to the current environment timezone.

## Final acceptance gate

Before delivery, verify:

- Every digest/radar paper passes `references/per-paper-deep-read.md`; all user-specified papers are covered, later papers retain full depth, and unavailable-source items are not counted as completed deep reads.
- The route-specific structure and optional-section thresholds pass. For 跟着 limu 解读, also pass the teaching checklist in `references/single-paper-limu.md`: one concrete problem, a recoverable method route, located paragraph explanations, and bounded experimental claims.
- Every formula renders and has an immediate plain-language translation.
- Every deep-read card is independently understandable: the reader can recover the input-to-output method route, separate training from inference, locate at least one main result and one ablation/diagnostic result, and understand any key formula without opening the paper first.
- Every retained screenshot is complete, legible, compressed, and discussed in the text.
- Every SVG number matches its cited source and every marker ID is unique within the page.
- `embed_images.py` and `validate_html.py` pass.
- The final HTML works as a standalone file on desktop and mobile.
- The `.wechat.md` has clear sections (usually 4–6 for single/series; grouped by paper/topic for digest/radar), short mobile paragraphs, exact numbers, 1–3 images at most, no base64, no sidebar TOC/Q&A, and a final reference list.
- The Markdown previews cleanly in a standard WeChat Markdown editor such as doocs/md or Wenyan; project-specific extension syntax is optional, never the default.

Do not call a result complete while any HTML image is external, a formula is visibly broken, a required source is silently missing, a single-paper filename differs from its PDF basename, or the Markdown is merely a full HTML text dump without semantic shortening.
