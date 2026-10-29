---
name: paper-studio
description: "Read and explain research papers, connect work within one direction, and discover papers through daily/weekly/monthly research radars. Three modes only: single, series, radar; single combines structured analysis with original limu-inspired teaching by default; single-limu is a compatibility alias. Every formal paper body covers background, direction, problem, approach, concrete method, main results, ablation/analysis conclusions, and summary, with depth adapted to the mode. Produces self-contained HTML and a concise WeChat Markdown companion unless the user requests another format; also converts existing research HTML to WeChat Markdown."
---

# PaperStudio

Explain papers so readers can recover the actual method, judge its evidence, and identify where it may be useful months later. Use three modes: **单篇精读 / 同方向串讲 / 雷达发现**. Preserve each paper's storyline; vary explanation depth rather than dropping information.

## Route the request

1. Honor explicit `single`, `series`, or `radar`. `single-limu` is a compatibility alias for the same merged single workflow, not a separate mode.
2. One supplied paper → **single**. Merge structured coverage with limu-inspired examples, mechanism walkthroughs and evidence reasoning by default.
3. Multiple supplied papers addressing a common direction, task or research question → **series**. Explain evolution, competing solutions, complementary components or different constraints; do not require or invent direct inheritance. No fixed paper-count ceiling.
4. Discovery requests such as “latest/this week/this month/HF Daily Papers” → **radar**, even if the report covers only one direction.
5. Supplied papers from unrelated directions → **radar with supplied candidates**, organized by direction. Preserve the requested set; external discovery is not implied by this route. Use available primary sources to verify content unless the user limits analysis to provided material.
6. Retire `digest` / 随笔 as a mode. For a legacy request, route by the supplied material using rules 3–5 and state the chosen current mode; do not create a digest report or ask the user to choose a retired mode.

An existing HTML plus “转 Markdown / 公众号版 / 精简发布” uses the conversion workflow below. This is a delivery operation, not a fourth reading mode. Preserve explicit chapter scope, interaction style and output format; a request for chat-only analysis does not require files.

## Read the shared and mode instructions

Always read [references/foundation.md](references/foundation.md) and [references/paper-storyline.md](references/paper-storyline.md) completely. The shared storyline defines eight content obligations for every formal paper body:

**背景 → 方向/任务 → 问题与前作缺口 → 解决思路 → 具体方法 → 主结果 → 消融或分析结论 → 带条件总结。**

Then read the selected references completely:

- **Single:** [references/single-paper.md](references/single-paper.md), the unified structured and teaching workflow.
- **Series:** [references/series.md](references/series.md) and [references/per-paper-deep-read.md](references/per-paper-deep-read.md).
- **Radar:** [references/radar.md](references/radar.md), [references/directions.md](references/directions.md), and [references/per-paper-deep-read.md](references/per-paper-deep-read.md).
- **HTML creation/conversion:** [references/wechat-markdown.md](references/wechat-markdown.md), unless the user requests HTML only.
- **Visuals:** [references/svg-patterns.md](references/svg-patterns.md) for SVGs; [references/layout-patterns.md](references/layout-patterns.md) for multi-paper navigation and body layout.

Single expands mechanisms, examples, formulas and experimental reasoning. Series focuses on relationships around a shared question. Radar gives compact but complete explanations. Separate approach from concrete method and main results from ablation conclusions. Every paper has its own summary; navigation cards and the report-level recap do not replace it.

Do not set default total/per-paper word, screen or method-step quotas. Let complexity and the user's requested depth determine length. Finish the understanding chain, then remove repetition and peripheral detail. Never divide a total budget across papers, shorten later papers, or omit selected papers to finish a batch. Explicit requests for short versions or abstract-only output take priority; label their scope.

## Execute the workflow

1. Verify paper identity/version and record source coverage. Resolve titles/URLs through primary paper/project pages; inspect supplied PDFs or parsed material. Honor user source boundaries. Generated summaries remain upstream records, not proof that the original paper was checked.
2. Build one lightweight reading record: eight storyline items, major claims and source positions, figures/formulas, main comparisons, ablation/diagnostic conclusions, costs, and missing evidence. Reuse it across summary and narrative views; do not require a separate JSON deliverable.
3. Write the method and evidence before the abstract, reading recommendation and report overview. Explain the input-to-output route and each decisive state transformation. Show training/inference differences when relevant. Use examples and formulas where needed, not to fill a fixed template.
4. Present ablation conclusions separately: what worked, failed, saturated or cost more; preserve the changed factor, important controls, observed result and inference boundary. Distinguish a paper that reports no ablation from unavailable sections and inapplicable paper types.
5. Apply the selected narrative organization. Complete the same eight-part coverage for all formal entries, including those after Top picks. Preserve per-paper summaries and conditional transferable lessons; personal-project actions and extra Insight remain optional.
6. For HTML, inline [assets/style.css](assets/style.css) and adapt the palette/layout. Embed retained images and render necessary formulas offline using native MathML or a fully embedded renderer.
7. Run deterministic delivery checks:

   ```bash
   python3 scripts/embed_images.py "{output.html}" --in-place
   python3 scripts/validate_html.py "{output.html}" --source-pdf "{source.pdf}"  # single
   python3 scripts/validate_html.py "{output.html}"                              # combined
   ```

8. Check each paper's storyline and evidence separately from file validation. Inspect the final figures, formulas, navigation, accordions and mobile layout. Fix failures before delivery.
9. Unless the user requests HTML only, write `{HTML stem}.wechat.md` from the same evidence. Preserve per-paper storyline coverage while removing repetition, navigation and peripheral detail. Keep necessary conditions and exact numbers.
10. Deliver the requested formats with source coverage and material limitations. Follow the environment's durable-file storage rules; do not deliver intermediate manifests unless requested.

For radar, compute the report key before discovery. Reuse an existing same-name report only if the current scope and content requirements are satisfied and no revision is requested. Otherwise update that report after filling evidence/content gaps. Respect explicit candidate sources and direction boundaries; supplied candidates do not authorize adding unrelated discoveries.

## Preserve naming and portability

For a single paper with a PDF, derive the HTML mechanically:

```python
html_path = pdf_path.with_suffix(".html")
```

Preserve spaces, punctuation, capitalization and multiple dots. For URL/arXiv input, download the PDF first and derive the HTML basename from it. Do not replace it with a method name or add a limu prefix.

Combined outputs:

- Series: `{direction-or-series-name}.html`
- Daily radar: `{YYYY-MM-DD}-radar.html`
- Weekly radar: `{YYYY}-W{WW}-radar.html`
- Monthly radar: `{YYYY}-M{M}-radar.html`

The radar JSON is a working provenance manifest, not a mandatory public deliverable. With HTML-only requests, keep it in temporary storage. Companion Markdown uses `{HTML stem}.wechat.md`; retained Markdown images go in `{HTML stem}.wechat-assets/`.

All HTML image dependencies (`img`, SVG `image`, `source/srcset`, CSS images) must use valid base64 image data URIs; inline SVG is allowed. Source/PDF/project hyperlinks may remain external. Markdown must not contain base64: retain only the useful images as relative asset paths.

## Keep the explanation concrete and evidence-backed

1. Write in natural Chinese unless requested otherwise; explain necessary terms on first use.
2. Ground the task in specific inputs, outputs and a meaningful use case.
3. Link the previous method's gap to the new approach before naming its components.
4. Explain objects, operations and transitions; “alignment/fusion/enhancement” alone is not a mechanism.
5. Keep one useful example through difficult steps; label invented examples as teaching constructions.
6. Follow each necessary formula immediately with plain-language purpose, variable objects, operations and conditions.
7. Trace load-bearing numbers to specific tables, figures or official sources; preserve printed precision and comparison conditions.
8. Distinguish findings from author claims and your own inferences. Missing data stays missing.
9. Separate overall results from ablation/diagnostic evidence; do not overstate causality or statistical significance.
10. State cost, failure conditions and transfer prerequisites. Useful lessons need not be dramatic or immediately actionable in a personal project.
11. Make the problem, approach, method and finding recoverable on rereading.
12. Remove repetition across abstract, captions, body and recap; do not replace clarity with more words.

Use media for discovery/context, primary papers/project pages for technical evidence. Distinguish open/closed-source groups, metric directions, percentage points versus relative changes, and theoretical compute versus measured latency. Do not invent architectures, datasets, formulas, results, limitations, quotations or executed experiments.

## Radar discovery

For active discovery, run from the skill directory as appropriate:

```bash
python3 scripts/fetch_content.py --range today -o /tmp/paperstudio-radar.json
python3 scripts/fetch_content.py --range week --top-k 40 -o /tmp/paperstudio-radar.json
python3 scripts/fetch_content.py --start YYYY-MM-DD --end YYYY-MM-DD -o /tmp/paperstudio-radar.json
```

Treat keyword matches as recall only. Apply semantic direction boundaries, deduplicate, and retain keep/drop reasons, primary/secondary directions, reading reasons and evidence levels. Record every requested source as successful, unconfigured or failed. Follow the user's direction set; “Diffusion” means Diffusion LLM unless visual diffusion is explicitly requested. Explicit HF-only candidate sets remain bounded by the dated HF results.

Create or change an automation only when the user requests recurring work. Use the current radar prompt and the user's timezone; editing this skill alone does not modify existing schedules.

## HTML-to-WeChat conversion

Read the Markdown reference and make a deterministic draft:

```bash
python3 scripts/html_to_markdown.py "{input.html}" --compact --max-chars 0
```

Then semantically rewrite it. Do not copy the whole HTML or truncate it at a character boundary. The per-paper body retains the storyline and conditional findings; single/series can use a few natural sections, while multi-paper coverage takes priority over section counts.

## Updating this skill

Whenever this package is revised, read [references/skill-iteration.md](references/skill-iteration.md) and run its generated-output regression workflow before claiming the update complete. Freeze baseline and candidate packages, generate from raw fixtures in fresh contexts, review against source evidence, record concrete failures, make localized fixes and retest. Run the deterministic gate with [scripts/run_regression.py](scripts/run_regression.py); it verifies records and artifacts, not semantic truth. Do not fabricate test outputs, evaluator judgments or passing runs. Ordinary paper reading does not trigger a skill rewrite or scheduled job.

## Final acceptance

- Every formal paper body passes the eight-part storyline gate with actual content or an accurately scoped gap; approach/method and result/ablation remain distinguishable.
- Method operations connect, relevant training/inference distinctions are clear, and summaries retain specific findings and boundaries.
- All supplied and selected papers are accounted for; evidence-poor watch items do not count as completed full-paper reads.
- Series relations have evidence; shared direction alone is not direct inheritance. Radar reports obey candidate/time/direction boundaries.
- Content depth matches the mode without fixed quotas or later-paper shrinkage; all batches are assembled.
- HTML naming, embedded images, offline formulas, source links, navigation and mobile layout pass. File validation does not certify semantic completeness.
- Requested companion Markdown preserves the same papers and core evidence, with mobile-friendly paragraphs, a final reference list and portable assets.

Do not call a report complete while required evidence is silently missing, formal entries lack storyline elements, images depend on external files, formulas are broken, or the output is merely repeated abstracts.
