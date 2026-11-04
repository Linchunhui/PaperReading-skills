# 研究任务与证据交接

## 入口、范围与产物

| mode | 默认执行 | 交付 |
| --- | --- | --- |
| screen | 元数据与选定页/语义块；默认已审核 frontmatter 或第一页及原摘要，按缺口指定探针 | evidence-bundle，候选判断仍由专题侧负责 |
| evidence | 元数据、页/块、章节、整篇范围内综合 | evidence-bundle；不运行价值评估、深读和全参考区 |
| full | 全部正文任务、并行深读与评估、独立参考区、合并 | evidence-bundle、paper-record、完整卡和短卡 |

`full` 表示完整交付组合，不宣称读完所有附录。未读附录、遗漏正文或缺失材料保留 partial 和实际覆盖记录。精确阶段选择 `--stage/--stage-id/--through` 仍可用，其选择覆盖模式默认值。

```bash
python scripts/prepare_scope.py --input pdf/input.json --page-manifest pdf/page-manifest.json --output manifest.json
# 当前会话核对分区、章节、读序与摘要逐字跨度，更新 manifest.review_status=reviewed。
python scripts/run_agent.py --mode screen --input pdf/input.json --manifest manifest.json --plan-only
python scripts/run_agent.py --mode screen --input pdf/input.json --manifest manifest.json --out runs/screen --cache-dir runs/stage-cache
python scripts/run_agent.py --mode evidence --input pdf/input.json --manifest manifest.json --out runs/evidence --cache-dir runs/stage-cache
python scripts/run_agent.py --mode full --input pdf/input.json --manifest manifest.json --out runs/full --cache-dir runs/stage-cache
```

先根据 `prepare_pdf.py` 的 outline_hints、label_hints 和文本阅读实际原文。草稿只是索引线索，运行器拒绝未审核草稿。`scope.metadata_source_unit_ids` 可明确指定作者、摘要等页面，必须覆盖 original_abstract_spans；缺字段如实说明。`manifest.screen_unit_ids` 或重复的 `--unit-id` 可选择引言、结论、方法探针。页组可代表有定位的语义块；先核对双栏顺序、跨页段落/表格的续接，再并发。上下文最多向两侧各扩展三个完整块，受字符预算限制，不能无声截断原文块。

## 附录与图表

在原始 manifest 顶层记录 `appendix_unit_ids`，这些原文保留于 scope.excluded_units。可用 `appendix_sections=[{section_id,title,unit_ids}]` 保存连续章节。正文与附录混在一个块时先拆分，保留 parent_unit_id 与字符范围。独立补充 PDF 单独记录哈希和版本关联，不能冒用正文 PDF 的页面来源。

```bash
python scripts/read_evidence.py --input pdf/input.json --manifest manifest.json --query 'A.2' --page-manifest pdf/page-manifest.json --output lookup.json
python scripts/run_agent.py --mode evidence --input pdf/input.json --manifest manifest.json \
  --appendix-unit-id p12-b3 --appendix-unit-id p13-b0 --request-reason '核对定理的必要假设与跨页证明' \
  --out runs/proof --cache-dir runs/stage-cache
```

运行器保存 task-input 派生范围，把显式激活的附录作为本文来源并入本次分析，保留原始输入和请求理由；不混入 external_unit_ids。需要证明、配置、关键消融或统计细节时检查附录索引，不只等待正文出现 See Appendix。部分读取保留未读单元列表。

图像路径输出后，由当前会话的可用视觉工具实际查看。优先架构图、主结果表、公式/表格解析异常；表格保留行列标题、脚注、单位和比较条件。文本 runner 不会自动查看 PNG。记录视觉观察与作者文字的区别，不把图像文件存在当作核验通过。

核对后的逐字转写可用 `import_visual.py --input INPUT --manifest PLAN --page-manifest PAGES --review REVIEW --out NEW_DIR` 导入。review 字段：paper_id、document_version_id、status="reviewed"、method="vlm"或"manual"、reviewer，以及 transcriptions 数组。每行含 page、label、image_sha256、bbox_px=[x0,y0,x1,y1]、text、region="body"或"appendix"；正文行还需 section_id。脚本核对图片身份并生成 origin=visual_transcription 的独立单元。视觉解释留作判断，不能伪装成逐字转写。脚本验证记录和哈希，不代替视觉判断。

## 原文读取、缓存与修复

整篇综合保留已声明原文；assessment/reading 默认收到理解结果、事实、引文和 source_index。需要上下文时返回 `{request_original_unit_ids:[...],reason:"具体缺口"}`，运行器在下一次调用附入原始块，每阶段最多两次、每次最多 16000 字符。越界附录或视觉需求交回宿主扩展范围；预算耗尽写缺口。此协议不开放任意文件或浏览工具。

共享缓存按论文版本、当前阶段源单元、Schema、提示词、模型设置及依赖内容寻址。复用时验证收据、哈希并重新校验来源范围。输入/范围变化使用新运行目录，缓存目录可共享；不把一个专题的价值判断无条件移给另一个专题。

`--repair-file issues.json` 接收 `{issues:[{issue_id,kind,stage_id,reason}]}`。kind 为 extraction/unsupported 时只重跑问题阶段与依赖它的任务；parse、visual、source_missing、comparison 分别转到源解析、看图、材料待核/检索、专题比较。每个 issue_id 最多两次局部重跑，历史保存在 repair-history；耗尽输出 pending。修复会隔离相关共享缓存。调用失败保留错误，不伪造内容修复成功。

## 事实核验与交接

运行完成后自动输出 `evidence-bundle.json`（paper-evidence/1）：paper/paper_key、metadata、sources、evidence、facts、products、coverage、verification、provenance。保留 fact → evidence → unit → 页码/图表/视觉来源。自动测量检查拒绝引文中不存在的报告数值，并要求 value/raw_value 保持原始量纲；计算差值另作综合判断。它不能独立检查归因、条件或科学正确性。遇到特殊数学记号无法机械匹配时回查原文，保留原表示并标记待核；不得为了通过校验修改原文或换成别的数值。

对将进入专题的事实读取 verification.review_queue，核对原始上下文与图表，生成 `{reviews:[{fact_id,fact_sha256,status,reason,reviewer,checked_fields}]}`；status 为 supported/unsupported/uncertain。fact_sha256 从队列复制，不自行改写。上下文、引文或事实变化会使旧核验失效。

```bash
python scripts/evidence_bundle.py --run runs/evidence --reviews reviews.json --output reviewed-evidence.json
```

只有已支持的事实进入确定性结论；不确定项保留在研究记录和待核清单，不阻塞无关章节。没有模型后端时，当前会话可按同一结构抽取，使用 export_bundle 组装；provenance 明确 execution_mode=host_session，不生成伪运行收据。

外部材料先复用专题记录，仍有缺口再按来源边界定向查找。前作、评审意见、作者回应、资源访问与实际执行分别记录 source_type。仓库可访问、许可证允许使用、实现完整和真正运行成功分别判断；后续评价标记日期，区分发表当时与截至当前的结论。
