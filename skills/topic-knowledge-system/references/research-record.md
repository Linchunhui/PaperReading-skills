# 研究记录与交接

## 保存研究状态

用 `research.json` 保存研究事实与决策，用 `topic.json` 保存展示内容。二者通过 JSON Pointer 绑定，不让 SVG 容量或短标题决定实际纳入范围。已有人选论文优先复用来源，缺原文标 pending；不反复做完整单篇解读。

research.json 契约为 `schema_version="topic-research/1"`：

| 字段 | 内容 |
| --- | --- |
| source_policy | local 或 web；已有授权边界继续生效 |
| papers | `{paper_key,bundle}` 数组；bundle 是研究目录内 paper-evidence/1 文件的相对路径 |
| candidates | `{candidate_id,paper_key,status,reason,...}`；status 为 included/pending/excluded；保留发现路径、DOI/arXiv 身份及版本疑点 |
| claims | `{claim_id,kind,text,supports,...}`；supports 为 `{paper_key,fact_id}` 数组 |
| bindings | `{ "/branches/0/papers/0/method": "claim-id", ... }`，展示文本必须与已审 claim.text 完全一致 |
| gaps | `{gap_id,question,reason,priority,status}`；priority 越小越先处理，status 为 open/pending/resolved |
| search_budget | `{max_rounds,max_queries}`，停止不表示覆盖穷尽 |
| search_history | 实际查询数组，每项含 round_id、query，并记录时间、gap_id、响应来源与执行状态 |

paper_key 由单篇证据包给出，绑定 paper_id + document_version_id；不能拿新版论文覆盖旧版事实。paper_key 可被多个分支的不同展示 id 引用。旧串讲提供问题骨架和讲解素材；只有版本和证据可回查的部分才能升级为本轮事实。

## 结论及核验

kind 可为 report（转述）、synthesis（跨篇综合）、comparison（数值比较）、teaching（教学算例）、relation（关系）。所有已发布结论的 supports 必须引用 evidence-bundle 中 support_status=supported 的事实；可定位但未审的事实留待核。报告前按单篇 review_queue 核对关键数字、归因、条件和限制。

report 文本若逐字等于唯一支持事实的 text，可复用其核验；改写、综合、关系、算例和比较均需自己的 review：

```json
{"status":"supported","reason":"具体核验依据与边界","reviewer":"当前会话或人工复核者","claim_sha256":"指纹"}
```

claim_sha256 从 audit 输出的 review_queue 复制；它同时绑定结论和当前支持事实的指纹。核对后记录；不能先填 supported 再寻找依据。支持事实本身改变时须重新审查综合结论。自动审查身份、证据跨度、指纹与比较条件，不保证科学真实性。

synthesis/relation 至少关联两个论文版本。relation 只使用 adopts、extends、compares、complements、different_constraints；继承关系需要原文明确采用或扩展的支持，不能用发表时间或相似性代替。原文观点与外部评审意见分别记录。

comparison 另填 `measurements`，为 supports 中两个不同的测量引用。允许同论文消融或跨论文比较。脚本核对 task、dataset、split、metric、unit、direction 与 conditions；跨论文还需 conditions 中明确 model、compute_budget、evaluation_protocol。未知不能当相同，不可比时分别展示原始结果，不生成无条件领先/差值结论。原始事实保留原单位，计算差值放在综合判断中。

教学算例可选，先对齐问题假设与输入输出，按分支解释。`case` 必须绑定 kind=teaching，依据可为公式、算法或作者图；不要把示意数值写成实验数据，也不要强行统一不同前提的方法。

bindings 至少覆盖方法 method、步骤 steps、边界 boundary、结果行的 conditions/metric/result/baseline/change，以及分支 case/synthesis。其他实质性论断也应绑定并复核。展示条目增加 paper_key，且该版本必须处于 included。尚未绑定到展示内容的待核结论可以保存在 claims 中，不阻塞其余报告。

```bash
python scripts/topic_handoff.py audit --research research.json --topic topic.json --output audit.json
python scripts/build_topic.py topic.json report.html --research research.json --svg-dir diagrams
```

## 缺口驱动检索

```bash
python scripts/topic_handoff.py gaps --research research.json --output search-next.json
```

只为 open 缺口提出新查询，排除已执行的同文查询，受剩余轮次与查询数限制。local 模式不生成公开检索任务。当前会话执行 GPT Researcher、阅读实际结果，更新 search_history、候选与 gap 状态，再运行 screen/evidence；脚本不会自行搜索或运行无人值守 Agent。GPT Researcher 内部展开的实际查询也计入预算，失败的已发出查询同样记录。没有新增有效候选或缺口已可说明时停止，并把未覆盖分支写入报告。

外部核验先复用已有领域基线，再定向查缺失前作、后续反例或代码资源。分别记录仓库访问、许可证、实现覆盖和实际运行结果；有链接不代表已执行。按截至日期解释后续评价，不能用当前证据假装发表当时已知。
