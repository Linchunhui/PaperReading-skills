# Layout Patterns（同方向串讲 / 雷达发现）

多篇报告用总览帮助选读，再让每篇正文独立展开。模板只约定布局，正文深度以 [`per-paper-deep-read.md`](./per-paper-deep-read.md) 为准；不要把占位段落的长度当成篇幅限制。本文的花括号与论文 A/B 是占位符，使用前全部换成已核实内容。

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

下面的结构为每篇重复一次，使用唯一前缀。雷达默认按背景介绍、问题及解决思路、方法、实验及结果、总结五部分展开；模板标题是示例，主标题和内部小标题都可贴合论文措辞，导航同步实际标题。理论等类型可将实验部分改为相应的结果与分析标题；步骤数没有配额。串讲可按共同问题调整自然标题。所有正文占位内容须写成实际解读，不能把整条机制拆成五句标签。

```html
<article class="chapter p1" id="paper-a">
  <h2>① {论文 A 简短名}</h2>
  <p class="tagline">{改变了哪个具体环节}</p>
  <p class="meta">{方向/任务 · 关键词 · 问题签名 · 版本与年份} · <a href="{PAPER_URL}">论文原文</a></p>
  <p class="hook">{为什么值得读，保留成立条件}</p>

  <section id="paper-a-background">
    <h3>背景介绍</h3>
    <p>{任务输入、期望输出、贯穿全文的实例}</p>
  </section>

  <section id="paper-a-problem">
    <h3>问题及解决思路</h3>
    <p>{最相关旧方案的操作、卡点与后果；交代本篇要解决的目标}</p>
    <p>{承接这个瓶颈，解释改变哪个环节、为什么可能有效、与最相关前作的差别}</p>
  </section>

  <section id="paper-a-met">
    <h3>方法</h3>
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
    <h3>实验及结果</h3>
    <h4>关键结果</h4>
    <p>{主结果：任务、基线、预算、指标、精确数字及 Table/Figure 位置}</p>
    <!-- 小表或结果图，用正文解释“看哪里—比什么—支持到哪里” -->

    <section id="paper-a-ablation">
      <h4>关键消融与分析</h4>
      <p>{消融或相应分析：改变了什么、保持了什么、结果与归因边界；材料不足准确说明缺口}</p>
    </section>

    <h4>成本与比较限制</h4>
    <p>{与关键结论有关的代价、比较条件和未证明部分，不重复所有限制}</p>
  </section>

  <section id="paper-a-recall">
    <h3>总结</h3>
    <p>{简明收束贡献、可借鉴内容和整体适用边界；能够区分这篇与其他论文}</p>
  </section>
</article>
```

必要的原文论证可穿插在方法与证据解释中，例如某段先定义了什么，后一个目标或对照为什么需要它。不要把整篇读法变成机械填写若干空。

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
  <a class="lvl2" href="#paper-a-background">背景介绍</a>
  <a class="lvl2" href="#paper-a-problem">问题及解决思路</a>
  <a class="lvl2" href="#paper-a-met">方法</a>
  <a class="lvl2" href="#paper-a-exp">实验及结果</a>
  <a class="lvl2" href="#paper-a-recall">总结</a>
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
