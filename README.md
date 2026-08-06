# PaperStudio

> 把论文发现、精读、系列梳理和研究雷达统一成可长期保存的自包含 HTML。

`PaperStudio` 是 `PaperReading` 的升级版，支持四种模式：

- **单篇 / single**：1 篇论文 → 深度结构化阅读笔记
- **系列 / series**：2–6 篇同系列论文 → 演进综述
- **随笔 / digest**：2–12 篇独立论文 → 多篇 digest
- **雷达 / radar**：主动抓取 HF Daily Papers、arXiv 与配置的中文媒体/RSS → 日报或周报

所有模式输出单文件 HTML。位图全部嵌入 base64，SVG 直接内联；本地 PDF 的单篇输出严格保留 PDF 原文件名，只替换扩展名。

## 使用方式

安装后可直接调用：

```text
使用 $paper-studio 单篇，分析这篇论文：@paper.pdf
使用 $paper-studio 系列，梳理 V-JEPA 到 V-JEPA 2.1 的演进
使用 $paper-studio 随笔，把这几篇独立论文整理成 digest
使用 $paper-studio 雷达，生成本周 VLM、OCR、VLA 与世界模型周报
```

未明确指定模式时会自动分流：1 篇走单篇；同系列的 2–6 篇走系列；互相独立的 2–12 篇走随笔；没有给论文、询问今日或本周研究动态时走雷达。

## 能力重点

- 面向外行的 Motivation、方法机制、实验结果和 Q&A
- 每条公式紧跟中文白话翻译
- 架构图、实验图和 SVG 数字均要求可追溯到论文原始证据
- 单篇、系列、随笔和雷达分别拥有独立结构规范
- 雷达保留每个来源的成功、失败或未配置状态
- `embed_images.py` 将图片转为 base64
- `validate_html.py` 校验文件名和图片自包含规则

## 目录

```text
PaperReading-skills/
├── SKILL.md
├── agents/
│   └── openai.yaml
├── assets/
│   ├── icon.svg
│   └── style.css
├── references/
│   ├── foundation.md
│   ├── single-paper.md
│   ├── series.md
│   ├── digest.md
│   ├── radar.md
│   ├── directions.md
│   ├── svg-patterns.md
│   └── layout-patterns.md
├── scripts/
│   ├── fetch_content.py
│   ├── fetch_papers.py
│   ├── embed_images.py
│   └── validate_html.py
├── example/ 或现有示例目录
└── index.html
```

现有论文结果、示例目录及 `index.html` 预览页会继续保留。

## 校验

```bash
python3 scripts/embed_images.py "output.html" --in-place
python3 scripts/validate_html.py "output.html"
python3 scripts/validate_html.py "paper.html" --source-pdf "paper.pdf"
```

## License

MIT，见 [LICENSE](./LICENSE)。
