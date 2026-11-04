# 字段与来源约定
metadata 保留源语言和原文姓名，未知标量 null、列表 []；author 的 affiliation_ids 只能引用本次输出明确列出的单位。page_summary 为 text/basis/evidence_ids。facts 在此基础上增加 kind、subject、importance、qualifiers 和 keywords；每条必须有目标页证据，上下文只作补接。独立的邻页补充放入同结构的 context_facts；程序按来源路由并保留全部原始内容，记录 target/context 数量，不给无依据的本页引用。open_links 记录未解决的跨片段关系。所有引用 ID 必须来自本次 SOURCE_SPANS。完整原始摘要和识别可靠的显式作者名单可由脚本回填；raw 生成与该处理记录分开保存。schema 通过不代表语义正确。


metadata.dates 的 value 保留日期原文；normalized 仅作不丢精度的 YYYY / YYYY-MM / YYYY-MM-DD 规范化，precision 为 year/month/day/unknown。kind 的 preprint_first_posted、preprint_updated 分别指明确的首次预印本发布和更新；无说明的 Date 用 unspecified。
identifiers.arxiv_id / doi 为 {value, origin, evidence_ids}，单页中 origin 仅能 source_text 或 not_found。code_repositories 为 {url, relationship, release_status, description, evidence_ids}；project_links 为 {url, relationship, resource_type, evidence_ids}。this_paper 需要属于本文的直接证据，不能因出现在文内就视为本文仓库。
keywords 是短语数组，不单独增加生成调用；它沿用所属事实的 evidence_ids。

作者姓名本身不改写。若模型给出的作者引用片段不含该姓名，而输入中恰有一个片段包含该完整姓名，程序可按唯一精确匹配修正 evidence_ids，并记录旧、新定位；无匹配或多重匹配时不猜测。
