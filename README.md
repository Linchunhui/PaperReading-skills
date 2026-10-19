# PaperStudio

> 把论文发现、精读、系列梳理和研究雷达统一成可长期保存的自包含 HTML，并同步生成适合公众号编辑器的精简 Markdown。

`PaperStudio` 是 `PaperReading` 的升级版，支持四种模式：

- **单篇 / single**：1 篇论文 → 深度结构化阅读笔记；可选 **跟着 limu 解读 / single-limu** 教学流程
- **系列 / series**：2–6 篇同系列论文 → 演进综述
- **随笔 / digest**：2–12 篇独立论文 → 每篇都能独立读懂的深度合集
- **雷达 / radar**：主动发现与筛选论文 → 日报、周报或月报，每篇正式入选论文默认深读

所有模式默认同时输出两份内容：

- `{stem}.html`：完整、自包含的长期阅读笔记。位图全部嵌入 base64，SVG 直接内联。
- `{stem}.wechat.md`：压缩背景、保留核心方法与关键数字的公众号发布稿；图片释放到 `{stem}.wechat-assets/`，方便上传到公众号素材库。

本地 PDF 的单篇 HTML 严格保留 PDF 原文件名，只替换扩展名。

## 使用方式

安装后可直接调用：

```text
使用 $paper-studio 单篇，分析这篇论文：@paper.pdf
使用 $paper-studio 单篇，跟着 limu 解读这篇论文：https://arxiv.org/pdf/2501.12948v1
使用 $paper-studio 系列，梳理 V-JEPA 到 V-JEPA 2.1 的演进
使用 $paper-studio 随笔，把这几篇独立论文整理成 digest
使用 $paper-studio 雷达，生成本周 VLM、OCR、VLA 与世界模型周报
使用 $paper-studio，把 existing-note.html 转成精简的公众号 Markdown
```

未明确指定模式时会自动分流：1 篇走单篇；同系列的 2–6 篇走系列；互相独立的 2–12 篇走随笔；没有给论文、询问今日或本周研究动态时走雷达。

## 单篇新增：跟着 limu 解读

这是受李沐论文精读方法启发的原创教学讲解，直接内置在 PaperStudio 中，只需安装 PaperStudio。保留普通单篇模式，明确说“跟着 limu 解读”“李沐式精读”“用 limu 的讲解方式”，或使用 `single-limu` 时启用；只说“精读”仍走普通单篇流程。

```text
使用 $paper-studio single-limu，精读 @paper.pdf
使用 $paper-studio 单篇，用 limu 的讲解方式逐段讲 Method，只在对话里解释
```

讲解先建立具体输入输出和前作卡点，再用同一个例子串起核心方法、训练与推理；在关键段落处解释作者如何推进论证，最后检查实验对照、成本与适用边界。公式先说目的，再讲变量与操作；作者解释、实验观察和讲解者推测分别交代。不会冒充李沐本人或编造他的评价。

默认仍交付完整 HTML 和精简 `.wechat.md`，HTML 严格沿用源 PDF basename，Q&A 放在折叠附录。用户明确限定章节、互动或格式时遵守该要求。流程详见 [单篇 limu 带读规范](references/single-paper-limu.md)。

## 随笔与雷达：默认逐篇深读

随笔和日报、周报、月报都吸收 limu 的教学方法，不必再加“详细”或“limu”才展开。每篇从具体问题与前作卡点出发，用同一个例子走通方法，分清训练与推理，解释关键公式和原文论证，再展开主结果、消融/诊断、代价与适用条件，最后给出能复述的回顾。

完整 HTML 和公众号 Markdown 都不设默认总字数、单篇字数或方法小节上限。每篇按讲清问题、机制、证据与边界所需的长度展开，篇数越多报告越长，不按固定总预算平均分摊。单次生成受限时分批写完，再合并为完整报告。所有正式入选论文使用同一深度，Top picks 只表示阅读顺序。已有笔记可复用，但核心方法和结果要回源核验。原文不足的自选候选进入观察区，不冒充完成精读。

```text
使用 $paper-studio 随笔，整理这几篇论文：……
使用 $paper-studio 雷达，生成本周 OCR、VLA 和世界模型报告
```

以上调用默认逐篇深读。用户指定及正式入选的论文完整覆盖；雷达按相关性、贡献和证据质量选篇，不为控制总字数减少篇目或压缩后几篇。只有明确要求简版、短卡、仅摘要或字数上限时才压缩。公众号伴随稿也覆盖同一批论文，保留每篇的连续机制和证据条件；仅要 HTML 时可明确说明。

详见 [逐篇深读规范](references/per-paper-deep-read.md)、[随笔](references/digest.md) 和 [雷达](references/radar.md)。单篇可选 limu 带读与系列串讲继续使用各自结构。

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
│   ├── single-paper-limu.md
│   ├── per-paper-deep-read.md
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
