# 模式四 · 研究雷达 / daily-weekly radar

> 无需用户先给 PDF。主动抓取 HF Daily Papers、arXiv、量子位、机器之心及其他配置的 RSS / 公众号公开入口，筛出关注方向，解析成每日或每周自包含 HTML。

## 目录

- [默认关注方向](#默认关注方向)
- [触发与周期](#触发与周期)
- [抓取与来源状态](#step-1抓取并保留来源状态)
- [语义精筛](#step-2按语义边界精筛)
- [跨源合并](#step-3跨源合并与证据回填)
- [解析深度](#step-4解析深度)
- [HTML 结构](#html-结构)
- [输出规则](#输出与自包含规则)
- [定时任务](#日报--周报定时任务)
- [验收](#验收)

这个模式把原 `paper-radar` 合并进 PaperStudio。抓取脚本负责发现、规范化、关键词宽召回和跨源去重；模型负责按 [`directions.md`](./directions.md) 做语义精筛、核对一手来源和写解读。两层不要混：关键词命中不等于真正入选。

## 默认关注方向

VLM / 多模态、OCR / 文档理解、RL、VLA、世界模型、基座模型 / LLM，以及 Diffusion LLM。用户可以在 prompt 里临时增删方向；长期修改时同步更新：

- `scripts/fetch_content.py` 的 `DIRECTIONS`
- `references/directions.md` 的语义边界

## 触发与周期

- “今天有什么值得看的”“今日论文”“AI 日报”“paper radar” → 当天
- “本周热门”“周报”“总结这周 VLA / 世界模型” → 本周；自动任务优先取**上一完整自然周**
- “每天 / 每周给我生成任务” → 创建定时任务，任务正文必须包含本文件末尾的完整 prompt
- 用户给出明确日期 / 区间 → 以用户范围为准

日报默认选 6-10 条，周报默认选 12-20 条。候选不足时不要凑数；候选很多时优先留下真正有技术增量、证据完整、能改变理解的内容。

## Step 1：抓取并保留来源状态

在 skill 根目录运行：

```bash
# 今天，四类默认源
python3 scripts/fetch_content.py --range today -o /tmp/paperstudio-radar.json

# 本周，只关心最热的 40 条候选
python3 scripts/fetch_content.py --range week --top-k 40 -o /tmp/paperstudio-radar.json

# 指定区间 + 额外公众号/RSS
python3 scripts/fetch_content.py \
  --start 2026-07-01 --end 2026-07-07 \
  --feed "自定义来源=https://example.com/feed.xml" \
  -o /tmp/paperstudio-radar.json
```

默认源：

| 来源 | 角色 | 接入 |
|---|---|---|
| Hugging Face Daily Papers | 热度 / 社区关注信号 | `hf-mirror.com/api/daily_papers`，可切官方站 |
| arXiv | 论文一手元数据与 PDF | Atom API；覆盖 `cs.CV/CL/LG/AI/RO/IR` |
| 量子位 | 中文媒体解读 / 行业背景 | `https://www.qbitai.com/feed` |
| 机器之心 | 中文媒体解读 / 论文报道 | 授权 RSS / 数据服务 feed |
| 其他公众号 / 博客 | 可扩展发现源 | 重复传 `--feed NAME=URL` |

机器之心当前的数据服务 / RSS 地址可能与账户绑定。用环境变量或参数传入已授权 feed：

```bash
export PAPERSTUDIO_JIQIZHIXIN_RSS="https://你的授权-feed"
python3 scripts/fetch_content.py --range today

# 或
python3 scripts/fetch_content.py \
  --range today \
  --jiqizhixin-rss "https://你的授权-feed"
```

没有配置时，结果中的 `source_status` 必须写 `not_configured`；某个源失败时写 `error + 原因`。**不允许静默漏源后声称“已抓取全部来源”。**

公众号没有稳定公开 feed 时：

1. 用户给了文章链接 → 直接解析这些公开链接；
2. 有授权 RSS / 数据服务 → 配置到脚本；
3. 两者都没有 → 用网页搜索做当期补充发现，并在来源状态标“search fallback”；
4. 不绕过登录、付费墙、验证码或访问控制，不批量转载全文。

## Step 2：按语义边界精筛

读取 [`directions.md`](./directions.md)，对候选逐条判断：

1. 标题 + abstract / 摘要是否真的命中目标领域；
2. 是否是通用 / 基础贡献，而非垂类套壳；
3. 是否有技术增量，而非纯宣传；
4. 能否找到论文、项目页或其他一手证据；
5. 主方向是什么，次方向是什么。

脚本的 `matched_directions` 只是宽召回。常见误命中：

- “diffusion” 其实是图像 / 视频扩散，不是 Diffusion LLM；
- “robot” 只有感知，没有动作策略，不是 VLA；
- “world model” 只生成视频，不学交互动态；
- “RL” 只在背景里出现，训练实际是 SFT；
- “大模型发布”只有营销口号，没有技术报告。

精筛结果必须补齐 `keep / primary_direction / why_match / why_read / evidence_level`。拿不准的宁可放到“观察”区，或直接剔除。

## Step 3：跨源合并与证据回填

同一工作可能同时出现在 HF、arXiv、量子位、机器之心。只做一张主卡：

- 论文 / 技术报告作为主证据；
- HF upvotes 作为热度信号；
- 中文媒体作为背景、作者观点或产业语境；
- 所有可用来源列进“来源”行，但不要把媒体转述写成论文原话；
- 媒体标题夸张时，用论文原始标题和数据纠偏。

对媒体文章，如果正文引用了论文 / 项目：

1. 打开并核对一手来源；
2. 把 arXiv PDF / 项目页作为主链接；
3. 媒体链接放“中文解读”；
4. 找不到一手来源时明确标 `media-only`，降低结论语气。

## Step 4：解析深度

### 论文卡

每篇至少回答：

1. **为什么现在值得看**：真正的技术增量是什么；
2. **Motivation**：过去卡在哪，给一个具体场景；
3. **Method**：核心机制、输入输出、设计理由；
4. **Findings**：最关键的 1-3 个结果，数字可追溯；
5. **边界**：什么没证明、什么条件下可能不成立；
6. **来源**：PDF / abs / 项目页 / 中文解读。

日报每篇约 250-500 中文字；周报重点 3-5 篇可展开到 600-1000 字，其余做短卡。

### 媒体 / 公众号文章卡

不要套论文 Method 模板。改为：

1. 发生了什么；
2. 文章的核心主张；
3. 可核实证据是什么；
4. 它和关注方向的关系；
5. 哪部分是事实、推断或宣传；
6. 值不值得继续追原论文 / 项目。

只做摘要与分析，不大段复制媒体正文。

## HTML 结构

```html
<header>
  <h1>AI Research Radar · {日期或周区间}</h1>
  <p class="subtitle">{命中数} 条 · VLM · OCR · RL · VLA · 世界模型 · 基座模型</p>
  <p class="meta">抓取来源与状态 · 生成时间 · 时区</p>
</header>

<main>
  <section id="source-status">来源状态与覆盖范围</section>
  <section id="overview">本期总览 + 领域分布 + Top picks</section>
  <section id="vlm">VLM / 多模态</section>
  <section id="ocr">OCR / 文档理解</section>
  <section id="rl">RL</section>
  <section id="vla">VLA</section>
  <section id="world-model">世界模型</section>
  <section id="diffusion-llm">Diffusion LLM</section>
  <section id="foundation-model">基座模型 / LLM</section>
  <section id="watchlist">观察区（证据不足但值得跟踪，可选）</section>
  <section id="recap">今天 / 本周真正发生了什么</section>
</main>
```

空方向不必保留空 section，在 overview 里写“本期无高质量命中”即可。一条内容只在主方向出现一次。

每张卡固定带：

- 类型：`paper / article / release`
- 证据等级：`一手论文 / 项目页 / 媒体+一手 / 仅媒体`
- 热度：HF upvotes（有则写，没有不要伪造）
- `为什么值得看`
- 原始来源与中文解读

## 输出与自包含规则

雷达没有单一源 PDF，因此使用周期名：

- 日报：`{YYYY-MM-DD}-radar.html`
- 周报：`{YYYY}-W{WW}-radar.html`
- 同时保存抓取清单：同名 `.json`

所有 HTML 图片必须是 `data:image/...;base64,...`；SVG 直接内联。生成后依次运行：

```bash
python3 scripts/embed_images.py "{输出.html}" --in-place
python3 scripts/validate_html.py "{输出.html}"
```

同时按 [`wechat-markdown.md`](./wechat-markdown.md) 生成同周期的 `.wechat.md`：日报突出 3–5 条，周报突出 5–8 条；来源状态压成一句覆盖说明，技术卡只保留“为什么值得看 / 核心机制 / 关键证据 / 边界”。

来源 URL、PDF URL、项目页仍可作为普通 `<a href>`，因为它们是引用，不是图片资源。

## 日报 / 周报定时任务

当用户说“创建每日 / 每周任务”时，如果环境有 automation 工具，直接创建任务；没有时提供 cron / 调度器命令。时区默认使用用户当前时区，当前项目默认 `Asia/Shanghai`。

### 日报任务正文

```text
运行 PaperStudio 研究雷达，范围为今天（Asia/Shanghai）。抓取 HF Daily Papers、
arXiv、量子位、机器之心已配置 feed 和其他配置 RSS；报告每个来源的成功/失败状态。
按 directions.md 精筛 VLM、OCR、RL、VLA、世界模型、基座模型、Diffusion LLM，
只保留通用或基础贡献。跨源去重并回填一手论文/项目页。选 6-10 条，逐条解析
为什么值得看、Motivation、Method、Findings、边界与证据等级。输出
YYYY-MM-DD-radar.json 和同名 HTML；HTML 图片全部 base64，最后运行
embed_images.py 与 validate_html.py。即使某个源失败也继续，并在报告中显式说明。
```

推荐时间：每天 09:00。

### 周报任务正文

```text
运行 PaperStudio 研究雷达，范围为上一完整自然周（周一 00:00 到周日 23:59，
Asia/Shanghai）。抓取并报告 HF Daily Papers、arXiv、量子位、机器之心已配置
feed 和其他 RSS 的状态。按 directions.md 精筛 VLM、OCR、RL、VLA、世界模型、
基座模型、Diffusion LLM，跨源去重并补一手证据。选 12-20 条；重点 3-5 条深析，
其余做短卡。总结本周各方向真正的变化、升温主题和证据不足的观察项。输出
YYYY-Www-radar.json 和同名 HTML；HTML 图片全部 base64，并通过 validate_html.py。
```

推荐时间：每周一 09:30。

## 验收

- 来源状态完整，未配置 / 失败不静默；
- 关键词候选已做语义精筛；
- 论文与媒体证据角色分清；
- 同一工作跨源只出现一次；
- 每条有明确主方向、为什么值得看和证据等级；
- 数字能回到论文 Table / Figure 或项目页；
- 不复制大段媒体正文；
- HTML 图片 100% base64，SVG 内联；
- `validate_html.py` 返回成功；
- 日报 / 周报文件名能一眼看出周期。
