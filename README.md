# PaperStudio

> 把论文发现、精读、系列梳理和研究雷达统一成可长期保存的自包含 HTML，并同步生成适合公众号编辑器的精简 Markdown。

`PaperStudio` 是 `PaperReading` 的升级版，支持四种模式：

- **单篇 / single**：1 篇论文 → 深度结构化阅读笔记
- **系列 / series**：2–6 篇同系列论文 → 演进综述
- **随笔 / digest**：2–12 篇独立论文 → 多篇 digest
- **雷达 / radar**：主动抓取 HF Daily Papers、arXiv 与配置的中文媒体/RSS → 日报或周报

所有模式默认同时输出两份内容：

- `{stem}.html`：完整、自包含的长期阅读笔记。位图全部嵌入 base64，SVG 直接内联。
- `{stem}.wechat.md`：压缩背景、保留核心方法与关键数字的公众号发布稿；图片释放到 `{stem}.wechat-assets/`，方便上传到公众号素材库。

本地 PDF 的单篇 HTML 严格保留 PDF 原文件名，只替换扩展名。

## 使用方式

安装后可直接调用：

```text
使用 $paper-studio 单篇，分析这篇论文：@paper.pdf
使用 $paper-studio 系列，梳理 V-JEPA 到 V-JEPA 2.1 的演进
使用 $paper-studio 随笔，把这几篇独立论文整理成 digest
使用 $paper-studio 雷达，生成本周 VLM、OCR、VLA 与世界模型周报
使用 $paper-studio，把 existing-note.html 转成精简的公众号 Markdown
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
- `html_to_markdown.py` 可独立把既有论文 HTML 转成精简 Markdown，提取图片、简化表格，并把正文链接整理为文末参考资料

## 公众号 Markdown

直接转换一份已有 HTML：

```bash
python3 scripts/html_to_markdown.py "paper.html" --compact
```

默认产出 `paper.wechat.md` 和 `paper.wechat-assets/`。确定性转换负责清理目录、Q&A 等长尾内容，最终仍需做一次语义精简，确保开头有钩子、方法讲得清、数字有来源、结尾能带走一个明确结论。

输出坚持标准 Markdown，优先兼容 [doocs/md](https://github.com/doocs/md) 与 [Wenyan](https://github.com/caol64/wenyan) 这类公众号排版器；链接脚注、移动端短段落、列表样式等处理也参考了 [wechat-format](https://github.com/lyricat/wechat-format)、[markdown-nice](https://github.com/nicejade/markdown-nice) 和 [md2wechat-skill](https://github.com/geekjourneyx/md2wechat-skill) 的公开设计。

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
│   ├── wechat-markdown.md
│   ├── svg-patterns.md
│   └── layout-patterns.md
├── scripts/
│   ├── fetch_content.py
│   ├── fetch_papers.py
│   ├── embed_images.py
│   ├── html_to_markdown.py
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
python3 scripts/html_to_markdown.py "output.html" --compact
```

## License

MIT，见 [LICENSE](./LICENSE)。
