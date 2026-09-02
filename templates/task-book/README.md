# 2026 届本科毕业论文（设计）任务书模板

本目录使用一份结构化 JSON 同时驱动 Word 与 LaTeX/PDF。当前格式权威为学校发布材料中的
`2025届毕业论文任务书-样例修正版(1).docx`；历史二进制 DOC 仅作辅助参考。

“基本内容与要求”和“需收集的资料”已支持公共结构化内容块：`data_table` 使用显式
行列数据、列宽权重和对齐方式；`figure_group` 支持 2–4 张本地图片、自动子图标记、
统一图号与总题注；`equation` 使用受限表达式树生成 Word 原生 OMML 与同源 LaTeX 公式，
不接受原始 TeX/MathML/OMML。Word 与 LaTeX/PDF 使用同一份数据，示例见
`fixtures/structured-content.json`。

## 统一数据入口

- `schema/task-book.schema.json`：公开 JSON 契约；
- `python/model.py`：渲染前的严格校验与确定性规范化；
- `spec/fixed-content.json`：封面、六条须知、分区标题、选项和签名标签；
- `spec/layout.json`：字体、字号、页面、表格、间距和签名留白令牌；
- `spec/artifact.md`：修正版 DOCX 的取证、槽位和验收规格；
- `fixtures/`：不含真实学生信息的公开压力数据。

Word 与 LaTeX 渲染器必须先调用同一个接口：

```python
import importlib.util
from pathlib import Path
import json

model_path = Path("templates/task-book/python/model.py").resolve()
spec = importlib.util.spec_from_file_location("task_book_model", model_path)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)

raw = json.loads(Path("task-book.json").read_text(encoding="utf-8"))
data = module.validate_data(raw)
```

由于目录名包含连字符，渲染器应按文件路径加载 `python/model.py`，或由统一入口导入；不得
在两个渲染器内复制校验逻辑。

## 数据规则

- `metadata.title` 和正文支持显式 `runs`，每个 run 可设置 `script`、`bold`、`italic`；
- 基本内容和需收集资料支持段落、有序/无序列表、最多四级 `children` 嵌套和本地图片；
- 列表层级来自结构而非空格或 Tab；旧式扁平 `ordered_list` 与自定义 `marker` 继续有效；
- 进度安排由 `period` 与富文本 `content` 组成，不用空格或 Tab 分列；
- 进度渲染为普通段落；以日期开头时可不缩进，其他情况首行缩进两个字符；
- 参考文献每条独立，使用无首行缩进的专属样式；
- 选题性质、来源、科研项目级别和自拟人均使用条件枚举；
- 指导教师只写姓名，不能附带职称；教师签名和学院领导意见不属于输入数据。

## 字体与验收

任务书需要华文行楷、黑体、宋体和 Times New Roman；Word 版的空心勾选框另外需要
`Wingdings 2`。缺少字体时必须停止生成，不能使用
系统默认字体替换。仓库中的 `STXingkai.ttf` 可供 XeLaTeX 使用；生成 Word 前仍应把华文
行楷安装到系统字体目录。中易黑体、中易宋体和 Times New Roman 应从已有合法授权的
Windows、Office、WPS 或学校软件环境取得；`Wingdings 2.ttf`（Windows 上也可能名为
`Wingdng2.ttf`）同样需要先安装。项目不额外分发这些商业字体。LaTeX 版的勾选框由矢量
线条绘制，不依赖 `Wingdings 2`。

开发阶段优先编译 LaTeX/PDF；Word 路径只生成 DOCX，不自动启动 Word 或 WPS。结构检查、
中文字形、逐页版式和 Word/WPS 验收保持为四个独立状态。

## 生成命令

以下命令从仓库根目录执行。`normal.json` 只是公开虚构示例；实际使用时应复制一份 JSON，
按 Schema 填写，而不是编辑生成的 DOCX 或 TeX 数据文件。

```bash
PY=/Users/chen/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3

# 同时生成 DOCX、LaTeX 源码与 PDF
"$PY" templates/task-book/render.py \
  --data templates/task-book/fixtures/normal.json \
  --output-dir tmp/task-book-normal \
  --overwrite --compile

# 只走快速迭代的 LaTeX/PDF 路径
python3 templates/task-book/render.py \
  --data templates/task-book/fixtures/normal.json \
  --output-dir tmp/task-book-latex \
  --format latex --overwrite --compile

# 只生成 DOCX；不会启动 Word 或 WPS
"$PY" templates/task-book/render.py \
  --data templates/task-book/fixtures/normal.json \
  --output-dir tmp/task-book-word \
  --format word --overwrite
```

统一入口的主要结果是 `task-book.docx` 与 `latex/main.pdf`。图片路径相对于输入 JSON
所在目录解析，远程 URL 会被拒绝。

## 回归测试

```bash
PY=/Users/chen/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3
"$PY" templates/task-book/test.py
```

测试覆盖公开虚构 fixture（包括参考文献跨页、最终签署区、临近分页的图片及其题注和后续正文）、
模型负向约束、封面四行字段与一行/两行题目对齐、Word 结构与字体、
须知 1.5 倍行距、连续表格与上下内边距、空心框内勾选、项目编号横线、自拟题目纵列、
签名与日期横线、富文本、上下标、图片、四级有序/无序混合列表、长短字段、LaTeX 跨页闭口、字体嵌入、
A4 几何、文本顺序和中文字形门禁。
测试通过不等于 Microsoft Word 或 WPS 目标编辑器验收通过。

真实历史材料、OCR、签名、教师意见和生成结果只能保存在 `references/private/` 或 `tmp/`，
不得复制到 fixture 或提交到 Git。
