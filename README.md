# PaperReading

> 一个把研究论文读成"可长期保存的思想笔记"的 Claude Code skill。
> 参考https://github.com/lijigang/ljg-skill-paper

## 简介

读论文不是做学术，是猎取思想。`PaperReading` 是一个 [Claude Code](https://claude.com/claude-code) skill，它把一篇论文（arxiv URL / PDF 文件 / 论文名称）拆解成一份结构化的 HTML 阅读笔记，让一个**不懂这个领域的聪明人**读完能复述：

1. 论文在解决什么问题（具体到一个例子）
2. 作者用什么招数解的（机制 + 设计选择的理由）
3. 核心发现是什么（包括最反直觉的副发现）
4. 你能带走什么洞见 + 能动手的启发

## 输出形态

单文件 HTML（自包含、可独立打开），包含：

- **朴素 h1**：`{论文简短名} 阅读笔记`
- **摘要**：200-300 字全景导览
- **十节结构化笔记**：Motivation → 现存问题 → 相关工作 → 方法详解 → 实验结果 → 总结 → Insight → 启发 → 关键引用 → Q&A
- **配图**：从 PDF 提取的关键架构图、流程图（边界完整、清晰可读、单张 ≤ 300 KB）
- **SVG 可视化**：消融对比、训练流程等，数据严格对照论文原表
- **KaTeX 渲染公式**：每条公式后跟中文白话翻译
- **双语关键引用**：3-5 处真正定义论文思想的原句 + 大白话翻译
- **可折叠 Q&A**：5-10 道围绕模型结构 / 训练流程 / 实验细节的开放性问题

## 安装

把整个目录复制到 Claude Code 的 skills 路径

## 用法

在 Claude Code 里直接调用：

```
/PaperReading https://arxiv.org/abs/2605.12500
```

或喂一个本地 PDF：

```
/PaperReading @/path/to/paper.pdf
```

或描述论文：

```
读一下 SenseNova-U1 这篇论文，生成阅读笔记
```

触发词：`读论文`、`分析论文`、`paper`、或分享任何学术论文。

## 输出位置

- **本地 PDF 来源**：HTML 输出到 PDF 同级目录，文件名 `{简短标题}.html`
- **arxiv URL 来源**：自动下载 PDF 到 `~/Documents/notes/pdf/`，HTML 同级
- **纯网页来源**：HTML 输出到 `~/Documents/notes/html/`
- **配图**：统一放 `~/Documents/notes/images/`

## 设计原则

| 原则 | 含义 |
|------|------|
| 一个锚点撑全文 | Motivation 立一个具象场景，后续所有章节都回到它 |
| 推理外显 | 模拟"一个人想明白的过程"，而非"想明白之后的结果" |
| 变形替代定义 | 解释概念关系时把 A 变形成 B，不要说"A 和 B 是 XX 关系" |
| 落点在能用 | 启发部分给"你可以 ___"，而非"值得思考 ___" |
| 公式必翻译 | 每条 LaTeX 后用一句中文说明它在做什么 |
| 图片必核对 | 配图边界完整、清晰、≤ 300 KB；SVG 数据必须能在论文表里逐项追溯 |

## 文件说明

```
PaperReading/
├── SKILL.md         # skill 主文件，所有写作规则和执行流程
├── README.md        # 你正在看的这个
├── LICENSE          # MIT
├── .gitignore       # 排除临时文件
└── references/      # 预留给参考资料
```

## 示例

效果示例（生成 `SenseNova-U1` 阅读笔记）：

- h1：`SenseNova-U1 阅读笔记`
- 副标题：`SenseNova-U1: Unifying Multimodal Understanding and Generation with NEO-unify Architecture — Diao et al., 2026`
- 6 张架构 / 实验配图（每张 ≤ 300 KB）
- 2 张 SVG 可视化（5 阶段训练时间线 + 重建质量对比）
- 4 个 KaTeX 公式块 + 全部带中文翻译
- 5 处双语关键引用
- 10 题 Q&A 涵盖模型结构 / 训练流程 / 实验细节 / 失效场景

## 贡献

欢迎 PR 改进写作原则、SVG 模板或样式细节。

## License

MIT，见 [LICENSE](./LICENSE)。
