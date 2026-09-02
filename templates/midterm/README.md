# 2026 届中期检查表模板

本目录用同一份 JSON 生成 Word 与 LaTeX/PDF。官方 DOCX 与图像型 PDF 是格式权威；
完整历史批次只用于本地真实内容压力测试，聚合结论见
`docs/HISTORICAL_PROCESS_DOCUMENT_AUDIT.md`。教师勾选、意见和签名区域始终留空。

## 数据入口

正文与进展内容使用公共结构化内容块。除段落、有序/无序列表和单图外，当前已支持：

- `data_table`：真实行列数据、显式列宽权重和对齐；Word 使用可重复表头的嵌套表格，
  LaTeX/PDF 使用同源列定义，数据行禁止拆分。
- `figure_group`：2–4 张本地图片组成一个图组，自动生成 `（a）`、`（b）` 子图标记、
  统一图号与总题注，并作为一个分页单元处理。

示例数据见 `fixtures/structured-content.json`。开题报告与任务书也已完成同等的双路
渲染和回归；前端仍应按具体文档字段开放能力，不向签名、意见等固定区域注入内容块。

- `schema/midterm.schema.json`：统一数据契约；
- `fixtures/`：公开虚构测试数据；
- `spec/artifact.md`：官方原件蒸馏规格；
- `spec/layout.json`：机器可读排版令牌；
- `word/official-template.docx`：与官方范例 DOCX 字节一致的保留基准；
- `word/render.py`、`latex/render.py`：确定性双路渲染器。

目录层级必须通过 `level` 和 `number` 表达；上下标、粗体和斜体使用 `runs`；正文列表
使用显式 `ordered_list` 或 `unordered_list`，并可通过单个 `children` 子列表嵌套至四级；
图片使用本地路径、替代文本、宽度和可选题注。不得用空格模拟
缩进，也不得让 Agent 直接修改 Word 表格或生成的 TeX 数据文件。

## 必需字体

- 标题：方正小标宋简体；
- 中文正文：中易宋体；
- 英文和数字：Times New Roman。

缺少任一字体时 LaTeX 渲染会停止，不会回退。商业字体不进入 Git；可安装到系统字体
目录、放入本地 `templates/midterm/fonts.local/`，或用 `SZTU_FONT_DIR` 与对应单字体
环境变量指定。当前 macOS 开发环境只从已安装的 WPS 授权字体缓存复制一份到被 Git
忽略的 `fonts.local/`，不会对外分发。

## 开发与验收原则

- 优先用 XeLaTeX 快速迭代和逐页检查；
- Word 路径只生成 DOCX，不自动启动 Word/WPS；
- 正常开发不使用 LibreOffice 的渲染结果作为 Word/WPS 验收；
- 最终由项目负责人在 Word/WPS 中检查并反馈。

## 生成命令

以下命令均从仓库根目录执行。先复制一份最接近实际内容的 fixture，按照
`schema/midterm.schema.json` 修改 JSON；这一个 JSON 是 Word 与 LaTeX 的唯一输入，
生成文件不作为数据入口，也不直接手改。

```bash
PY=/Users/chen/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3

# 检查本机是否具备全部必需字体
"$PY" templates/midterm/latex/render.py --check-fonts

# 同时生成 DOCX、LaTeX 和 PDF
"$PY" templates/midterm/render.py \
  --data templates/midterm/fixtures/normal.json \
  --output-dir tmp/midterm-normal \
  --overwrite --compile

# 需要时也可以只生成 DOCX；不会启动 Word 或 WPS
"$PY" templates/midterm/render.py \
  --data templates/midterm/fixtures/normal.json \
  --output-dir tmp/midterm-normal-word \
  --format word --overwrite
```

统一入口生成 `midterm.docx` 与 `latex/main.pdf`；后者是快速排版验收件，DOCX 必须最后在
Microsoft Word 或 WPS 中检查。图片路径相对于数据 JSON 所在目录解析，远程 URL 会被拒绝。

## 回归测试

```bash
PY=/Users/chen/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3
"$PY" templates/midterm/test.py
```

测试同时覆盖最短、正常、长字段、长正文含图片和四级混合列表五类 fixture，并检查 Word 结构、字体字号、
颜色、居中与缩进、列表、上下标、图片替代文本，以及 LaTeX 的字体嵌入、A4 页面、表格几何、
分页闭合边框和中文字形门禁。该测试通过不等于 Word/WPS 目标编辑器验收通过。
