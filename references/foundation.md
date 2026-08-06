# Foundation：四种模式共享的写作与技术规范

> PaperStudio 的四种模式（单篇 / 系列 / 随笔 / 雷达）都建立在这一层之上。本文件集中放**所有模式都要遵守**的规则：总目标、格式约束、工具箱、SVG 可视化、KaTeX 公式、内容获取与截图、过红线。
>
> SKILL.md 里的 **12 条红线** 和 **4 条写作原则** 是本文件之上最 load-bearing 的一层，先内化它们；本文件是它们的技术展开。
>
> 各模式特有的结构 / 工作流 / 验收在各自的 reference：
> - 单篇 → [`single-paper.md`](./single-paper.md)
> - 系列 → [`series.md`](./series.md)
> - 随笔 → [`digest.md`](./digest.md)
> - 雷达 → [`radar.md`](./radar.md)

## 目录

- [总目标](#总目标四种模式共用)
- [格式约束](#格式约束)
- [工具箱](#工具箱选用没有哪个是必须的)
- [SVG 可视化](#svg-可视化什么时候画怎么画)
- [KaTeX 公式](#katex-公式必须能渲染--必须翻译)
- [获取内容](#获取内容arxiv--pdf--论文名)
- [过红线](#过红线生成-html-前的最后检查)
- [生成 HTML](#生成-html)

---

## 总目标（四种模式共用）

读论文不是做学术，是猎取思想——把别人的发现拆解成自己能用的认知。四种模式都输出**一份可直接当笔记长期保存的结构化 HTML**，让一个**不懂这个领域的聪明人**读完能跟下来、半年后还能查。

最终交付一个 HTML 文件（自包含单文件、可独立打开、内嵌配图与 SVG 可视化、KaTeX 渲染公式）。

**凝练只在 HTML 大标题上追求；正文该展开就展开**——目标不是短，是让人从不懂走到懂。短词、口语、具体名词、有力动词；学术腔是默认敌人。

---

## 格式约束

### ASCII Art（正文里的简单结构图）

正文中的简易示意图（流程、结构、对比）可以用纯 ASCII 字符。允许：`+ - | / \ > < v ^ * = ~ . : # [ ] ( ) _ , ; ! ' "` 和空格。禁止 Unicode 绘图符号。

更正式的、需要承重表达的图（架构图、数据流、消融对比）用 *SVG*——见下方「SVG 可视化」。

### 文件命名

**单篇 + PDF 是机械规则，不做语言模型命名：**

```python
html_path = pdf_path.with_suffix(".html")
```

- `My Paper.v2.pdf` → `My Paper.v2.html`
- `论文 最终版.PDF` → `论文 最终版.html`
- 与 PDF 同级；保留 basename 的空格、标点、大小写与多个点。
- arXiv / URL 来源先下载 PDF；HTML 再严格跟随下载后的 PDF 文件名。
- 不用方法简称替换文件名，不 slugify，不翻译。

多源合并没有唯一 PDF，按批次命名：

- 系列：`{系列名}.html`
- 随笔：`{YYYY-MM-DD}-digest.html`
- 日报雷达：`{YYYY-MM-DD}-radar.html`
- 周报雷达：`{YYYY}-W{WW}-radar.html`

配图裁切文件只是**生成过程中的临时资产**，可以放任务临时目录；最终 HTML 不引用它们的路径，而是嵌入 base64。

---

## 工具箱（选用，没有哪个是必须的）

讲解论文时可以拿的工具：

- *类比* — 承重的，方法的关键组件都能映射上。沿着类比走一遍方法
- *ASCII 图* — 简易结构、流程、对比，正文里直接展示
- *SVG 可视化* — 见下方专节，承重的图都用 SVG
- *餐巾纸速写* — 「以前这么想，现在应该这么想」的并排对比（SVG 实现）
- *好问题* — 把论文解决的困境变成一个让外行也好奇的问题
- *递进例子* — 从简单到复杂，一步步搭建理解
- *反问入链* — 遇到隐含假设，用问题打开

---

## SVG 可视化（什么时候画、怎么画）

数字、对比、流程、关系——只要能用图说清楚比文字说得快，就画 SVG。SVG 内嵌在 HTML 里（无需外部资源），是这套笔记的*视觉骨架*之一。

具体的 SVG / 布局模板见 [`svg-patterns.md`](./svg-patterns.md)（系列用的：时间线、对照矩阵、bar chart、架构图）和 [`layout-patterns.md`](./layout-patterns.md)（随笔用的：概览卡墙、领域分布、bar chart）。**写之前先打开对应模板文件**。

*什么场景必画*：

1. *消融实验对比* — 「去掉 A 掉 5 点，去掉 B 掉 12 点」用横向 bar chart，比表格直观十倍
2. *主结果对比* — 在 N 个 benchmark 上 vs N 个 baseline，分组 bar / dot plot
3. *方法流程* — 数据如何流过模块，箭头 + 节点
4. *训练曲线* — Loss / accuracy 随 step 变化
5. *分布对比* — 「之前的分布是这样，现在变成这样」叠加分布图
6. *架构图* — 模型组件、连接关系（系列模式的 met 子节默认从原论文截图，见下）
7. *因果链* — 「输入这个 → 触发那个 → 导致结果」的概念图

*数据准确性是 SVG 的红线*——画错数字比不画更糟：

- *每个数字必须有出处* — 画 SVG 前先在论文里把要用的数字定位到具体 Table N 或 Figure N，写一个临时记录（哪个数字来自哪张表的哪一行哪一列）
- *不要"凭印象"或四舍五入估算* — 论文写 88.14 就是 88.14，不能写 88、88.1、~88；论文写 0.940 就是 0.940，不能写 0.94
- *不要把"开源最佳"等同于"全部最佳"* — 仔细看论文表格分了 closed-source / open-source 两段，画图标注时必须区分
- *baseline 和对比对象要选论文里真实有的对比* — 不能把没在论文里直接对比过的模型硬拉进来对比；如果非要补充上下文，明确标注"非论文数据"
- *画完逐项核对一遍* — 把 SVG 里的每个数字和源表的对应单元格逐一对照，发现差异立刻修；这一步不可跳过
- *标题和说明也要准* — bar chart 的 "越长越好"/"越短越好"方向、坐标轴单位、对比组的含义，都要和论文一致

*视觉原则*：

- *一个图传达一个 insight* — 不要在一张图里塞五件事
- *简洁线条、最少颜色* — 主色一种、强调色一种、辅助灰，够了
- *标注必备* — 每条数据都要有数值标签，每个轴都要有标题，每个对比都要标"+5%"这种增量
- *响应式* — `viewBox` 而非固定宽高，能在手机上缩放
- *字体跟随* — 用 `font-family: inherit` 让 SVG 文字和 HTML 正文字体一致
- *亲手写而非工具生成* — 不要套 chartjs / d3 这种重库，直接写 SVG 元素，单文件可独立打开
- *末尾标数据来源* — SVG 里加一行小字 "Source: Table N / Figure N of the paper"，让读者能追溯
- *CSS class*：统一加 `class="viz"`，在 [`../assets/style.css`](../assets/style.css) 全局控样式

*简单 bar chart 模板（消融实验示意）*：

```svg
<svg class="viz" viewBox="0 0 600 280" xmlns="http://www.w3.org/2000/svg" style="font-family: inherit;">
  <text x="20" y="30" font-size="16" font-weight="bold">消融实验：去掉某组件的影响</text>
  <!-- 横轴 baseline 线 -->
  <line x1="180" y1="80" x2="180" y2="240" stroke="#999"/>
  <!-- 各项 bar，每条配上数值 -->
  <rect x="180" y="90" width="320" height="24" fill="#4a6fa5"/>
  <text x="510" y="107" font-size="13">+完整方法 (78.5)</text>
  <rect x="180" y="125" width="280" height="24" fill="#4a6fa5" opacity="0.7"/>
  <text x="470" y="142" font-size="13">−组件 A (74.2)</text>
  <rect x="180" y="160" width="200" height="24" fill="#c97064"/>
  <text x="390" y="177" font-size="13">−组件 B (66.1)</text>
  <text x="20" y="270" font-size="11" fill="#666">越长越好；组件 B 是关键</text>
</svg>
```

哪些数据值得画：实验表格里抽出读完后让人"哇"的那条对比；方法描述里如果有"先 A 再 B 再 C"的步骤；消融对比里增量明显的那几条。其他凑数表格不必画。

---

## KaTeX 公式：必须能渲染 + 必须翻译

每条 LaTeX 公式后*必须用一句中文翻译*它在做什么——不解释公式 = 没解释方法（对应红线 10）。

**公式必须能完整渲染**——这是硬要求。书写时遵守以下规范，否则 KaTeX 会渲染失败或显示错乱：

- *转义符号正确* — 下划线 `_` 在数学环境内是下标符号，不要在公式里写未转义的 markdown 强调符；公式外的下划线如果会被 markdown 误解析，用反斜杠转义 `\_`
- *配对完整* — 每个 `$` 必须有配对的 `$`，每个 `$$` 必须有配对的 `$$`；`\left(` 必须配 `\right)`；`\begin{aligned}` 必须配 `\end{aligned}`
- *不混用未支持的 LaTeX 包* — KaTeX 支持的命令是 LaTeX 的子集，不要用 `\usepackage`、`\newcommand` 自定义、不要用 `\mathds`、不要用未声明的环境（如 `\begin{cases}` 可以但 `\begin{equation}` 不行）。常见替代见 https://katex.org/docs/supported.html
- *中文不要混进数学环境* — 公式块里全英文/符号；解释中文写在公式*外面*。`$L_{\text{loss}}$` 这种用 `\text{}` 包裹的英文是允许的，但中文字符塞进 `\text{}` 里在某些 KaTeX 版本上会出错
- *复杂多行公式用 `aligned`* — 不要用 `eqnarray`（不支持），用 `$$\begin{aligned} a &= b \\\\ c &= d \end{aligned}$$`，注意 markdown 转义里换行需要 `\\\\`（四个反斜杠）才能渲染成 LaTeX 的 `\\`
- *写完自检* — 生成 HTML 后*必须打开浏览器肉眼确认每一条公式都正常渲染*，看到 `$...$` 原文裸露、看到红色报错框、看到符号缺失，立刻回去修。一条没渲染好就是整段没渲染好

公式翻译的写法（系列 / 随笔里统一用 `<p class="note">` 包起来加粗「白话翻译」开头）：

```html
<p>$$\mathcal{L} = ...$$</p>
<p class="note"><strong>白话翻译</strong>：第一项让 XX 学 XX；第二项让 YY 学 YY；
$\lambda$ 控制 XX；……</p>
```

翻译要求：不复述公式；解释每个符号实际指什么（不只是字面）；解释公式的*设计意图*——为什么这么写不那么写；必要时给"如果去掉某项会怎样"的反事实。

---

## 获取内容（arxiv / PDF / 论文名）

- arxiv URL → WebFetch 拿到 abstract 和正文；同时记下 PDF URL（通常是 `arxiv.org/pdf/xxx.pdf`）
- 本地 PDF → Read（注意 pages 参数限制）
- 论文名称 → WebSearch 找到 arxiv / 官网链接，再走 URL 流程

确保拿到：标题、作者、摘要、Related Work（前作的引用上下文）、Method（章节结构与公式）、Experiments（主结果表 + 消融表）、Limitation（如果有）。

### 配图提取

识别承载理解的关键图——架构图、流程图、关键示意图、失败案例可视化、消融对比图。提取并暂存：

- arxiv → 优先访问 HTML 版（`arxiv.org/html/{paper_id}`）找原始图片 URL，WebFetch / curl 下载（这种方式得到的是高分辨率原图，边界天然完整）
- PDF → 截取含图页面保存为图片
- 路径：优先放任务临时目录；命名能对应论文与 Figure 编号即可。最终交付前嵌入 HTML。

*结构图 / 架构图截图必须边界完整、清晰可读、文件大小适中*——三条同时满足才行：

**(a) 边界完整**：不能让读者看一张被裁掉一角的图来理解方法

- *截图前先定位完整边界* — 找到图的标题（Figure N: ...）和图正下方的 caption，框选范围必须包含从图正上方一点点空白到 caption 末尾，不能切到任何元素
- *优先用 HTML 版图源而非 PDF 截图* — arxiv HTML 版的图通常是独立 PNG/SVG，下载即完整；PDF 截图容易因为页面跨页、旁边有公式、缩放比例不对而被裁
- *如果只能 PDF 截图*：用足够大的截图区域（宁可多留白，不要切边）；如果图横跨两页，分别截取后竖向拼接；截完*打开图片肉眼检查*，确认四周没有截到一半的字、没有遮挡的图例、没有缺失的箭头终点
- *复杂架构图建议两张*：一张全景（整体结构）+ 一张关键子模块特写。读者先看全景建立心智模型，再看特写理解细节

**(b) 清晰可读**：每个字、每个箭头都能看清

- *截图 DPI 至少 200*：用 `pdftoppm -png -r 200 ...` 而不是默认的 72 DPI；模糊的图等于没有
- *最终宽度 1200-1600 px*：太窄文字糊、太宽页面卡顿
- *肉眼检查*：在浏览器里 100% 缩放看文字是否清晰；遇到 PDF 内嵌的小字图，单独再截一张放大版

**(c) 文件大小适中**：HTML 不能因为一张图就肥到打不开

- *单张图压缩后 ≤ 300 KB*；总图量（base64 嵌入后）控制在 ≤ 2 MB
- *转 JPEG 而非保留 PNG*：除非是线条图截图（PNG 锯齿更少），照片类一律 JPEG quality 80-85 优化
- *压缩流程*（推荐用 PIL 一段脚本搞定）：

```python
from PIL import Image
img = Image.open(src_png).convert("RGB")
# 限制最大宽度避免过大
if img.width > 1400:
    ratio = 1400 / img.width
    img = img.resize((1400, int(img.height * ratio)), Image.LANCZOS)
img.save(out_jpg, "JPEG", quality=85, optimize=True)
```

- *base64 内嵌前再核对一遍*：`ls -la` 看每张图的 KB 数；超出预算就降 quality 到 75 或降宽度到 1200
- *内嵌后删掉路径依赖*：`<img src>` 只能保留 `data:image/...;base64,...`；不能留 `./x.jpg`、绝对路径、`file://` 或远程图片 URL

不是所有图都值得保存——装饰性图、无信息量的曲线图通常可以跳过。挑承重的（一般 3-6 张就够），多了 HTML 会臃肿、读者也疲劳。但凡你决定保留的图，都必须三条同时过：边界完整、清晰可读、大小适中。

### PDF 下载（仅当来源是 arxiv URL 等无本地 PDF 时）

```bash
notes_dir="${PAPERSTUDIO_OUTPUT_DIR:-$PWD}"
mkdir -p "$notes_dir/pdf"
curl -L -o "$notes_dir/pdf/{你选择并保留的PDF文件名}.pdf" {pdf_url}
```

下载完成后，单篇 HTML 必须用 `Path(pdf_path).with_suffix(".html")` 推导，和这份 PDF 严格同名。

### 截图工作流（系列 / 随笔里大量从原论文截架构图时用）

详细的「转页 → 裁切 → autotrim → 压缩」脚本和 HTML `<figure>` 引用模板见 [`svg-patterns.md`](./svg-patterns.md) 的「模型架构图」一节。截图质量红线（完整 / 干净 / 清晰 / 带 caption / figcaption 自己写导读 / 单张 100-300 KB）在那一份文件里逐条列出。

---

## 过红线（生成 HTML 前的最后检查）

逐条扫 SKILL.md 的 12 条红线（每条都过）。额外检查：

- 破公式——否定式排比全文不超过两处，三段式改两项或四项
- 变节奏——长短句交替
- 杀金句——听起来像可引用的，重写
- 查跳跃——逻辑每步可追
- 公式都翻译——每条 LaTeX 后面有中文一句话说明

列修改清单确认后再生成 HTML。

---

## 生成 HTML

各模式的 HTML 结构 / 大标题写法 / 视觉细节在各自的 reference 里。共同点：

- 单文件 HTML，所有 CSS 内联在 `<style>`；KaTeX / 字体可以按环境选择 CDN 或本地内嵌，但图片资源不得走外链
- 直接用 HTML/CSS 生成；若当前环境提供前端设计技能，可调用它协作。无论采用哪种方式，都把三类材料一并纳入：① 内容（正文 + LaTeX 公式 + SVG 代码 + 配图路径）② 资源路径（论文截图绝对路径或 base64）③ 视觉风格规范
- 共享视觉风格：学术阅读风（干净、留白充足、行距 1.7+、正文 16-18px）；中文衬线字体（Noto Serif CJK / 思源宋体）；KaTeX 渲染 LaTeX；配色简洁（背景 `#fafaf7`、正文 `#2c2c2c`、强调色 `#4a6fa5`）；双语引用块（左侧 4px 色条 + 浅底）；配图自适应 `max-width:100%; height:auto`；侧边 TOC（桌面端 ≥1024px 固定，移动端折叠）
- 起手 CSS 直接 copy [`../assets/style.css`](../assets/style.css) 到 `<style>` 里，按需改 `--p1…--p6`

生成完先做确定性后处理：

```bash
python3 scripts/embed_images.py "{输出.html}" --in-place
python3 scripts/validate_html.py "{输出.html}" --source-pdf "{源.pdf}"  # 单篇
python3 scripts/validate_html.py "{输出.html}"                         # 多源
```

`validate_html.py` 失败时继续修，直到：

- 单篇 HTML stem 与 PDF stem 完全一致；
- 每个 `<img src>` 都是合法的 base64 `data:image`；
- SVG 直接内联；SVG `<image href>` 若存在也必须是 base64；
- CSS 背景图没有残留本地或远程路径。

最后打开 HTML 肉眼检查图片、公式、TOC 和移动端布局，再报告绝对路径与文件大小。
