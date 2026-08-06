# Layout Patterns（随笔 / digest 模式）

随笔（digest）模式比系列（series）模式简单——没有时间线、没有对照矩阵、没有贯穿线。这里只放 digest 特有的模板 + 一个完整结构示例。bar chart 等 SVG 沿用系列的横向 bar 模板（见 [`svg-patterns.md`](./svg-patterns.md)）。

所有模板：`viewBox` 响应式、`font-family: inherit` 跟随正文字体、内嵌而非外部库、`class="viz"` 统一样式。

## 目录

- [概览卡墙](#1-概览卡墙必画放在-overview-里)
- [领域分布 SVG](#2-领域分布-svg可选领域失衡时才画)
- [每篇承重 bar chart](#3-每篇承重-bar-chart沿用)
- [完整 digest 示例](#4-完整-digest-结构示例3-篇跨-3-领域)

---

## 1. 概览卡墙（必画，放在 `#overview` 里）

CSS grid 实现，**不是 SVG**。每篇一张迷你卡，跨 ≥ 3 领域时按领域分组。

### 平铺版（领域少时）

```html
<div class="overview-grid">
  <a class="overview-card" href="#deepseek-r1" style="--c: var(--p1);">
    <div class="oc-head">
      <span class="oc-num">①</span>
      <span class="field-tag" style="background: var(--p1);">RL</span>
    </div>
    <div class="oc-name">DeepSeek-R1</div>
    <div class="oc-use">用纯 RL 让模型自己长出推理</div>
    <div class="oc-hook">✦ 不需要 SFT 冷启动也能训出来</div>
  </a>

  <a class="overview-card" href="#onevl" style="--c: var(--p2);">
    <div class="oc-head">
      <span class="oc-num">②</span>
      <span class="field-tag" style="background: var(--p2);">VLM</span>
    </div>
    <div class="oc-name">OneVL</div>
    <div class="oc-use">物理预测当辅助监督</div>
    <div class="oc-hook">✦ 物理性监督比语言 latent 有效得多</div>
  </a>

  <!-- ... 更多卡 ... -->
</div>
```

### 分组版（跨 ≥ 3 领域时）

```html
<h3 class="field-group">强化学习</h3>
<div class="overview-grid">
  <!-- 该领域的卡 -->
</div>

<h3 class="field-group">视觉语言</h3>
<div class="overview-grid">
  <!-- 该领域的卡 -->
</div>
```

**要点**：

- 编号 ①②③ 和正文卡片标题、TOC、结尾回顾**全程一致**
- `href="#{shortname}"` 让点卡跳到对应正文卡片
- 颜色通过 `style="--c: var(--pN);"` 注入该篇主色（卡片左条 + 编号 + field-tag 三处统一）
- `.oc-hook` 是亮点 hook，整份 digest 最重要的一行——必须**读完之后**抽出来，不是 abstract 客气话、不是方法步骤

CSS 见 [`../assets/style.css`](../assets/style.css) 的 `.overview-*` / `.field-tag` 部分。

---

## 2. 领域分布 SVG（可选，领域失衡时才画）

当本期某个领域特别集中（如 5 篇里 3 篇都是 RL），在导读下画一张小的分布图点出来。**不强求**——卡墙分组已经表达了。

```svg
<svg class="viz" viewBox="0 0 620 200" xmlns="http://www.w3.org/2000/svg" style="font-family:inherit;">
  <text x="20" y="28" font-size="15" font-weight="700">本期领域分布</text>

  <!-- 每个领域一个色块 + 篇数，宽度按篇数成比例，从多到少排 -->
  <rect x="40"  y="56" width="190" height="42" rx="5" fill="#5b8def" opacity="0.88"/>
  <text x="135" y="83" text-anchor="middle" fill="#fff" font-size="14" font-weight="600">RL · 3 篇</text>

  <rect x="250" y="56" width="125" height="42" rx="5" fill="#62b88f" opacity="0.88"/>
  <text x="312" y="83" text-anchor="middle" fill="#fff" font-size="14" font-weight="600">VLM · 2 篇</text>

  <rect x="395" y="56" width="80"  height="42" rx="5" fill="#e08e45" opacity="0.88"/>
  <text x="435" y="83" text-anchor="middle" fill="#fff" font-size="14" font-weight="600">评测 · 1</text>

  <text x="20" y="140" font-size="12.5" fill="#666">
    本期 6 篇里一半在搞 RL + 推理——这个方向明显在升温
  </text>
</svg>
```

宽度按篇数成比例；颜色用各领域代表色；底部一句话点出"这意味着什么"。

---

## 3. 每篇承重 bar chart（沿用）

每篇 `#{shortname}-exp` 里至少一张承重图，把"vs baseline 涨了多少"或"消融掉某个组件掉多少"抽成横向 bar。模板和系列 / 单篇一致，bar 用该篇主色：

```svg
<svg class="viz" viewBox="0 0 700 280" xmlns="http://www.w3.org/2000/svg" style="font-family:inherit;">
  <text x="20" y="30" font-size="16" font-weight="bold">{标题：这篇 vs baseline / 消融}</text>

  <!-- baseline 竖线 -->
  <line x1="180" y1="60" x2="180" y2="240" stroke="#999"/>

  <!-- 每条 bar：x=180 固定起点，width 按数值缩放，fill 用该篇主色 -->
  <rect x="180" y="80"  width="200" height="22" fill="var(--p1)" opacity="0.7"/>
  <text x="385" y="96"  font-size="13">指标 A：旧 X → 新 Y（+Z%）</text>

  <rect x="180" y="120" width="320" height="22" fill="var(--p1)"/>
  <text x="505" y="136" font-size="13">指标 B：旧 X → 新 Y（+Z%）</text>

  <text x="20" y="270" font-size="11" fill="#666">Source: Table N of {论文名}</text>
</svg>
```

记住：bar 方向 / 长度比例诚实；"越低越好"的指标（RMSE / loss）在标题或底部标明"越短越好"；末尾标 `Source: ...`。

---

## 4. 完整 digest 结构示例（3 篇，跨 3 领域）

一份典型 digest 的骨架，照着填内容：

```html
<header>
  <h1>Paper Digest · 2026-06-26</h1>
  <p class="subtitle">3 篇 · RL · VLM · 评测 — 本期一半在搞推理</p>
  <p class="meta">2026-06-26 · 3 篇论文整合 · 单篇笔记：
    <a href="./DeepSeek-R1.html">DeepSeek-R1</a> ·
    <a href="./OneVL.html">OneVL</a> ·
    <a>（这篇暂无单篇笔记）</a>
  </p>
</header>

<main>
  <!-- 1. 开头总览 -->
  <section id="overview">
    <h2 class="lvl0">本期一览</h2>
    <p>{100-200 字导读：这批哪来的、跨了哪几个领域、哪篇最亮眼、留个钩子}</p>

    <h3 class="field-group">强化学习</h3>
    <div class="overview-grid">
      <a class="overview-card" href="#deepseek-r1" style="--c: var(--p1);">
        <div class="oc-head"><span class="oc-num">①</span>
          <span class="field-tag" style="background: var(--p1);">RL</span></div>
        <div class="oc-name">DeepSeek-R1</div>
        <div class="oc-use">用纯 RL 让模型自己长出推理</div>
        <div class="oc-hook">✦ 不需要 SFT 冷启动，纯 RL 也能涌现长链思考</div>
      </a>
    </div>

    <h3 class="field-group">视觉语言</h3>
    <div class="overview-grid">
      <a class="overview-card" href="#onevl" style="--c: var(--p2);"> ... </a>
    </div>

    <h3 class="field-group">评测</h3>
    <div class="overview-grid">
      <a class="overview-card" href="#mmlu-pro" style="--c: var(--p3);"> ... </a>
    </div>
  </section>

  <!-- 2. 每篇独立卡片 -->
  <div class="chapter p1" id="deepseek-r1">
    <h2>① DeepSeek-R1 <span class="field-tag" style="background: var(--p1);">RL</span></h2>
    <p class="tagline">用纯 RL 让模型自己长出推理</p>
    <p class="hook">✦ 亮点：不需要 SFT 冷启动，纯 RL 也能涌现长链思考——冷启动反而拖后腿</p>

    <section id="r1-mot"><h3>出发点</h3><p>...</p></section>

    <section id="r1-met">
      <h3>方法</h3>
      <figure>
        <img src="data:image/jpeg;base64,{BASE64_PAYLOAD}" alt="DeepSeek-R1 训练流程">
        <figcaption>训练流程（原论文 Figure 2）：先看 RL 冷启动怎么独立站住，再看 SFT 加在哪……</figcaption>
      </figure>
      <h4>(1) 整体流程</h4><p>...</p>
      <h4>(2) GRPO 奖励</h4>
      <p>$$L = \mathbb{E}[\ldots]$$</p>
      <p class="note"><strong>白话翻译</strong>：让模型自己比较多个回答的相对好坏，好的强化坏的削弱……</p>
    </section>

    <section id="r1-exp">
      <h3>关键发现</h3>
      <!-- bar chart SVG：AIME / MATH 等数字 vs baseline -->
    </section>
  </div>

  <div class="chapter p2" id="onevl"> ... </div>
  <div class="chapter p3" id="mmlu-pro"> ... </div>

  <!-- 3. 结尾回顾 -->
  <section id="recap">
    <h2 class="lvl0">回顾：这 3 篇分别是什么</h2>
    <ul class="recap-list">
      <li><span class="rc-num">①</span>
        <span class="field-tag" style="background: var(--p1);">RL</span>
        <strong>DeepSeek-R1</strong> —— 用纯 RL 长出推理；最反直觉的是冷启动反而拖后腿</li>
      <li><span class="rc-num">②</span>
        <span class="field-tag" style="background: var(--p2);">VLM</span>
        <strong>OneVL</strong> —— 物理预测当辅助监督；+0.87 vs +0.31 的对比记得最牢</li>
      <li><span class="rc-num">③</span>
        <span class="field-tag" style="background: var(--p3);">评测</span>
        <strong>MMLU-Pro</strong> —— 给 LLM 做更难的笔试；原来"会做简单题"和"真懂"差这么远</li>
    </ul>
    <p class="takeaway">本期 3 篇有 2 篇都在碰推理——RL 侧从训练范式推、评测侧从测量推，两条线都在收紧。</p>
  </section>
</main>

<aside id="toc">
  <a class="lvl1" href="#overview">本期一览</a>
  <a class="lvl2" href="#deepseek-r1">① DeepSeek-R1</a>
  <a class="lvl2" href="#onevl">② OneVL</a>
  <a class="lvl2" href="#mmlu-pro">③ MMLU-Pro</a>
  <a class="lvl1" href="#recap">回顾</a>
</aside>
```

**要点**：

- 每篇卡片的 `id` 要和概览卡墙的 `href` 对应，点击能跳
- 编号 ①②③ 在 overview、卡片标题、recap、TOC 里**全程一致**
- 领域 tag 在四处都出现（overview 卡 / 卡片标题 / recap / 可选领域分布 SVG），用同一种主色，是该篇的视觉锚
- 没有 `#threads` / 时间线 / 对照矩阵——独立论文就是独立展位，不硬串
