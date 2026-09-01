# 过程文档公共层

本目录保存开题报告、任务书、中期检查、诚信声明和毕业论文可复用的内容语义、字体政策
和检查工具。具体文档的列宽、行高、边框尺寸、签名区和字段映射仍放在对应模板的
`spec/` 目录中。

## 内容

- `schema/content-block.schema.json`：富文本运行、段落、有序/无序列表及最多四级
  `children` 嵌套的公共 Schema；`textContentBlock` 不含图片，供只接受文字的官方栏目使用；
- `typography/chinese-sizes.json`：中文字号名称到确定点值和 LaTeX `zihao` 的映射；
- `typography/font-policy-2026.json`：宋体、黑体、楷体、华文中宋、华文行楷和
  Times New Roman 的角色与字体文件政策；
- `python/content.py`：富文本校验、列表树规范化、文本宽度和旧式括号列表兼容解析；
- `python/typography.py`：公共字体政策与文档专属排版令牌加载器；
- `python/font_files.py`：按文档实际使用的字体角色解析授权字体文件，禁止静默回退；
- `python/process_form.py`：校验三类过程文档共有的版式令牌，并把公共 LaTeX 表单皮肤
  复制到可独立编译的导出 bundle；
- `python/outline_numbering.py`：学校允许的五种目录编号格式、中文序数和最多六级的
  结构校验；中期检查与未来毕业论文目录共用该实现；
- `python/pdf_geometry.py`：PDF 字符包围盒、居中和边线栅格断言。
- `latex/sztu-process-form.tex`：连续边框、可跨页正文分区、固定分区和紧密拼接的公共实现；
- `fixtures/pasted-scientific-text.json`：Word/WPS 粘贴中常见的 Unicode
  上下标与摄氏度符号回归样例。

公共规则的解释和使用边界见
[`docs/TEMPLATE_ENGINEERING_GUIDE.md`](../../docs/TEMPLATE_ENGINEERING_GUIDE.md)。

新模板必须实际引用公共层；禁止复制一份公共代码后在文档目录中独立演化。

从 Word、WPS 或文献网站粘贴的 Unicode 上下标字符（如 `CO₂`、`R²`）
必须在内容规范化阶段转换为普通字符与 `script=sub/super` 运行属性；
不得把兼容字形直接交给宋体或 LaTeX 正文字体渲染。`℃` 同样在该阶段
规范为跨 Word/PDF 字体可用的 `°C`。

宋体、黑体等官方中文字体文件通常只提供 Regular 字形。富文本运行中的
`bold=true`、`italic=true` 及两者组合仍必须同时作用于中文和西文：Word 输出写入
明确的粗体/斜体运行属性；XeLaTeX 输出统一使用公共字体选项生成确定性的仿粗体和
仿斜体，不允许只让 Times New Roman 西文字形发生变化。该规则只响应用户显式设置
的富文本属性，不改变模板本身规定的字号、字体角色或固定栏目样式。

## 回归检查

```bash
python3 templates/common/test.py
```
