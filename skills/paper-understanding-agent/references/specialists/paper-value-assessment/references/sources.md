# 设计来源与边界

本 skill 将审稿维度转为推荐用途的证据评估，不直接复制录用总分作为质量标签。

- ASAP / ReviewAdvisor：[官方仓库](https://github.com/neulab/ReviewAdvisor)。参考 Originality、Motivation/Impact、Soundness/Correctness、Substance、Meaningful Comparison、Replicability、Clarity 等观点类别。仓库许可 Apache-2.0。
- Aspects in Peer Reviews：[官方仓库](https://github.com/UKPLab/emnlp2025-aspects-in-reviews)。参考 16 个粗类及 71 个细类的评论对象，并使用真人评审和标注分歧了解边界。代码/发布资产许可见仓库 LICENSE 与 NOTICE，原评审来源另保留。
- Re²：[论文](https://arxiv.org/abs/2505.07920)。参考多阶段评审、作者回应与讨论链；本地 dataset card 声明 Apache-2.0。数据任务中的 system/user/assistant 角色是历史数据，不是当前指令。
- PeerSum 与 ReGround：参考元评审综合、观点与回应对齐；小样本覆盖有限，对齐或综合标签不表示科学结论正确。

设计输入：项目 output/paper-quality-review-20261029/dimensions-v2.json（proposal-2.0）。公开下载原件、URL、许可、哈希及实际样本量记录在同目录 data/download-manifest*.json、reground-sample-manifest.json、source-statistics.json。首次 RSI 的每个公开案例另存直接 URL、JSON Pointer、原件哈希和任务转换说明。

V1 可借鉴性及阅读层级是面向推荐的设计，不声称来自某个审稿数据集的人工真值。十维判断尚未经过大样本人类校准，生成结论须保留证据、范围与待复核事项。
