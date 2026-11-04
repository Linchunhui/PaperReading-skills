# 元数据字段约定

## extracted

`title`、`abstract_original`、`venue` 使用 `{text, evidence}`。原始摘要保持源语言和内容；仅可恢复明确的排版断行/连字符，不能改写、缩写或翻译后仍标作原始摘要。结构化输入若仅包含生成摘要，`abstract_original.text` 为 `null`，可在 `generated.summary` 引用上游摘要并说明来源局限。

`authors` 按署名顺序存放，`author_id` 和 `affiliation_id` 是本篇局部 ID。无明确单位对应时 `affiliation_ids: []`，在 `missing_fields` 记录，而不是把列出的所有单位分给所有作者。团体作者与贡献者名单分别看待，不从附录自动扩充标题页作者。

`dates` 保留 `type`、`value`、`precision`、`raw`。例如 `2026-01` + `month`；月份或日期无法可靠解析时 `value: null`、`precision: unknown` 并保留原文。多个日期可以共存，冲突值也保留并解释。`venue` 的缺失不说明论文未发表。

`references` 保留列表顺序与 `raw_citation`。标题无法恢复则为 `null`，明确出现几个作者就记录几个。`authors_complete: false` 表示省略号/et al. 等明确截断，`null` 表示无法判断，`true` 需输入确实给出完整列表。作者名保持原文，不擅自扩写缩写。

`benchmark_observations` 每条是一项测量：

- `benchmark`：名称、数据集、版本、split；缺项为 `null`，不要把训练集名称当测试集。
- `model`、`role`：保留被测模型及其属于本文/基线/其他的角色；模型相同但预算不同是不同观测。
- `metric`：原名、`value`、`raw_value`、`value_form`、`unit`、`direction`。`92.0%` 存 `value: 92.0, unit: "%"`，不是 `0.92`；`< 12 ms` 的数值为 `null`，原串照存。含误差的 `12 ± 1 ms` 用 `uncertainty`，不要静默丢误差。
- `direction` 仅按输入定义或无歧义的指标含义填写；不能确定用 `unspecified`，不要从本文高低数值猜测好坏。
- `conditions` 保存支持比较所必需的设置和边界，包括硬件、精度、batch、采样/投票、上下文、预算、时间是否含预处理。未知条件不补猜；在 `missing_fields` 中指出影响比较的关键缺口。
- `comparison_group_id` 只是本文内可比较结果的局部组 ID，不表示对照设计足以支持因果结论；条件不明则为 `null`。不同指标即使同组也不能直接相减。

只有标题/图例、没有实际指标值的 benchmark 不造一个测量；在缺失项记录其名称和缺少数值的情况。数值来自供给的结构化转录时，保留该来源属性，不声称已核对原图。

## generated

`related_work` 逐项保存 `problem / approach / remaining_gap` 和指向参考文献的 `work_reference_ids`。输入未包含完整书目信息时，允许引用列表为空，但不能伪造文献 ID。摘要式归纳保留证据，未由输入支持的缺口不补全。

`research_questions` 和 `summary` 为带稳定局部 `item_id` 的条目，`basis: paraphrase` 表示忠实归纳，`inference` 表示分析推断。推断在文字里也说清楚，不能把推断包装成作者结论。总结尽量短，但保留问题、机制、主要证据及影响结论的边界；不要求逐条罗列实验。

## missing_fields 与 limitations

`missing_fields.path` 使用输出内从 `/data` 开始的 JSON Pointer，允许指向缺失的子属性/条目。`reason` 区分输入未提供、论文明确未报告、来源冲突、覆盖不全。字段虽然出现但仍不完整，也可记录该路径。

顶层 `limitations` 放影响整份抽取可靠性的限制，例如只能看到摘要、参考文献被截断、上游是未回源的生成文本。它不是论文自身局限的替代品。
