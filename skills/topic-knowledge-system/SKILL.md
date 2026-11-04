---
name: topic-knowledge-system
description: 将多篇论文或技术资料按问题构建知识体系，按需使用 GPT Researcher 扩展候选并核对论文，生成含 SVG 问题树、原文证据和论文原图的离线 HTML。适用于研究脉络和多方法对照，单篇摘要通常无需调用。
metadata:
  short-description: 专题综合与 SVG 知识图谱
---

# 专题知识体系

用一份有来源的专题数据生成可阅读的报告。总览把核心方法或概念连接到问题及其资料。章内小树在章节标题下从核心直接连接到竖排条目，每行带日期、做法和原文入口。点击条目可跳到正文。

先读[从论文集合到专题报告](references/paper-pipeline.md)，按六步串起人工材料、GPT Researcher、论文理解 Agent 和既有 PaperStudio 串讲。

1. **定范围。** 明确主题、读者、截至时间和允许来源，盘点人工选篇、论文库、已有解析和串讲。
2. **发现候选。** 先查已知材料缺口，获准联网时优先用 GPT Researcher 补经典与近期两轨，保留检索过程。[文献扩展](references/web-research.md)
3. **筛选论文。** 按标识去重，先看标题与摘要，再让论文理解 Agent 用 PDF 文本和必要页面图核对模糊候选。保留纳入、待核、排除及理由。
4. **核对原文。** 复用同版本证据，入选后按需抽取方法和实验原文，绑定页码、章节或表图及版本。作者主图从固定 PDF 裁取并核对。
5. **构建知识。** 以问题分支重组旧串讲与新证据，沿贯穿算例解释每篇改动，交代可比条件与反例。[综合与核验](references/synthesis.md)
6. **生成与复核。** 按[输入契约](references/input.md)写 `topic.json`，参考 [GRPO 节选](references/grpo-example.json)。输出 HTML 和 SVG，检查手机和宽屏图表、原图放大与跳转。增补时保留旧版与检索、筛选、版本和证据记录。

```bash
python3 /path/to/topic-knowledge-system/scripts/build_topic.py topic.json report.html
python3 /path/to/topic-knowledge-system/scripts/build_topic.py topic.json report.html --svg-dir diagrams
```

默认画布适合 1–6 章、每章 1–5 项和最多 4 项前序或应用。材料较多时，可按问题拆图或拆成相互链接的专题；不要因画布容量静默丢弃已入选论文。保留结构化输入、检索与证据记录以便增补，明确单个 HTML 内嵌内容与外部 PDF 链接的可用范围。
