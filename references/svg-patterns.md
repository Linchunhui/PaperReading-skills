# SVG Patterns（系列 / 单篇共用）

写论文笔记常用的 SVG 模板。所有模板都用 `viewBox` 响应式、`font-family: inherit` 跟随正文字体、内嵌而非外部库、`class="viz"` 统一样式。

**谁用哪些**：
- *系列模式* —— 时间线（#1）、横向对照矩阵（#2）必画；bar chart（#3）、概念分布（#4）、架构图（#5）每篇都要
- *单篇模式* —— bar chart（#3）承重；架构图（#5）按需
- *随笔模式* —— 用 [`layout-patterns.md`](./layout-patterns.md) 的概览卡墙 / 领域分布；bar chart（#3）沿用本文件的横向 bar 模板

## 目录

- [时间线](#1-时间线系列必画放在-intro-里)
- [横向对照矩阵](#2-横向对照矩阵系列可选放在-threads-里)
- [关键发现 bar chart](#3-关键发现-bar-chart系列每篇-shortname-exp--单篇实验--随笔每篇至少一张)
- [概念分布对比](#4-概念分布对比可选用于解释理论性方法)
- [模型架构图](#5-模型架构图系列每篇-met-子节必备--单篇按需)
- [通用要求](#通用要求)

---

## 1. 时间线（系列必画，放在 `#intro` 里）

横轴 = 时间；节点 = 每篇论文；节点下方挂 3-5 行小字（机型 / 数据 / 关键变化）；底部用 N 个"叠加块"显示每代相对前代加了什么。

```svg
<svg class="viz" viewBox="0 0 880 460" xmlns="http://www.w3.org/2000/svg" style="font-family:inherit;">
  <!-- 时间轴主线 -->
  <line x1="60" y1="80" x2="820" y2="80" stroke="#bbb" stroke-width="2"/>
  <line x1="60" y1="78" x2="60" y2="86" stroke="#bbb" stroke-width="2"/>
  <line x1="820" y1="78" x2="820" y2="86" stroke="#bbb" stroke-width="2"/>
  <text x="60"  y="60" font-size="12" fill="#666">{起始年月}</text>
  <text x="820" y="60" font-size="12" fill="#666" text-anchor="end">{结束年月}</text>

  <!-- 每篇论文节点（按 x 坐标摆开） -->
  <!-- 论文 1 -->
  <circle cx="120" cy="80" r="9" fill="{color1}"/>
  <text x="120" y="105" font-size="14" fill="{color1}" font-weight="700" text-anchor="middle">{name1}</text>
  <text x="120" y="122" font-size="11" fill="#666" text-anchor="middle">{date1}</text>
  <text x="120" y="160" text-anchor="middle" font-size="12">{一句话定位}</text>
  <text x="120" y="180" text-anchor="middle" font-size="11" fill="#666">{细节 1}</text>
  <text x="120" y="196" text-anchor="middle" font-size="11" fill="#666">{细节 2}</text>
  <text x="120" y="212" text-anchor="middle" font-size="11" fill="#666">{细节 3}</text>

  <!-- ... 重复论文 2、3、4 ... -->

  <!-- 分隔线 -->
  <line x1="120" y1="280" x2="800" y2="280" stroke="#ddd" stroke-dasharray="3,3"/>
  <text x="440" y="270" font-size="13" fill="#666" text-anchor="middle">每一步在叠加什么</text>

  <!-- 叠加块（彩色矩形 + 文字） -->
  <rect x="60"  y="295" width="180" height="50" rx="4" fill="{color1-bg}" stroke="{color1}"/>
  <text x="150" y="316" text-anchor="middle" fill="{color1}" font-weight="600" font-size="12">{起点：核心招数}</text>
  <text x="150" y="332" text-anchor="middle" font-size="11" fill="#666">{副标题}</text>

  <rect x="250" y="295" width="170" height="50" rx="4" fill="{color2-bg}" stroke="{color2}"/>
  <text x="335" y="316" text-anchor="middle" fill="{color2}" font-weight="600" font-size="12">+ {叠加 1}</text>
  <text x="335" y="332" text-anchor="middle" font-size="11" fill="#666">{副标题}</text>

  <!-- 整条线的一句话总结 -->
  <text x="440" y="390" font-size="13" fill="#666" text-anchor="middle" font-style="italic">{从 X 走到 Y 的一句话总结}</text>
  <text x="440" y="412" font-size="12" fill="#999" text-anchor="middle">{补充注释}</text>
</svg>
```

**填色建议**（淡背景）：
- `{color1-bg}` = `#eef3ff`（蓝主色配淡蓝底）
- 其他类推：绿配 `#eefaef`、橙配 `#fff2e8`、玫红配 `#fbecef`

---

## 2. 横向对照矩阵（系列可选，放在 `#threads` 里）

行 = 维度（5-8 行，如 Backbone / 位置编码 / Loss / 防崩塌 / Masking / 超参 / 数据 ...），列 = 论文（N 列）。单元格里用箭头 + 彩色标记表示"新增 / 推翻 / 沿用"。

```svg
<svg class="viz" viewBox="0 0 880 500" xmlns="http://www.w3.org/2000/svg" style="font-family:inherit;">
  <defs>
    <marker id="evo-arr" viewBox="0 0 10 10" refX="9" refY="5"
            markerWidth="6" markerHeight="6" orient="auto">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#62b88f"/>
    </marker>
    <marker id="evo-arr-red" viewBox="0 0 10 10" refX="9" refY="5"
            markerWidth="6" markerHeight="6" orient="auto">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#c4636e"/>
    </marker>
  </defs>

  <!-- 表头：列名（论文名） -->
  <text x="240" y="30" text-anchor="middle" font-weight="700" fill="{color1}" font-size="14">{name1}</text>
  <text x="420" y="30" text-anchor="middle" font-weight="700" fill="{color2}" font-size="14">{name2}</text>
  <text x="600" y="30" text-anchor="middle" font-weight="700" fill="{color3}" font-size="14">{name3}</text>
  <text x="780" y="30" text-anchor="middle" font-weight="700" fill="{color4}" font-size="14">{name4}</text>

  <!-- 行 1：维度名 + 4 个单元格 -->
  <text x="20"  y="80" font-size="13" font-weight="600">{维度 1}</text>
  <text x="240" y="80" text-anchor="middle" font-size="12">{cell 1-1}</text>
  <text x="420" y="80" text-anchor="middle" font-size="12" fill="#666">沿用</text>
  <text x="600" y="80" text-anchor="middle" font-size="12">{cell 1-3}</text>
  <text x="780" y="80" text-anchor="middle" font-size="12" fill="#666">沿用</text>
  <!-- 箭头：1→3 表示 3 改了 1 -->
  <line x1="270" y1="76" x2="570" y2="76" stroke="#62b88f" stroke-dasharray="3,3"
        marker-end="url(#evo-arr)"/>

  <!-- ... 后续行重复 ... -->

  <!-- 底部图例 -->
  <line x1="60"  y1="470" x2="100" y2="470" stroke="#62b88f" marker-end="url(#evo-arr)"/>
  <text x="110" y="474" font-size="12">新增 / 改动</text>
  <line x1="220" y1="470" x2="260" y2="470" stroke="#c4636e" marker-end="url(#evo-arr-red)"/>
  <text x="270" y="474" font-size="12">推翻 / 删除</text>
  <text x="380" y="474" font-size="12" fill="#666">「沿用」= 与前一代相同</text>
</svg>
```

**配色规则**：
- 绿色箭头 `#62b88f` → 新增或改进
- 红色箭头 `#c4636e` → 推翻或删除
- 灰色文字 `#666` → 沿用上一代

---

## 3. 关键发现 bar chart（系列每篇 `#{shortname}-exp` / 单篇实验 / 随笔每篇至少一张）

把"和上一代相比涨了多少"或"vs baseline 的差距"抽成横向 bar chart。

```svg
<svg class="viz" viewBox="0 0 700 280" xmlns="http://www.w3.org/2000/svg" style="font-family:inherit;">
  <text x="20" y="30" font-size="16" font-weight="bold">{标题：例如 V-JEPA 2.1 vs V-JEPA 2 稠密任务}</text>

  <!-- baseline 竖线（左对齐） -->
  <line x1="180" y1="60" x2="180" y2="240" stroke="#999"/>

  <!-- 每条 bar：x=180 固定起点，width 按数值缩放，fill 用论文主色 -->
  <rect x="180" y="70"  width="200" height="22" fill="#62b88f" opacity="0.7"/>
  <text x="385" y="86"  font-size="13">指标 A：旧 0.453 → 新 0.307（−32%）</text>

  <rect x="180" y="110" width="320" height="22" fill="#62b88f"/>
  <text x="505" y="126" font-size="13">指标 B：旧 24.5 → 新 47.9（+96%）</text>

  <!-- ... -->

  <!-- 末尾标数据来源 -->
  <text x="20" y="270" font-size="11" fill="#666">Source: Table N of paper X</text>
</svg>
```

**记住**：bar 的方向 / 长度比例必须诚实——如果是"越低越好"的指标（RMSE / loss），在标题或底部明确写"越短越好"。

---

## 4. 概念分布对比（可选，用于解释理论性方法）

像 LeJEPA 那种"嵌入分布从塌缩 → 各向异性 → 各向同性高斯"的对比，用三个并列的 2D 概念图来讲。

```svg
<svg class="viz" viewBox="0 0 700 280" xmlns="http://www.w3.org/2000/svg" style="font-family:inherit;">
  <!-- 三组对比：左 / 中 / 右 -->

  <!-- 左：崩塌 -->
  <text x="120" y="30" text-anchor="middle" font-size="14" font-weight="700" fill="#c4636e">崩塌</text>
  <circle cx="120" cy="140" r="6" fill="#c4636e"/>
  <text x="120" y="240" text-anchor="middle" font-size="12" fill="#666">所有点挤成一团</text>

  <!-- 中：各向异性 -->
  <text x="350" y="30" text-anchor="middle" font-size="14" font-weight="700" fill="#e08e45">各向异性</text>
  <ellipse cx="350" cy="140" rx="80" ry="20" fill="none" stroke="#e08e45" stroke-width="2"/>
  <text x="350" y="240" text-anchor="middle" font-size="12" fill="#666">某些方向被压扁</text>

  <!-- 右：各向同性 -->
  <text x="580" y="30" text-anchor="middle" font-size="14" font-weight="700" fill="#62b88f">各向同性高斯</text>
  <circle cx="580" cy="140" r="50" fill="none" stroke="#62b88f" stroke-width="2"/>
  <text x="580" y="240" text-anchor="middle" font-size="12" fill="#666">每个方向都同样展开</text>
</svg>
```

---

## 5. 模型架构图（系列每篇 met 子节必备 / 单篇按需）

把模型主干呈现出来——输入是什么、主干由哪些模块组成、模块之间怎么连、输出走哪些 head、训练 / 推理时有什么差别。**这是 met 子节的开篇必备**。

### 5.1 默认做法：从原论文截图（绝大多数情况都该走这条）

为什么：原论文 Figure X 是作者亲自画的，模块名 / 参数规模 / 维度 / 数据流向都对，没有臆造风险；读者可以直接和论文 PDF 对照；自己画 SVG 容易在"好看"和"忠实"之间偏向前者，反而失真。

**截图工作流**：

```bash
# 1. 把目标页转成 200 dpi PNG
pdftoppm -png -r 200 -f {N} -l {N} "/path/to/{paper}.pdf" /tmp/{shortname}

# 2. 用 Pillow 裁切到只剩"图 + caption"
python3 << 'EOF'
from PIL import Image, ImageChops

def autotrim(img, bg=(255,255,255), pad=14):
    bg_im = Image.new(img.mode, img.size, bg)
    diff = ImageChops.difference(img, bg_im)
    bbox = diff.getbbox()
    if bbox is None: return img
    x0, y0, x1, y1 = bbox
    return img.crop((max(0,x0-pad), max(0,y0-pad),
                     min(img.size[0],x1+pad), min(img.size[1],y1+pad)))

img = Image.open('/tmp/{shortname}-{NN}.png').convert('RGB')
# 先按经验值粗裁（y_top 避开页眉、y_bottom 包到 caption 结束）
cropped = img.crop((x0, y_top, x1, y_bottom))
trimmed = autotrim(cropped)
# 单边超过 1400 像素就缩，控制体积
w, h = trimmed.size
if w > 1400:
    trimmed = trimmed.resize((1400, int(h*1400/w)), Image.LANCZOS)
trimmed.save('/path/to/{shortname}-arch.jpg', 'JPEG', quality=88, optimize=True)
EOF
```

**HTML 引用模板**：

```html
<figure>
  <img src="data:image/jpeg;base64,{BASE64_PAYLOAD}" alt="{模型名} 架构图">
  <figcaption>{模型名} 架构（原论文 Figure {N}）：{一句话讲清这张图的看点——
  输入怎么进、主干由谁组成、模块之间怎么连、输出怎么出、训练-推理差别在哪、
  和上一代差在哪}</figcaption>
</figure>
```

注意 figcaption **不要照抄论文的 caption**——原 caption 是「Figure 4: Model Architecture of X. The model takes ...」这种学术腔；你要写成「这张图的看点是什么、和上一代差在哪」这种导读语气。论文 caption 已经在截图里了（作为权威信息源保留），你额外的 figcaption 是给读者的"指路牌"。

**截图质量红线**（缺一项就回去重截）：

- [ ] 完整：图里所有元素（左右副图、子标题 (a)/(b)、所有箭头和文字）都裁进来了
- [ ] 干净：没混入正文段落、页眉、页码、脚注、其他 figure 的边角
- [ ] 清晰：200 dpi 起步，文字能看清；不要为了节省体积压糊
- [ ] 带 caption：原论文的 figure caption 一起截进来
- [ ] 自己写的 figcaption 是导读语，不是论文原文复读
- [ ] 单张 100-300 KB；临时文件命名 `{shortname}-arch.jpg`，最终转成 base64，不留路径引用

### 5.2 例外情况：自己画 SVG（少用）

只有下面三种情况才画 SVG：

1. 原论文确实没架构图（罕见，纯算法 paper 偶尔出现）
2. 原论文图太复杂、信息密度太低，截下来反而看不清
3. 要画的是**跨论文的对照图**（4 代架构演进矩阵之类）——这种本来就不属于"某一篇的架构图"，放 `#threads` 节而不是 met 节，自己画 SVG 是合理的

如果走例外，SVG 模板：

```svg
<svg class="viz" viewBox="0 0 880 500" xmlns="http://www.w3.org/2000/svg" style="font-family:inherit;">
  <defs>
    <marker id="{prefix}-arr" viewBox="0 0 10 10" refX="9" refY="5"
            markerWidth="6" markerHeight="6" orient="auto">
      <path d="M0,0 L10,5 L0,10 z" fill="#666"/>
    </marker>
  </defs>

  <text x="440" y="26" text-anchor="middle" font-size="15" font-weight="700">
    {模型名} 架构：{一句话副标题}
  </text>

  <!-- 第一层：输入节点（标 shape） -->
  <rect x="..." y="80" width="..." height="50" rx="4" fill="#f0eee8" stroke="#999"/>
  <text>{输入名}</text>
  <text font-size="11" fill="#666">{shape / dim}</text>

  <!-- 第二层：主干模块（标参数规模和维度） -->
  <rect x="..." y="160" width="..." height="70" rx="6"
        fill="{淡彩底}" stroke="{主色}" stroke-width="2"/>
  <text font-weight="700">{模块名}</text>
  <text>{参数规模} · {维度}</text>

  <!-- 第三层：连接机制（attention / cross-attention 处用矩形+文字标） -->
  <rect ... fill="#fffae6" stroke="#b88a3e"/>
  <text>Joint Attention / Cross-Attention / MoT Shared</text>

  <!-- 第四层：输出 head（每个标 loss 名） -->
  <rect ... fill="{对应模态色}" stroke="..."/>
  <text>{head 名}</text>
  <text>{loss 类型}</text>

  <!-- 箭头串起来，必要时用不同色标"主路径" vs "次要路径" -->
  <line x1="..." y1="..." x2="..." y2="..." stroke="#666" marker-end="url(#{prefix}-arr)"/>

  <text font-size="11.5" fill="#888" font-style="italic">
    {一句话：这个架构和上一代/同期方法的关键差别在哪}
  </text>
</svg>
```

即使走例外画 SVG，下面这些不能少：每个模块标参数规模和维度、每个输入/输出标 shape、连接箭头有标注、训练-推理差别画出来、用该篇主色染色、底部斜体一句"看点"。

**正反例**：

- ✓ WAM.html 里 5 篇全部从原论文截图：Motus 的 Tri-model Joint Attention、Cosmos Policy 的 latent injection 序列、DreamZero 的训练/推理双区、LingBot-VA 的 MoT 交替序列、Fast-WAM 的架构+mask 双图——每张配一句自己写的 figcaption 做导读
- ✓ 例外做法：JEPA 系列贯穿线节里"4 代架构对照矩阵"用 SVG 画——因为没有任何一篇论文里会有这张图
- ✗ 自己画 SVG 时只画几个矩形写"VLM"、"Action Head"、"Backbone"，箭头一根接一根没有任何 shape / dim / loss 标注 → 等于没画
- ✗ 截图时把整页都截进来（混入正文段落、页眉页码、相邻 figure）→ 不清不准，必须重裁

---

## 通用要求

- **viewBox 响应式**：用 `viewBox="0 0 W H"` 而非固定 `width/height`
- **字体跟随**：`style="font-family:inherit;"`，让 SVG 文字和正文字体一致
- **简洁色板**：主色一个、强调色一个、辅助灰；不要用超过 5 种颜色
- **数值标签必须有**：每条数据都要有数字，每个轴都要有标题
- **末尾标 Source**：`Source: Table N / Figure N of paper X`
- **CSS class**：统一加 `class="viz"`，这样在 HTML 全局 style 里就能一处控样式
