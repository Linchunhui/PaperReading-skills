---
name: paper-metadata
description: 从 PDF 解析结果或已有结构化文本抽取论文元数据、参考文献和带评测条件的 benchmark 指标，并生成相关工作、研究问题与简短总结。适用于论文入库和信息结构化；不负责获取或解析 PDF。
---

# Paper Metadata

把提供的论文材料转成可追溯的 JSON。原文抽取放在 `data.extracted`，解释和归纳放在 `data.generated`；论文原始摘要与生成总结不得互相替代。

## 输入与输出

先读 [输入契约](references/input-contract.md)。接受解析后的 Markdown、文本块、章节/段落 JSON 或已有结构化记录；保留论文 ID、版本、原有定位信息和上游证据。默认只使用输入，不补查论文、作者和榜单。

机器可读输出遵循 [output.schema.json](schemas/output.schema.json)。所有定义的字段保留；未知标量为 `null`、集合为 `[]`，并在 `missing_fields` 说明缺失原因。不要为了得到完整结构推测缺失内容。`coverage` 不是 `full_text` 时必须 `status: partial`；全文输入有请求字段缺失/冲突而无法完成抽取时也标为 `partial`；`complete` 只表示在提供材料内完成请求，不表示全文真实性经过独立核实。

字段解释和容易混淆的情况见 [字段约定](references/fields.md)。[输入](examples/input.json) 与 [输出](examples/output.json) 是明确标记为 synthetic 的小样例，不代表真实研究结果。

需要规范化文件时运行 `python scripts/normalize_input.py parsed.json input.json`（也接受 `.md` / `.txt`）。原始文本默认标为 `partial`，确认覆盖全文才传 `--coverage full_text`；上游 skill 输出会保留 ID 和证据并标为 `structured_only`。规范化不会下载或解析 PDF。

## 抽取重点

- 作者保持署名顺序，团体署名保留为 `collective`。作者与单位的关联必须有明确编号、声明或已结构化映射；邮箱域名、致谢和作者常识不能替代署名证据。
- 日期分别记录预印本发布、修订、接受、正式发表等类型，保留原始精度。不要把 arXiv 日期当会议发表日期，不把年份补成 1 月 1 日。
- 参考文献保留原始条目；标题或作者缺失就留缺失。`et al.` 不是作者姓名，也不表示作者列表完整。
- 每个 benchmark 的每个模型、每个指标独立记录。保留数据集版本/split、指标原名、数值原串、单位、数值形式、评测条件和来源。范围、置信区间、上下界不能被静默变成点估计；无法安全表示为一个数时 `value: null`。
- 仅在比较条件可对齐时复用 `comparison_group_id`。`pass@1`、多次采样投票、不同硬件、量化、批量、训练或推理预算不能当作同一口径。描述性比较不自动成为因果消融。
- 相关工作说明它在解决什么、用了什么办法、还留下什么问题；引用属于前人工作的结果不能算作本文贡献。原文未解释的缺口保持 `null`。

## 完成检查

对照输入核对作者映射、日期类型、参考文献完整性、数值与单位以及每个精确证据片段。结果数字不足以支持 SOTA、速度或成本结论时，只保存数字和条件。

有文件时运行 `python scripts/validate_contract.py INPUT OUTPUT`。它检查结构与可定位证据，不验证科学结论。另检查 `affiliation_ids`、`work_reference_ids` 是否指向本篇实际条目。默认交付一份 JSON，无需额外报告或网页。
