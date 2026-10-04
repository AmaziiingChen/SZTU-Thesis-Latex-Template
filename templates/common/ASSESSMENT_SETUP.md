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
2. 四份空白 Word 底稿已随分支提供，可按各模板 `spec/artifact.md` 核对来源及哈希：
   - `templates/advisor-review/word/official-template.docx`
   - `templates/reviewer-review/word/official-template.docx`
   - `templates/defense-record/word/official-template.docx`
   - `templates/grade-assessment/word/official-template.docx`
3. 按模板 README 准备 Python 依赖、XeLaTeX/Poppler 和合法字体。不要把字体或机器字体配置提交到仓库。

这四份 DOCX 已按用户明确授权纳入 Git，“只在本地保存”的旧约定已废止。拉取分支即可取得
渲染器、规格和底稿。Word 渲染器保留底稿结构，应用的模板快照也会读取它们；无需额外寻找或转换
这四份文件。Python、TeX、Poppler 和合法字体仍按功能需要在目标机器准备。

## 2026-10-04 推送前复核

- 新纳入 Git 的内容为四类模板源码、规格、虚构 fixtures、共享模块、schema、回归脚本及底稿忽略规则。
- 模板测试通过：74 项基础数据/容量断言、24 份可编辑标题契约、20 份指导文字契约，以及学院/专业、成绩、答辩字段和题目行距契约。
- Python 语法、JSON 解析及相对 schema 依赖均通过。
- 将暂存源码导出到独立目录，额外放入本机四份底稿；对应用已提交版本 `f0ba179` 运行
  `backend/tests/test_assessment_forms.py`，18 项全部通过，包含四类模板的隔离快照和 Word 输出结构检查。
- 本轮是源码补齐和集成检查，未重新进行逐页视觉或 Word/WPS 验收；各模板 QA 保留此前证据及限制。

## 2026-10-04 底稿补齐

用户明确要求将四份空白 Word 底稿一并上传。已移除四条忽略规则，同步更新 AGENTS、各模板 README、
规格及本说明。提取的正文只有表单固定标签和填写说明，无学生填写信息；未发现批注、修订、图片或嵌入文件。
底稿二进制保持原样，SHA-256 记录于各自规格。历史“补入本机底稿后通过”的测试记录保留为当时证据。

本轮从 Git 暂存内容直接导出全新模板工程，未额外拷入任何底稿；应用已提交版本的 18 项 assessment 集成测试全部通过，确认四份底稿与共享依赖均由仓库提供。
