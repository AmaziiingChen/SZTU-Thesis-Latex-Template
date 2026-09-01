# 2026 届开题报告模板（工程原型）

本目录同时维护 Word 与 LaTeX 两条输出路径。当前优先完成 Word 基准、统一数据
Schema 和确定性渲染器；签名与审核意见不由程序填写。

## 开发阶段的迭代方式

- 优先使用 LaTeX 快速迭代，并完成编译、字体、中文字形和逐页视觉检查。
- Word 路径只生成 DOCX，由项目负责人在 Microsoft Word 或 WPS 中人工检查并反馈。
- 日常修改不自动启动 Word/WPS，也不反复导出 Word PDF；仅在模板定版或关键验收节点
  进行完整的目标编辑器复核。

## 目录

- `word/official-template.docx`：Microsoft Word 从学校官方 `.doc` 原样转换的基准。
- `references/official/…/2 2026届开题报告.pdf`：当前官方排版基准（仓库外本地参考）。
- `schema/proposal.schema.json`：Agent 和渲染器共用的数据契约。
- `spec/layout.json`：本模板专属字体角色、字号、段落、边框、页边距和签署区令牌。
- `fixtures/`：短、正常、长内容及顶部信息表压力测试数据。
- `spec/artifact.md`：从 OOXML 蒸馏出的版式与字段映射。
- `word/render.py`：从 JSON 生成 DOCX 的确定性渲染器。
- `latex/main.tex`、`latex/render.py`：读取同一份 JSON 的 XeLaTeX 原型。

富文本校验、括号列表兼容解析、字号映射、字体文件政策和 PDF 几何断言来自
`templates/common/`。任务书和中期检查必须复用同一公共层，不复制这些实现。

## 生成 Word 文档

请使用项目工作区依赖中的 Python，或安装了 `python-docx` 的 Python 3：

```bash
python3 templates/proposal/word/render.py \
  --data templates/proposal/fixtures/normal.json \
  --output tmp/proposal-normal.docx
```

如需覆盖已有输出，显式添加 `--overwrite`。渲染器会检查 Schema 关键约束、官方
表格结构以及生成文件能否重新打开。

## Agent 边界

Agent 只生成符合 `proposal.schema.json` 的 JSON 内容，不直接操作 Word 表格。
渲染器负责把数据放入固定槽位。题目、姓名、学号、专业、学院、指导教师只填写一次，
两条输出路径共同使用；指导教师字段只写姓名，不写“老师/教授”等职称。学生签名、
指导教师意见和学院领导意见保持为空，
供后续打印签署和扫描上传。

题目和正文既可直接写字符串，也可用 `runs` 表达上下标、粗体和斜体。例如：

```json
{"runs": [{"text": "g-C"}, {"text": "3", "script": "sub"}, {"text": "N"}, {"text": "4", "script": "sub"}]}
```

化学式、数学符号或物理量中的上下标必须使用 `script: "sub"` 或
`script: "super"`，不要直接输入 Unicode 下标字符，也不要把需要上下标的题目退化为
`H2O2`、`g-C3N4` 等基线数字。相同规则后续适用于任务书、中期检查表和毕业论文的
所有可编辑字段。

正文中的每个独立段落默认首行缩进两个字符。研究内容、方法和步骤支持显式
`ordered_list`、`unordered_list` 与最多四级 `children` 嵌套；旧式方法或步骤段落数组
仍按原规则自动编号。方法或步骤中需要兼容旧数据的二级有序列表时，也可在
同一个字符串中使用连续的 `（1）`、`（2）`、`（3）` 标记；渲染器会将各子项分别成段。
如果最后一个子项后还有普通说明段，请用换行明确分隔，例如：

```json
"对比分析法……具体包括：\n（1）第一项；\n（2）第二项；\n（3）第三项。\n通过上述比较确定最终方案。"
```

最后一行会恢复为普通正文缩进，不会被并入“（3）”子项。

## 生成 LaTeX/PDF

### 必需字体（禁止自动替换）

LaTeX 模板严格使用学校官方 PDF 中的三套字体：

- 中文正文和信息内容：`SimSun`（中易宋体）；
- 中文标题和表格标签：`SimHei`（中易黑体）；
- 英文、数字：`Times New Roman`。

模板会在编译开始时检查这三套字体。缺少任意字体时 XeLaTeX 会直接报错并停止，
不会回退到苹方、华文宋体、Fandol 或其他系统默认字体。

Windows 安装 Microsoft Office 后通常已包含这些字体；macOS 需要在“字体册”中安装
具有合法授权的 `SimSun`、`SimHei` 和 `Times New Roman` 字体文件。常见文件名包括
`simsun.ttc`/`simsun.ttf`、`simhei.ttf` 和 Times New Roman 字体族文件。项目不分发
这些商业字体文件，使用者应从已获许可的 Windows/Office 安装或学校提供的软件环境
中取得。安装后请在项目根目录运行严格字体预检：

```bash
python3 templates/proposal/latex/render.py --check-fonts
```

预检会输出实际采用的六个字体文件路径，包括宋体、黑体，以及 Times New Roman 的
常规、粗体、斜体和粗斜体文件；缺少任何一个文件都会失败。若字体安装在非标准目录，
可以用 `SZTU_FONT_DIR` 指定目录，或使用 `SZTU_SIMSUN_FONT`、
`SZTU_SIMHEI_FONT`、`SZTU_TIMES_REGULAR_FONT` 等环境变量指定单个文件。

也可以把具有合法授权的字体放入本地目录 `templates/proposal/fonts.local/`。该目录已被
Git 忽略，禁止将商业字体提交到开源仓库。TeXstudio 的编译器必须选择 XeLaTeX；
pdfLaTeX 不能使用该模板配置。

```bash
python3 templates/proposal/latex/render.py \
  --data templates/proposal/fixtures/normal.json \
  --output-dir tmp/proposal-latex-normal \
  --compile
```

LaTeX 路径当前是版式原型，使用 XeLaTeX。所有内容统一采用自然跨页布局，不按字数
切换另一套页面结构，也不缩小正文字号。它与 Word 路径共享相同 Schema，但仍需经过
教师审核，以及后续 Windows + TeXstudio 复核。

## 回归测试

请使用含 `python-docx` 的 Python 运行：

```bash
python3 templates/common/test.py
python3 templates/proposal/test.py
```

第一条命令检查公共富文本、字号与字体政策、括号列表拆分和 Schema 引用；第二条命令
会生成五组 Word 文档，编译五组 LaTeX/PDF，检查结构、四级混合列表、自然分页、上下标、中文字体
可见性，以及双倍长度题目、长专业、长学院和超长参考文献的换行与对齐。
Word/WPS 的最终分页与视觉检查仍需在对应办公软件中完成。
