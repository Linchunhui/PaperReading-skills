# 输入契约

输入是 UTF-8 JSON。文本字段使用普通字符串。渲染器使用随技能携带的 CSS 与 SVG 模板，运行时使用 Python 标准库，图和样式嵌入 HTML。

| 层级 | 字段 | 约定 |
| --- | --- | --- |
| 顶层必需 | `title`、`subtitle`、`core`、`branches` | 标题简短。问题分支按读者能跟上的顺序给出。 |
| `core` | `name`、`label`、`description` | 图中的短名称、概念类型或全称、定义。名称和标签各一行。 |
| 顶层可选 | `entry_label`、`date_label` | 默认为「论文」「首次提交日」。教材、标准或其他资料可用「资料」「发布日期」或「版次日期」。 |
| 顶层可选 | `scope`、`intro`、`background`、`lineage`、`open_questions` | `scope` 是范围与截至时间。 `intro` 与 `open_questions` 是字符串数组。 `background` 是最多 4 项的条目数组，省略 ID 即可。 `lineage` 仅写有来源支持的关系。 |
| 章节必需 | `id`、`title`、`description`、`papers` | `title` 是页面章名。 `description` 是图上的问题陈述。 `papers` 是这一问题对应的 1–5 项条目，可以是论文、教材或标准。 |
| 章节可选 | `label`、`context`、`case`、`synthesis` | `label` 是图和目录使用的短章名。 `context` 为背景段落数组， `case` 为一个示意算例， `synthesis` 为跨条目的比较或边界。 |
| 条目必需 | `id`、`name`、`method`、`url` | `name` 是图上的短名， `method` 用一句话交代对象、操作与作用。 `url` 是 HTTPS 原文入口。前序条目也应尽量带原文。 |
| 条目可选 | `title`、`date`、`steps`、`locator`、`boundary`、`results`、`evidence` | `title` 是正文全名， `steps` 为方法步骤数组， `locator` 用章节、表号、图号或页码定位。日期使用 YYYY-MM-DD，缺失显示「日期待核」，有日期的条目排在前面。 |
| 章节或条目可选 | `formulas`、`figures` | 见下方。 |
| 论文条目可选 | `original_figures` | 论文原图数组。放在对应方法和公式之后、结果表之前。 |

章节和条目 ID 使用小写字母、数字和连字符，全局唯一。章节 ID 用于目录，条目在页面中以 `paper-ID` 锚定。避免使用页面保留名 `top`、`overview`、`background`、`open-questions`、`map-frame` 和 `map-zoom`，以及章节前缀 `paper-`。

`results` 的每一行包含以下字段。可比结果填明各自数值与单位，缺少可比基线时省略 `baseline` 和 `change`。

- `conditions` 记录任务、模型或样本、配置与评测口径。
- `metric`、`result`、可选 `baseline` 和 `change` 都用字符串，保留原单位与近似标记。
- `locator` 给出确切表、图或章节，`url` 可选并默认使用条目原文。

`evidence` 每项包含 `text` 和 `locator`，可选 `url`。摘录须核对原文，归纳须明确是归纳。对证据的进一步解释放在正文。

`formulas` 每项填写 `expression` 与可选 `explain`。简单公式用 Unicode 文本。需要分式、根号或上下标时，可用 `mathml` 替代 `expression`，例如 `<math><mfrac><mi>a</mi><mi>b</mi></mfrac></math>`。 `figures` 每项填写 `file`、`alt`、`caption`，可选 `url` 和 `locator`。 `file` 为输入 JSON 同目录下的自包含 SVG 相对路径，须有 `viewBox`。把图的阅读要点写进 `caption`。

### 论文原图

`original_figures` 的每项填写 `file`、`figure`、`page`、`pdf`、`alt` 与 `caption`。

- `file` 是输入 JSON 同目录下的相对 PNG 路径。PNG 原样嵌入 HTML，打开报告即可离线查看。
- `figure` 保留原文图号，如 `2` 或 `"S1"`。 `page` 是 PDF 阅读器从 1 开始的文件页码。印刷页码有差异时可以另写在 `caption`。
- `pdf` 是相对于输出 HTML 的本地 PDF 路径，或已核对的 HTTPS PDF 地址。渲染器拼接 `#page=N`。若提供页码片段，须与 `page` 一致。生成过程读取本地 PNG。
- `alt` 描述图中可见的结构。 `caption` 用一两句指出应该看哪里和怎样理解。可选 `reading_width` 控制桌面默认图宽，单位为像素。手机可点「放大原图」并滚动查看。
- `figures` 用于自绘 SVG，`original_figures` 用于作者的原图。同一概念已有清晰原图时，优先选原图并保留图例、子图标记和坐标轴。

总览把短名和一句做法排在同一画布。报告正文容纳全名和细节。若生成器提示文字过长，优先缩短图上的 `name`、`label` 或 `method`，并在正文用 `title`、`steps` 和 `boundary` 保留原信息。
