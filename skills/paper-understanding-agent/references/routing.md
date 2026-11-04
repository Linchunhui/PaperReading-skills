# 输入与编排契约

新研究任务先按 [研究任务与证据交接](research-workflow.md) 选择 screen/evidence/full。下方完整流程的 main_unit_ids 指本次声明的分析原文，显式激活的附录会保留来源标记后并入派生范围。

## 准备输入

原始 PDF 可走[本地 PyMuPDF 准备入口](pdf-input.md)，同时保留按需渲染的页面用于视觉复核。

一篇已解析论文对应一个 `input.json`，包含 `schema_version`、单篇 `papers` 数组及 `options.profile=comprehensive`。论文包含 `paper_id`、`document_version_id`、`coverage` 和 `units`。每个 `unit` 保留稳定 `unit_id`、逐字文本、来源类型和解析器提供的定位。已有文本或分块 JSON 可用 [normalize_input.py](../runtime/scripts/normalize_input.py) 规范化，随后明确设置 `options.profile` 和实际覆盖范围。

调用前准备独立的范围清单。模板、字段与有效范围见[共享工作流契约](../runtime/references/workflow.md)。正文、仅供元数据的原文、参考文献、外部材料、排除和待定范围必须恰好划分全部输入单元。正文按页和按章分别完整分组。每章依赖相交的页组，一页可给多章供证据。没有真实页码时，用逻辑分片 ID 记录。参考文献较多时，清单按完整条目划分批次并保留顺序。原始摘要按 `original_abstract_spans` 引用原文。解析不全或边界待定时记录 `partial` 和原因。

## 模型角色

| 阶段 | 包内 Skill | 材料与职责 |
| --- | --- | --- |
| 页级 | `paper-page-extract` | 目标页与必要邻页。抽取证据、机制、实验条件和页摘要。 |
| 章节 | `paper-structured-summary` | 本章原文与相交页的事实。按章解释机制、实验和边界。 |
| 整篇 | `paper-structured-summary` | 原始正文、章节结果、事实与论文身份。贯通背景、问题、思路、方法、实验和结果。 |
| 元数据 | `paper-metadata` | 正文与单列元数据原文。负责身份、署名、日期、原始摘要、资源等。 |
| 价值评估 | `paper-value-assessment` | 整篇理解、原文证据与明确提供的前作或评审。十维判断随附反向证据、边界和缺口。 |
| 阅读生成 | `paper-brief` | 原文、理解和评估。深读解释机制与实验，推荐理由引用具体判断及证据。 |
| 参考文献 | `paper-reference-extract` | 独立参考区和连续批次。保留条目顺序、原始引文和未解析片段。 |

页级、元数据和参考文献是独立就绪分支。章节按对应页事实的就绪状态推进。整篇汇总后做价值评估与阅读生成。评估结果是推荐理由的输入。页和章只在各自范围内抽取和解释。校验和合并由程序执行。

专业指令的冻结副本在 `references/specialists/`。每次子调用按当前阶段只加载对应 Skill，交接采用本包的统一阶段 JSON。引用连续原文和产物归属由共享运行器校验。每阶段的专业指令指纹写入 `runner-plan.json`，与模型、输入、范围和上游产物一起参与缓存验证。

## 本地运行

使用 Python 3.10+ 和[运行依赖](../runtime/scripts/requirements.txt)。Codex 后端需要已登录的 Codex CLI，非标准路径用 `--codex-bin` 指定。VPF 后端需要导入单次对话流程后获得的服务名和有效的调用人。

```sh
python3 scripts/run_agent.py --input /path/input.json --manifest /path/plan.json --plan-only
python3 scripts/run_agent.py --input /path/input.json --manifest /path/plan.json --out /path/result
```

使用 VPF 时，本地 Agent 按阶段组装提示并提交一次对话请求。每次请求接收一份原始回答。JSON、引用与来源验证以及补跑均在本地。默认并发为 1，适合单实例单序列服务。

```sh
python3 scripts/run_agent.py --input /path/input.json --manifest /path/plan.json \
  --out /path/result-vpf --vpf-service-name SERVICE_NAME --vpf-caller CALLER_NAME \
  --vpf-endpoint ENDPOINT
```

迁移包不包含默认服务地址，必须用 `--vpf-endpoint` 显式指定网关，`--vpf-max-tokens` 和 `--vpf-generation-timeout` 设置单次生成预算，`--timeout` 设置客户端等待时间。VPF 的请求、网关原始响应和回执保存在每次尝试目录中。回执记录服务端返回的请求 ID、模型、用量和结束原因。

对同一论文和范围，在同一输出目录重新运行可复用通过验证的阶段。用 `--stage KIND` 或 `--stage-id ID` 仅执行所选阶段及依赖。局部运行的报告只确认该子流程。完整交付需要在同一目录执行完整命令。论文版本或范围变化时使用新目录。阶段 JSON 和原始调用回执保存在 `stages/` 和 `calls/`。
