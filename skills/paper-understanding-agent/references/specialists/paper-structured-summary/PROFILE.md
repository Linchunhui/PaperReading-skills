---
name: paper-structured-summary
description: 将 PDF 解析结果或结构化论文文本总结成背景、方向、问题、解决思路、方法与总结六个字段，保留机制、证据和可供后续聚类的问题描述。用于入库和多论文分析，不负责 PDF 解析或面向读者的深度长文排版。
---

# Paper Structured Summary

输出能被下游检索、分类、聚类和解读复用的论文结构。六个核心字段都有固定语义，内容长短以讲清机制为准，避免把同一句话重复放进各字段。

## 输入与交付

先读 [输入契约](references/input-contract.md)。可直接接收解析 Markdown、文本块、段落/章节 JSON 或上游结构化输出；仅使用已提供材料，保留来源覆盖和版本。不要求先运行任何其他 skill，也不主动获取或解析 PDF。

输出遵循 [output.schema.json](schemas/output.schema.json)，默认交付一份 JSON。每篇都有六个条目数组 `background / direction / problem / approach / methods / summary`；不支持的部分留 `[]` 并解释，不编造内容凑齐模板。

读取 [字段与机制约定](references/fields.md) 来确定各字段边界和 `problem_signatures`。每个陈述带本篇局部 `item_id`、`basis` 和证据；`basis: inference` 的推断在正文中也明确标记。优先使用原始文本，结构化上游的结论保持为上游证据，不能自动变成原文事实。

需要规范化文件时运行 `python scripts/normalize_input.py parsed.json input.json`（也接受 `.md` / `.txt`）。原始文本默认标为 `partial`，确认覆盖全文才传 `--coverage full_text`；上游 skill 输出会保留 ID 和证据并标为 `structured_only`。规范化不会下载或解析 PDF。

## 总结方法

- 先明确作者要解决的具体问题，再解释机制如何作用于这个问题。分清任务目标、现有瓶颈、作者方案；“使用 Transformer / RL”本身不能充当问题描述。
- `approach` 讲解决方向和为什么可能有效；`methods` 讲输入如何经过关键组件、训练/推理阶段或数据构造得到输出。保留决定行为的关键公式并用白话说明变量和作用，不能只写方法名或口号。
- 方法论文讲工作流程；数据/benchmark 论文讲数据形成、协议和测量对象；理论论文讲假设、结论与适用边界；综述讲组织维度与覆盖范围。不把非方法论文硬写成训练流水线。
- 结果和限制支撑总结，但不把前人结果归给本文。保留影响结论的比较条件；观察性趋势、受控实验、作者主张和解释性推断分开表达。
- 生成 `problem_signatures` 时，描述目标、输入输出、瓶颈与适用约束，不把方法名当作问题。不同问题可以有多个签名；仅主题相同不代表研究同一问题。

## 完成检查

顺着“背景 → 问题 → 思路 → 实际方法 → 结论”检查是否闭合：读者应能解释关键步骤怎样改变结果，而不必靠空泛形容词。仅在材料支持时描述效果；不强制补齐未知训练细节或实验。

`coverage` 不是 `full_text` 时必须 `status: partial`；全文输入的核心字段无法形成受支持的总结时也标为 `partial`；其他非关键缺失仍写入 `missing_fields`。`complete` 只表示完成对所给材料的结构化总结。

有文件时运行 `python scripts/validate_contract.py INPUT OUTPUT`，再人工检查问题签名与论文实际问题是否一致、`problem_item_ids` 是否指向本篇 `problem` 条目。校验通过不代表语义正确。[输入](examples/input.json) 与 [输出](examples/output.json) 是 synthetic 机制样例，不是真实论文。
