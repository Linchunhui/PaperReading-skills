---
name: paper-brief
description: "将论文解析文本或结构化记录生成精简摘要、深度解读、首页解读摘要和有证据的推荐理由。用于论文内容生产、白话解读和阅读卡片；可按需输出原有卡片粗读或单页 HTML，不承担 PDF 解析、元数据抽取或方向聚类。"
---

# Paper Brief · 摘要、解读与推荐理由

让读者理解论文为什么做、前人卡在哪、本文怎样解决，以及证据支持到哪里。输入是**已解析的文本或已有结构化记录**。读取提供的全部相关内容；不默认下载、解析 PDF，也不把论文 Abstract 改写一下就当作全文摘要。

篇幅灵活，先讲清机制，再删重复。摘要选择性加粗关键问题、方法动作和结果；不要整段加粗。深度解读解释操作、阶段衔接、必要公式及实验边界，消融单独总结。

## 默认交付：四项内容的 JSON

先读 [输入与证据约定](references/input-contract.md) 与 [内容字段](references/content-products.md)，按 [输出契约](schemas/output.schema.json) 返回：

| 字段 | 用途 |
| --- | --- |
| `abstract` | 由全部可用内容提炼的摘要：背景、问题、前人思路与缺口、本文方法、主要结果；不列消融 |
| `deep_read` | 连贯的深度解读：机制、原图/公式、主结果、消融、边界；已有结构化信息不足时明确缺口 |
| `home_digest` | 首页可扫读的解读摘要：做什么、关键做法、最值得记住的发现，简短且能独立理解 |
| `recommendations` | 结构化推荐理由：标签、解释、证据、判断依据、范围与比较条件 |

默认四项都生成；`options.deliverables` 可只选其中几项。未选字段为 `null`（推荐理由为 `[]`），在 `omitted` 中写 `not_requested`。缺乏证据也允许留空，写明原因。**原论文自带摘要属于元数据；这里的 `abstract` 是生成摘要。**

SOTA 只针对材料中的比较范围；速度、成本必须说明测量条件与对照，不能从参数少推成推理更快。“重点单位”须由 `options.priority_institutions` 提供，并能对应作者单位；它表示用户偏好，不是质量保证。详细规则见内容字段文档。

## 工作顺序

1. 保留论文身份、版本、来源覆盖和 block/item 定位。非全文输入可以交付有范围标记的结果，不补搜全文，也不虚构缺失字段。
2. 按 [证据规则](references/evidence.md) 阅读全部可用部分，连起“背景 → 问题 → 前作缺口 → 切入点 → 操作链 → 结果”。先区分作者主张、实验观察、受控对照与理论支持。
3. 按 [摘要规范](references/abstract.md) 提炼摘要；生成深读时读取 [解读规范](references/rough-read.md)，检查输入、关键操作、输出以及多阶段模型/数据/目标是否衔接。必要的小例子标明是讲解示例。
4. 独立写首页摘要和推荐条目。首页摘要不是截断长摘要，推荐理由不能只重复标题或用无依据的“重要突破”。
5. 回到输入核对数字、对照、公式与证据引用。文件可用时运行 `scripts/validate_contract.py INPUT OUTPUT`；语义准确性仍需回源检查。

可用 `scripts/normalize_input.py INPUT OUTPUT` 把文本、常见解析 JSON 或上游 skill 输出转为统一输入；覆盖范围由输入声明或 `--coverage` 指定，缺省不假设全文。接口及证据引用参见本地 [输入 schema](schemas/input.schema.json)。

## 保留的阅读模式

用户明确要求原有形式时，按其需求交付，不强制同时输出机器 JSON：

| 模式 | 交付 |
| --- | --- |
| `abstract` | 对话/Markdown 精简摘要 |
| `cards` | 摘要 + 卡片粗读；消融直接列结果要点，避免复杂表格 |
| `summary` / `deep_read` | 摘要 + 连贯解读 |
| `all` | 单页 HTML：共享摘要、卡片、连贯解读 |
| `bundle`（默认） | 上述四项内容的 JSON，可按需再渲染成一个页面 |

只有生成 HTML 时读取 [图片、公式与页面交付](references/html-delivery.md)。保留输入中可用的关键原图与必要截图；只提供文字时继续完成文字解读并注明缺图，不伪造原图或声称看过图中细节。新绘辅助图须标明“解读示意”。

```text
使用 $paper-brief，依据这份解析 JSON 生成四项内容，返回 JSON。
使用 $paper-brief，只生成首页解读摘要和推荐理由；重点单位名单见 options。
使用 $paper-brief all，把已提供的文本和图片做成摘要、卡片、深读同页 HTML。
```

可参考 [合成输入](examples/input.json) 与 [合成输出](examples/output.json)。本 skill 沿用 PaperStudio 的回源核验、原图与公式解释、HTML 检查做法；不需要安装 PaperStudio。原 HTML 辅助脚本的上游来源与许可见 [交付规范](references/html-delivery.md) 和 [LICENSE](LICENSE)。
