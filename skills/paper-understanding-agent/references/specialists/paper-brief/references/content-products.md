# 四项内容与推荐理由

## 调用参数

`options.deliverables` 默认 `["abstract","deep_read","home_digest","recommendations"]`。用户可以只要其中某项；不要为单个首页摘要生成长篇报告。`options.language` 默认中文。用户提供字数限制时遵守、实际计数，不默认给每篇同样的长度。

`options.priority_institutions` 是 `{priority_id, name, aliases}` 对象数组。只做给定名称或别名的明确匹配；模糊的缩写、同名分校和不同组织不得静默合并。未传名单就不生成 `priority_institution` 理由。论文中提及某单位的方法、使用其模型、致谢其算力，都不等于作者来自该单位。

## 内容层次

- `abstract.markdown`：基于全部可用内容闭合问题—方法—结果链；用 `**...**` 高亮具体重点。不混入消融列表或推荐用语。部分内容未提供时，不为了凑齐模板编写前作、方法或结果。
- `deep_read.sections`：背景与问题、前作与缺口、方法、主结果、消融/诊断、边界与总结。标题与段落可按贡献类型调整，不强制六节都有内容。每节保留 `section_id`、`heading`、`markdown`、`evidence`、`asset_ids`。原文未报告消融与输入未包含消融必须区分；缺失的节在 `omitted` 中记录，不能为证明“没有”引用无关文本。
- `home_digest.markdown`：通常一至三句，用于首页直接扫读。先交代具体问题或贡献，再给关键做法和最有信息量的结果；保留会改变判断的条件。它是独立写作，不在字符数边界截断摘要，不用“点击了解如何颠覆……”制造悬念。
- 三种正文各带 evidence；可复用相同证据，但不能让只有结论的引用替代方法依据。科学符号使用 Markdown/LaTeX；JSON 内反斜杠正确转义。

正文中用 supplied asset ID 对应图片，或由渲染器解析 `asset_ids`。只有 figure caption 时可引用图注写出的事实，不能描述未提供的图形内容。没有图片不阻断 JSON；原图未提供写入 limitations。公式解析缺损时保留明确可读部分，说明缺项，不凭记忆恢复公式。

## 推荐条目的判断

每条 `recommendations` 包含 `reason_id`、`type`、简短 `label`、完整 `explanation`、`basis`、`scope`、`comparison`、`institution_match`、`evidence`。`comparison` 或 `institution_match` 不适用时为 null，不生造对照。

| type | 何时可写 | 必须保留的限制 |
| --- | --- | --- |
| `performance` | 在报告的对照集合中效果领先，或作者明确提出 SOTA 主张 | benchmark、指标、split/版本、对照集合与评测条件；只有作者主张时 basis=author_claim 并归因，不能宣称当前全领域 SOTA |
| `speed` | 直接报告运行速度、吞吐或时延比较 | 硬件、batch、精度、任务与质量约束；未给出的条件写 unknown，不标为同条件公平比较 |
| `cost` | 直接报告训练/推理计算、显存或货币成本优势 | 具体成本口径、预算与对照；参数量、FLOPs、显存、美元不互相替代 |
| `priority_institution` | 作者单位能与传入重点单位名单明确匹配 | 名单条目 ID、输入单位原文、匹配依据；basis=user_preference，不暗示质量认证 |
| `reproducibility` | 输入明确说明代码/数据/权重可用或提供复现细节 | 这是材料中的发布说明；未访问不能声称验证了链接或复现结果 |
| `resource` | 数据集、评测协议、工具资源具有具体覆盖或设计价值 | 对谁有用、提供了什么、覆盖边界 |
| `method_insight` | 方法/理论揭示清楚且有证据的关键机制或取舍 | 不把作者解释当成受控实验已证实的因果机制 |
| `practical_relevance` | 与调用方明确目标直接相关 | 用户目标来源与可用条件；尚未迁移验证要明说 |

`basis` 区分 `author_claim`、`reported_comparison`、`reported_fact`、`user_preference`、`grounded_inference`。推荐条目不输出未经校准的百分比信心或虚构全局分数。

比较条目的 `comparison` 包含 target、baseline、metric、outcome、conditions。目标/对照和 outcome 保留原始报告口径；条件数组 `{name,value}` 中未知值用 null，scope 说明比较范围。若仅有作者“更快”的文字声称而无对照，允许 author_claim、comparison=null，但 label 必须明确“作者声称”，不能包装成已核实的优势。

不要求每篇都有 SOTA、速度、成本、单位四种标签；同一事实不拆成几条同义推荐。没有可靠理由时用 `[]` 并说明证据不足。

## 状态和省略

`coverage` 原样保留。非 full_text 输入 `status=partial`，表示未核全文；全文中任务关键字段仍缺失时也用 partial。`complete` 只表示本次请求在输入范围内已完整处理，不是独立科学认证。`omitted` 条目给出字段路径、原因 `not_requested | absent_from_input | explicitly_unreported | conflicting | insufficient_evidence` 和简短解释。

抽取本来就未包含的作者单位不影响方法是否能解释，但会影响单位推荐；缺失应定位到具体字段，不把整篇一概判为无价值。
