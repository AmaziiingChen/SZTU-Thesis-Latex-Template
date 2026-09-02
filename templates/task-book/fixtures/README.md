# 任务书公开回归夹具

本目录只保存虚构、可公开、可重复的结构化压力数据。夹具用于模板单元测试、Word 结构检查和 LaTeX/PDF 渲染回归，不属于桌面应用运行时数据，也不得打包为用户示例文档。

## 历史样本转化边界

- 历史任务书只用于发现通用能力缺口，不复制姓名、学号、题目、正文、参考文献、签名、盖章或扫描页面。
- 每个历史缺陷只转化为一条匿名规格、一份合成夹具和对应自动断言。
- `reference-overflow.json` 验证大量中英文参考文献跨页、顺序完整、连续边框和末尾签署区域。
- `image-page-break.json` 验证图片接近分页边界时的尺寸约束、替代文本、题注关联和后续正文顺序。
- 双面扫描空白页、重复页和缺页属于扫描件导入 QA，不在模板夹具中复刻。
- 真实历史材料和生成结果只能保存在 `references/private/`、`output/**/private/` 或 `tmp/`，不得提交到 Git。

## 已覆盖的主要边界

- `minimal` / `normal`：最短与常规内容。
- `feedback-regression`：既有反馈回归。
- `layout-stress`：封面长字段、长题目和日期前缀。
- `long` / `page-break`：长正文与连续表格跨页。
- `rich-text-list`：富文本、图片和列表。
- `nested-list`：最多四级混合列表。
- `cover-subscript`：封面上下标与横线安全距离。
- `reference-overflow`：长参考文献跨页及末尾签署区。
- `image-page-break`：图片、题注和后续正文的分页边界。
