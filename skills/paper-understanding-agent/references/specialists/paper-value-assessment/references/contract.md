# 输入与输出契约 v1.0

## 输入

顶层 schema_version="1.0"、papers 数组、options 对象。每篇论文包含 paper_id、document_version_id、paper_type（字符串数组）、coverage、coverage_notes（字符串数组）、units。coverage 为 full_text / partial / abstract_only / structured_only / reviews_only；full_text 必须与实际正文、表图、附录覆盖说明一致，不暗示独立复现。

每个 unit 有 unit_id、source_type、source_id、source_version（可 null）、text、locator（对象，可含 url/path/json_pointer/page/section/block/source_sha256）。unit_id 在同一篇论文内唯一。source_type 只能是 paper / prior_work / review / rebuttal / resource_check / execution_check / structured。缺少版本时记录 unversioned-input，不猜论文版本。外部材料先加入输入再引用。

options.dimension_ids 为空或缺省表示全部十维；否则仅输出指定维度。options.target_context 为可选目标场景。不要从上下文擅自补出另一篇论文的结果。source_type=structured 的上游总结只能用于初步判断，除非同时提供可核对原文。

## 输出

精确字段和枚举以 output.schema.json 为准。顶层 schema_version="1.0"、skill="paper-value-assessment"、papers。

每篇输出保留 paper_id、document_version_id、coverage、coverage_notes；processing_status=complete 或 partial 仅表示本次输入处理覆盖，不是质量等级。输入不是 full_text 时用 partial。

facts 是抽取层：fact_id、kind、field_refs、statement、evidence。field_refs 使用 dimensions.md 中的 B1.contribution_claims 等键，可跨维复用同一事实。evidence 每项仅 unit_id 与逐字 quote；quote 是该 unit.text 的非空连续子串，不改写、补字或使用省略号串接。statement 可忠实概括，量化条件不丢失。

kind 与来源匹配：
- paper：author_claim / method / reported_result / limitation / resource_statement。
- prior_work：prior_work。
- review：review_opinion。
- rebuttal：author_response。
- resource_check：resource_verification。
- execution_check：execution_verification。
- structured：upstream_summary。

assessments 每项包含 dimension_id、grade、status、scope、summary、rationale、findings、supporting_fact_ids、counter_fact_ids、conditions、missing_evidence。findings 必须覆盖该维度 dimensions.md 的全部生成字段，每项为 field、value（具体判断文本）、fact_ids；材料不足的生成项说明无法判断并允许空引用。grade=strong / moderate / weak / mixed / null。status=supported / preliminary / disputed / insufficient / not_applicable。insufficient 和 not_applicable 必须 grade=null；其它状态需要非空等级与至少一个事实引用。scope=paper_evidence / review_consensus / upstream_summary / mixed_sources；只依据评审或上游摘要时不能标 supported。supported 仅指在明确检查范围内有直接支持，不表示论文整体正确。

conditions 写结论成立的任务、预算、假设、比较范围等。missing_evidence 写仍需获取的内容；缺项不自动降为 weak。not_applicable 必须解释论文类型/目标为何不适用。反向结果或异议应放 counter_fact_ids；不把低可信疑问写成已确认错误。

issues 每项有 issue_id、dimension_ids、description、raised_fact_ids、response_fact_ids、followup_fact_ids、resolution。resolution=unresolved / author_responded / reviewer_acknowledged / independently_verified。回应需 author_response 事实，认可需 review_opinion 后续且内容逐项对应，独立验证需 execution_verification 或 resource_verification 及相关实际结果。资源可访问只能解决访问问题，不能解决算法正确性问题。

synthesis 包含：
- breakthrough：label、assessment_refs、rationale。label=strong_candidate / incremental_progress / no_supported_breakthrough / insufficient_evidence / not_assessed。strong_candidate 需要 B1/B2/B3/Q1/Q2/Q3/Q4 均已评估且不是 disputed/insufficient/not_applicable，Q1—Q4 为 supported，并且有正文事实及实际前作证据支持 B1。仍须说明范围，不能声称绝对首次。
- value_summary、reliability_summary：分别解释贡献/借鉴价值与可靠性，不能只报均分。
- reading_tier：priority_reading_candidate / targeted_reference / high_potential_pending / insufficient_material / defer_and_review / not_assessed。
- assessment_refs、rationale、limitations（字符串数组）。只选部分维度且不足汇总时使用 not_assessed；不把未评维度当作合格。

priority_reading_candidate 需要 B1/B2/B3/V1 中至少一项有正面价值依据，Q1—Q4 supported，有正文依据且不存在未处理的核心疑点。defer_and_review 需要严重核心问题的直接依据，不能仅由低分、未录用、未开源或材料缺失触发。其他层级是阅读用途，不是录用概率。

同一论文有不同版本时分别处理，以 paper_id + document_version_id 为键。保留原文版本与回应时间顺序，不将新版本补证回填为旧版本已有证据。

## 最小调用

完整的合成输入/输出示例见 example.input.json 与 example.output.json；它演示“评审观点可提取，但不能当作独立验证”。

需要 Python 3.10+；校验脚本依赖 jsonschema（缺失时使用 python -m pip install jsonschema）。normalize_input.py 只用标准库。脚本不请求模型、不下载论文。

python scripts/normalize_input.py paper.txt --paper-id demo --source-id local-paper --output input.json

使用本 skill 依据 input.json 生成 result.json，再运行：

python scripts/validate_assessment.py input.json result.json

校验检查字段、来源类型、逐字引用、缺失状态和复合判断必要条件；不会执行科学证明、自动判断语义对应或保证结论正确。
