# 从 PDF 准备论文证据

优先复用同一 PDF 版本已审核的解析结果与范围清单。只有 PDF 时，先在隔离环境安装 [PyMuPDF 依赖](../scripts/requirements-pdf.txt)。解析只读本地 PDF。网页下载、版本确认与论文身份匹配由调用方负责。

```bash
python3 -m pip install -r scripts/requirements-pdf.txt
python3 scripts/prepare_pdf.py paper.pdf --paper-id arxiv:1234.56789 --version v2 \
  --pages 1-2,6 --render-pages 1,6 --out runs/paper-screen
```

- `--pages` 省略时提取全篇文本；`--render-pages` 按需渲染，只能选已提取的页。先跑文本，遇到双栏顺序、扫描、图表、公式、跨页摘要或证据冲突，再把关键页加入渲染。新一轮准备写入新目录。
- `input.json` 记录原始文本块、稳定单元 ID、从 1 开始的 PDF 文件页码及 PyMuPDF 未旋转页面坐标（pt）。`document_version_id` 同时绑定版本标签和 PDF SHA-256。文本块保留解析顺序；读序须结合页面核对。
- `page-manifest.json` 记录 PDF 页数、解析器版本、各页单元和图像相对路径、图像哈希、DPI、页面标签与旋转。没有文本块的页标为 `needs_text_review`，由读者区分空白页、扫描页和解析遗漏。缺页、读序错误或无法辨识的公式和表格需要保留缺口。
- 现有模型 runner 接收文本及原文定位。页面 PNG 交给可用的视觉模型或人工复核。对图片独有的证据，单独记录文件页码、图号/表号、局部位置、图片哈希、核验方式与状态。若经视觉/OCR 补充文本，先与页面核对，再以独立单元记录其来源与定位；待核识别结果只用于筛选线索。视觉观察与作者原文引文分开保存。
- PDF 准备输出的 `coverage` 初始为 `partial`。审核实际全文覆盖后才可设为 `full_text`。按[范围契约](routing.md)制作 `manifest.json`，定好正文、元数据、参考区、页组、章节组和摘要原文跨度，再跑 `--plan-only`。页面清单提供范围划分线索，章节边界仍需核对。

专题初筛时，可只跑 `--stage metadata` 提取作者原摘要等字段，或用 `--stage-id` 选择 `--plan-only` 中的具体页级任务。单阶段看 `stages/` 与运行报告。全文、方法与实验核验用真实全文范围，抽样和全文按各自输入及范围分目录保存。候选的专题适配度与最终入选理由由专题侧决定。
