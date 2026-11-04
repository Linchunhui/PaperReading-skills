---
name: paper-understanding-agent
description: 从 PDF 或已解析论文提取可回查的原摘要、逐页事实、方法和实验，支持为专题分阶段核验，也可生成完整结构化记录、价值评估、解读、短卡和参考文献。
---

# 论文理解 Agent

给一篇 PDF 或已解析论文和期望的交付范围，按阶段提取可回查的论文信息。Agent 负责确认原文范围、选择交付和说明缺口。调度脚本负责依赖、并发、重试、缓存、校验与合并。

1. 阅读[输入与编排契约](references/routing.md)。优先复用已有 `input.json` 与范围清单。若只有解析文本或分块 JSON，保留论文 ID、版本和原文定位，准备同一论文的规范输入与页、章节、正文和参考区清单。仅有 PDF 时，用[PyMuPDF 入口](references/pdf-input.md)提取带页码和坐标的文本块，并按需渲染页面供视觉复核。
2. 执行 `python3 scripts/run_agent.py --input INPUT --manifest PLAN --plan-only` 检查范围和依赖，再以同一组输入运行 `python3 scripts/run_agent.py --input INPUT --manifest PLAN --out OUT`。使用单次对话版 VPF 时传入 `--vpf-service-name`、`--vpf-endpoint` 和调用人。各阶段在本地加载对应 Skill。
3. 专题筛选或证据补查可用 `--stage metadata` 或 `--stage-id` 选取页面与章节任务，读取 `stages/` 下的已验证阶段。完整运行以 `runner-report.json` 的 `ok`、`outputs` 及统一记录的 `processing_status` 为交付依据。给用户 `paper-record.json`、`paper-card.md` 和按需的 `paper-short-card.md`。阶段错误从 `failures` 与 `calls/` 查看，同一输入与范围可在原目录继续。

整篇和深读都要能查回原始正文。论文事实、作者对前作的转述、外部材料与 Agent 判断分别保留来源。作者原始摘要由元数据阶段逐字抽取，生成摘要由阅读阶段另存。结构、范围和引文校验用于判断交付是否可追溯，阅读质量仍可用冻结要点独立评阅。

## 云端打包

本包只有这个顶层技能入口。`runtime/PROFILE.md` 与 `references/specialists/*/PROFILE.md` 是完整保留的内部专业指导，由运行脚本按阶段读取，无需分别安装。
