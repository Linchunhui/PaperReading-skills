---
name: topic-knowledge-system
description: 将多篇论文或技术资料按问题构建知识体系，按需使用 GPT Researcher 扩展候选并核对论文，生成含 SVG 问题树、原文证据和论文原图的离线 HTML。适用于研究脉络和多方法对照，单篇摘要通常无需调用。
---

# 专题知识体系

用一份有来源的专题数据生成可阅读的报告。总览把核心方法或概念连接到问题及其资料。章内小树在章节标题下从核心直接连接到竖排条目，每行带日期、做法和原文入口。点击条目可跳到正文。

先读[从论文集合到专题报告](references/paper-pipeline.md)，按六步串起人工材料、GPT Researcher、论文理解 Agent 和既有 PaperStudio 串讲。

1. **定范围。** 明确主题、读者、截至时间和允许来源，盘点人工选篇、论文库、已有解析和串讲。
2. **发现候选。** 先查已知材料缺口，获准联网时优先用 GPT Researcher 补经典与近期两轨，保留检索过程。[文献扩展](references/web-research.md)
3. **筛选论文。** 按标识去重，调用论文理解 Agent 的 screen 模式；摘要不足时探查引言、结论或关键方法页。分别记录相关性、纳入状态和证据状态，不能因未读附录判定缺实验。
4. **核对原文。** 调用 evidence 模式或复用同版本 evidence-bundle；关键证明、设置和消融按需读取附录，核心图表由会话视觉能力核验。审查重要事实的支持关系，保留原图和版本定位；只有需要完整单篇解读时才走 full。
5. **构建知识。** 按问题重组旧串讲与新证据，先对齐假设、输入输出和符号，再选择分支算例；不可统一时分开解释。分别记录明确继承、同条件比较、互补和约束不同的替代方案。发现证据缺口后带着具体问题返回检索，服从预算与本地来源限制。[综合与核验](references/synthesis.md)
6. **生成与复核。** 按[研究记录与交接](references/research-record.md)保存候选、事实引用、跨篇结论和缺口，再按[展示输入](references/input.md)生成 topic.json。新研究报告用 --research 校验已审结论与呈现字段的绑定后输出 HTML/SVG；待核结论留在研究记录，不阻塞无关已支持内容。旧报告仍可按原命令重新渲染。

```bash
python3 /path/to/topic-knowledge-system/scripts/topic_handoff.py audit --research research.json --topic topic.json
python3 /path/to/topic-knowledge-system/scripts/build_topic.py topic.json report.html --research research.json --svg-dir diagrams
```

默认画布适合 1–6 章、每章 1–5 项和最多 4 项前序或应用。研究记录不限此容量：paper_key 标识论文版本，展示条目 id 标识其出现位置，允许同一论文服务多个问题。材料较多时拆图或拆成互链专题，不因画布静默丢弃已入选论文。保留旧版与增量证据，明确离线内嵌内容和外部 PDF 的可用范围。
