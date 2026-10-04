# 四类评审与成绩表：源码及本地依赖

四类模板共用 `python/assessment_forms.py`、`python/assessment_latex.py`、
`python/assessment_word.py` 与 `schema/writing-guidance.schema.json`。
各自目录包含模型入口、schema、Word/LaTeX 渲染入口、版式规格及虚构回归样例：

| 应用类型 | 模板目录 |
| --- | --- |
| `advisor_review` | `templates/advisor-review` |
| `reviewer_review` | `templates/reviewer-review` |
| `defense_record` | `templates/defense-record` |
| `grade_assessment` | `templates/grade-assessment` |

## 换机后准备

1. 拉取模板仓库 `codex/thesis-workbench` 分支。应用开发工作树默认读取同级 `Thesis`；也可在应用中选择此模板工程。
2. 按各模板 `spec/artifact.md` 核对官方来源，并准备经过项目核对的本地 Word 底稿：
   - `templates/advisor-review/word/official-template.docx`
   - `templates/reviewer-review/word/official-template.docx`
   - `templates/defense-record/word/official-template.docx`
   - `templates/grade-assessment/word/official-template.docx`
3. 按模板 README 准备 Python 依赖、XeLaTeX/Poppler 和合法字体。不要把字体或机器字体配置提交到仓库。

这四份 DOCX 按现有规格及 `.gitignore` 留在本地，Git 拉取不会提供。Word 渲染器保留它们的
结构；截至应用提交 `f0ba179`，应用的模板快照清单也无条件要求它们存在，因此即使只在应用中
预览 PDF，也必须先补齐。直接调用 LaTeX 渲染入口则不读取 Word 底稿。不能把源码已推送表述
成目标机器已经具备全部运行依赖，也不要将未经验证的任意转换件当作兼容底稿。

## 2026-10-04 推送前复核

- 新纳入 Git 的内容为四类模板源码、规格、虚构 fixtures、共享模块、schema、回归脚本及底稿忽略规则。
- 模板测试通过：74 项基础数据/容量断言、24 份可编辑标题契约、20 份指导文字契约，以及学院/专业、成绩、答辩字段和题目行距契约。
- Python 语法、JSON 解析及相对 schema 依赖均通过。
- 将暂存源码导出到独立目录，额外放入本机四份底稿；对应用已提交版本 `f0ba179` 运行
  `backend/tests/test_assessment_forms.py`，18 项全部通过，包含四类模板的隔离快照和 Word 输出结构检查。
- 本轮是源码补齐和集成检查，未重新进行逐页视觉或 Word/WPS 验收；各模板 QA 保留此前证据及限制。
