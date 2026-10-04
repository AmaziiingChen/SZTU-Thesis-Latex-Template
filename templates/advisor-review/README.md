# 一页评审表模板

本模板优先生成基本信息预填、下半部留白的 A4 PDF，供现场打印和手写。评审区可提前填写，Word 和 LaTeX 源码为附加导出。所有区域尺寸、字号和签署坐标见 `spec/layout.json`，禁止用缩字号、裁剪或新增第 2 页处理超量内容。超量返回 `SINGLE_PAGE_OVERFLOW`。

`fixtures/` 全为虚构数据，包含空白、常规填写、四级富文本列表、容量边界和超量输入。基础信息必填，导师/评阅人/现场信息可以留空。建议成绩保留文本，最终成绩非负十进制四舍五入为整数。日期使用真实的 `YYYY-MM-DD`，输出年月日。

## 本地官方 Word 底稿

`word/official-template.docx` 不提交 Git。需由当前学校官方 `.doc` 在本地转换后保存；原始权威文件和 SHA-256 见 `spec/artifact.md`。转换件只提供结构，最终版式以 Word/WPS 为准。所需宋体、黑体和 Times New Roman 字体从本机授权字体位置解析，缺失即停止，不自动替换。

## 生成与检查

使用 Codex bundled Python（见 dependency loader）：

```sh
python templates/advisor-review/latex/render.py --data templates/advisor-review/fixtures/blank.json --output-dir tmp/advisor-review-blank --compile
python templates/advisor-review/word/render.py --data templates/advisor-review/fixtures/blank.json --output tmp/advisor-review-blank.docx
python templates/common/test_assessment_forms.py
python templates/common/test_assessment_forms.py --render --output-dir tmp/assessment-regression
```

结构、中文字形、逐页版式和 Word/WPS 验证分别记录。开发版本不宣称模板成熟，真实历史样例和目标编辑器验收按实际证据补充。

可编辑写作提示：`sections.editable_headings=true` 时提示是实际正文，可改、可删。三个评审/考核表用 comments，指导教师表另用 division_of_work，答辩表用 comments作为questions上方的intro。首段无用户marks且全文等于spec提示时保留官方混排；其他文本按共享正文。省略或false保持旧静态提示行为。`--editable-render` 回归24份合成样例，不含真实学生数据。


推荐新调用使用 `sections.writing_guidance`，把说明与普通正文分开。comments用于三种评审/考核表指导文字，advisor另用division_of_work，defense用questions保留原完整指导段。值为字符串或富文本paragraph；null、空字符串、空runs删除指导。固定标题始终保留官方黑体14pt常规字重，普通正文独立宋体10.5pt和两字首行缩进，指导中的用户bold/italic/super/sub仍有效。缺map/key维持上面的legacy/v1兼容。`--guidance-render`回归20份合成样例。
