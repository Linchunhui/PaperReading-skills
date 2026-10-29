# PaperStudio

把论文讲清楚，并保存为可长期阅读的自包含 HTML；默认同时生成适合公众号编辑器的 Markdown。只保留三个入口：

| 模式 | 用途 | 展开重点 |
| --- | --- | --- |
| **单篇精读 / single** | 一篇论文的完整理解 | 结构化记录与 limu 启发的原创教学默认融合：贯穿例子、机制推演、原文论证、实验判断 |
| **同方向串讲 / series** | 同一任务/方向下的多篇工作 | 每篇完整主线，加上演进、竞争、互补或不同约束的比较 |
| **雷达发现 / radar** | 主动发现，或整理给定候选集合 | 逐篇紧凑地讲清关键机制、结果与分析，不退化为标题和分数 |

单篇、串讲和雷达的每篇正式解读都保留：
**背景 → 方向/任务 → 问题与前作缺口 → 解决思路 → 具体方法 → 主结果 → 消融/分析结论 → 带条件总结。**

模式改变展开程度，不改变信息底线。导航卡可以短，正文必须能独立读懂。所有篇目同等覆盖，Top picks 只表示阅读顺序。

## 使用

```text
使用 $paper-studio 单篇，精读 @paper.pdf，可以长一点
使用 $paper-studio 单篇，逐段讲 Method，只在对话里解释
使用 $paper-studio 同方向串讲，比较这几篇工作的机制和取舍：……
使用 $paper-studio 雷达，生成本周 OCR、VLA 和世界模型报告
使用 $paper-studio 雷达，仅整理我给的这些候选，不额外发现：……
使用 $paper-studio，把 existing-note.html 转成公众号 Markdown
```

一篇默认单篇；共同方向下的多篇默认串讲；研究动态发现或跨方向候选默认雷达。旧 `single-limu` 写法兼容到融合单篇，不再是可选的另一套正文。旧随笔入口已退役，按材料路由到串讲或雷达。转换已有 HTML 是交付操作，不增加阅读模式。

## 单篇融合了什么

保留原有的完整结构、分类/关键词/问题签名、摘要、贡献、前作关系、结果、可迁移价值和自包含交付；融入具体输入输出、贯穿例子、逐步操作、必要公式白话、关键段落论证与有条件的实验判断。以原创教学表达讲解，不冒充李沐本人或编造其评价。

解决思路回答“为什么改这个环节”，方法回答“具体如何操作”；主结果回答“整体取得了什么”，消融回答“哪些设计有效、无效、饱和或有代价”。训练与推理、观察与推测、实测与建议验证分别交代。

不设默认总字数、屏数或方法步骤配额，可以充分展开。长篇应补齐理解连接，不靠重复增加篇幅。用户指定章节、仅摘要、字数或格式时尊重其范围。

## 串讲与雷达

串讲不局限于同一作者、产品或代际系列；共同问题下的并行方案也可比较。没有证据就不画继承箭头，不同比较协议不排统一榜。

雷达的每篇正文保留完整主线，用较短段落和结论要点表达。关键消融单独呈现，附必要数字和条件；缺失材料、未报告实验与理论论文不适用组件消融须区分。每篇均有总结，不能由全报告 recap 代替。附带稿也覆盖同一批论文。

雷达严格遵守用户方向、日期和候选来源，记录来源成功/失败/未配置状态。给定候选不暗示允许额外加篇；证据不足条目保留明确状态，不冒充完成精读。

详见 [共同主线](references/paper-storyline.md)、[单篇](references/single-paper.md)、[串讲](references/series.md)、[雷达](references/radar.md) 与 [逐篇正文](references/per-paper-deep-read.md)。

## 每次更新的生成回归

参考 SkillAdam 的任务反馈与验收思路，将以下流程写入 skill 更新规范：

**冻结基线和材料 → 独立生成基线/候选产物 → 对照原文评审 → 记录问题 → 局部修订 → 复测 → 接受或保留失败。**

```bash
python3 scripts/run_regression.py prepare \
  --baseline /path/to/baseline \
  --candidate /path/to/current-skill \
  --run-dir /path/to/new-run
# 由更新 skill 的 agent 自动派发生成任务，并安排独立证据评审
python3 scripts/run_regression.py check --run-dir /path/to/new-run
```

内置四类合成案例：复杂单篇、并行路线串讲、含材料不足条目的多篇雷达、理论论文雷达。脚本准备任务并检查案例/产物哈希/评审记录/回归门，不独立调用模型，也不能代替语义评审。不声称安装 SkillAdam 或提供常驻后台优化服务。

流程见 [更新迭代规范](references/skill-iteration.md)，案例在 [evals](evals)，本次结果见 [更新与回归记录](evals/history/2026-10-29/report.md)。一次通过仅说明这些案例未暴露相应问题，不代表所有真实论文都已验证。

## 输出与检查

默认 `{stem}.html` 与 `{stem}.wechat.md`；Markdown 图片放在 `{stem}.wechat-assets/`。用户指定只要 HTML、仅对话或其他格式时遵守。单篇 HTML 保留 PDF 原 basename，只换扩展名；串讲按方向/系列命名，雷达按日期、ISO 周或自然月命名。

HTML 位图嵌入 base64，SVG 内联，必要公式离线可渲染。Markdown 保持标准格式，适合常见公众号编辑器。

```bash
python3 scripts/embed_images.py "output.html" --in-place
python3 scripts/validate_html.py "output.html"
python3 scripts/validate_html.py "paper.html" --source-pdf "paper.pdf"
python3 scripts/html_to_markdown.py "output.html" --compact --max-chars 0
```

文件校验不等于内容完整。转换脚本负责提取和清理格式，之后仍需核对机制、数字、消融与总结。

## 历史示例

[Weekly-Radar](examples/Weekly-Radar) 与 [Monthly-Radar](examples/Monthly-Radar) 保留生成时的原貌，便于回顾。历史产物不代表当前规范已全部执行；新版输出按当前主线与验收要求生成。

## License

MIT，见 [LICENSE](LICENSE)。
