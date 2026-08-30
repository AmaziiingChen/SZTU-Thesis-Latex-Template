# 过程文档公共层

本目录保存开题报告、任务书、中期检查、诚信声明和毕业论文可复用的内容语义、字体政策
和检查工具。具体文档的列宽、行高、边框尺寸、签名区和字段映射仍放在对应模板的
`spec/` 目录中。

## 内容

- `schema/content-block.schema.json`：富文本运行、段落和显式列表的公共 Schema；
- `typography/chinese-sizes.json`：中文字号名称到确定点值和 LaTeX `zihao` 的映射；
- `typography/font-policy-2026.json`：宋体、黑体和 Times New Roman 的角色与字体文件政策；
- `python/content.py`：富文本校验、文本宽度和旧式括号列表兼容解析；
- `python/typography.py`：公共字体政策与文档专属排版令牌加载器；
- `python/font_files.py`：按文档实际使用的字体角色解析授权字体文件，禁止静默回退；
- `python/pdf_geometry.py`：PDF 字符包围盒、居中和边线栅格断言。

公共规则的解释和使用边界见
[`docs/TEMPLATE_ENGINEERING_GUIDE.md`](../../docs/TEMPLATE_ENGINEERING_GUIDE.md)。

新模板必须实际引用公共层；禁止复制一份公共代码后在文档目录中独立演化。

## 回归检查

```bash
python3 templates/common/test.py
```
