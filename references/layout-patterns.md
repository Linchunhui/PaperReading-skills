# Layout Patterns（随笔 / digest）

随笔用总览帮助选读，再让每篇正文独立展开。模板只约定布局，正文深度以 [`per-paper-deep-read.md`](./per-paper-deep-read.md) 为准；不要把占位段落的长度当成篇幅限制。本文的花括号与论文 A/B 是占位符，使用前全部换成已核实内容。

## 目录

- [导航卡](#1-导航卡)
- [按篇深读的正文骨架](#2-按篇深读的正文骨架)
- [回顾与导航](#3-回顾与导航)
- [图表](#4-图表)

## 1. 导航卡

使用 CSS grid；每张卡给用途、具体变化和正文锚点。跨领域时可加分组标题。卡片是阅读入口，完整讲解在后文。

```html
<section id="overview">
  <h2>本期阅读路线</h2>
  <p>{说明收录范围、各篇任务与建议阅读顺序}</p>
  <div class="overview-grid">
    <a class="overview-card" href="#paper-a" style="--c:var(--p1)">
      <div class="oc-head">
        <span class="oc-num">①</span>
        <span class="field-tag" style="background:var(--p1)">{领域}</span>
      </div>
      <div class="oc-name">{论文 A 简短名}</div>
      <div class="oc-use">{具体任务与用途}</div>
      <div class="oc-hook">{读完原文后提炼的具体变化，不用宣传词}</div>
    </a>
    <!-- 为每篇建立对应导航卡，编号和正文一致 -->
  </div>
</section>
```

CSS 起手式见 [`../assets/style.css`](../assets/style.css) 的 `.overview-*`、`.field-tag`、`.chapter`。不要设置截断正文的固定高度、line-clamp 或只显示摘要的默认折叠。

## 2. 按篇深读的正文骨架

下面的结构为每篇重复一次，使用唯一前缀；可按论文类型调整自然标题与方法步骤数。所有正文占位内容须写成实际解读，不能把整条机制拆成五句标签。

```html
<article class="chapter p1" id="paper-a">
  <h2>① {论文 A 简短名}</h2>
  <p class="tagline">{改变了哪个具体环节}</p>
  <p class="meta">{版本与年份} · <a href="{PAPER_URL}">论文原文</a></p>
  <p class="hook">{为什么值得读，保留成立条件}</p>

  <section id="paper-a-mot">
    <h3>先看一个具体困难</h3>
    <p>{任务输入、期望输出、贯穿全文的实例}</p>
    <p>{最相关旧方案的操作、卡点与后果；指出本篇核心变化}</p>
  </section>

  <section id="paper-a-met">
    <h3>拿这个样本走一遍方法</h3>
    <p>{最小完整路线：起点、关键表示与操作、最终输出}</p>
    <!-- 在这里插入已核验的原图或教学 SVG；图注解释阅读顺序与关键箭头 -->

    <h4>1. {输入怎样形成可操作的表示}</h4>
    <p>{进入什么、发生什么变化、结果交给谁、为什么需要；回到同一例子}</p>
    <h4>2. {核心机制改了哪一步}</h4>
    <p>{关键变换、与旧方案的差别、相应原文小节如何推进论证}</p>
    <h4>3. {目标与训练更新}</h4>
    <p>{监督从哪来、更新/冻结对象、一次更新流程；不适用训练时换成相应论证步骤}</p>
    <!-- 有承重公式时，使用已核实的原式、来源编号和离线可渲染数学格式 -->
    <p class="note">{紧邻公式解释变量对象、操作、方向与条件；无公式则删除此占位}</p>
    <h4>4. {使用时如何产生最终结果}</h4>
    <p>{推理顺序、保留模块、状态或循环、最终输出；必要时增加步骤}</p>
  </section>

  <section id="paper-a-exp">
    <h3>实验究竟支持什么</h3>
    <p>{主结果：任务、基线、预算、指标、精确数字及 Table/Figure 位置}</p>
    <!-- 小表或结果图，用正文解释“看哪里—比什么—支持到哪里” -->
    <p>{消融或诊断：改变了什么、保持了什么、结果与归因边界；没有则说明缺口}</p>
  </section>

  <section id="paper-a-limits">
    <h3>代价和适用边界</h3>
    <p>{成立条件、成本、未证明部分，区分作者说明与自己的分析}</p>
    <p>{有核验依据时交代代码/模型/数据状态与核验日期}</p>
  </section>

  <section id="paper-a-recall">
    <h3>读完记住什么</h3>
    <p>{具体问题、关键变化、支持证据及边界；能够区分这篇与其他论文}</p>
  </section>
</article>
```

原文论证穿插在方法与证据解释中，例如某段先定义了什么，后一个目标或对照为什么需要它。不要把整篇读法变成机械填写五个空。

## 3. 回顾与导航

```html
<section id="recap">
  <h2>回顾与回看入口</h2>
  <ul class="recap-list">
    <li><a href="#paper-a">① {论文 A}</a>：{问题与核心变化，保留一个关键条件}</li>
    <!-- 逐篇补齐，不复制开头 hook -->
  </ul>
</section>

<aside id="toc" aria-label="阅读目录">
  <a class="lvl1" href="#overview">本期阅读路线</a>
  <a class="lvl1" href="#paper-a">① {论文 A}</a>
  <a class="lvl2" href="#paper-a-mot">问题</a>
  <a class="lvl2" href="#paper-a-met">方法</a>
  <a class="lvl2" href="#paper-a-exp">证据</a>
  <a class="lvl2" href="#paper-a-limits">边界</a>
  <a class="lvl1" href="#recap">回顾</a>
</aside>
```

每篇都须有对应的正文、导航和回顾，不以链接到另一个文件代替解释。移动端 TOC 可折叠，但方法正文保持展开。

## 4. 图表

- 方法图随论文类型选择，核心作用是让对象、变换和连接看得见；优先原图并写原创导读图注，必要时补教学示意。
- 结果可用小表、bar/dot chart 或原文图；数字、单位、方向和比较协议都需核验。模板见 [`svg-patterns.md`](./svg-patterns.md)。
- 领域分布是可选导航信息：每类篇数与实际入选清单一致，长度按数值等比例，不能从本期小样本直接断言整个研究方向升温。
- 内联 SVG 使用 `viewBox` 与 `font-family:inherit`；每个 marker ID 全页唯一。位图压缩后嵌入 base64。
- 不在模板里填未经核实的真实论文数字、图号或因果解释，也不把布局示意误当作原论文架构。
