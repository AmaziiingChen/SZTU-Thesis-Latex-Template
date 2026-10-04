# 深圳技术大学本科毕业论文 LaTeX 工程

这是按本项目收录的 2026 届规范校准的论文写作起点。解压后，把整个文件夹交给 LaTeX 编辑器或你的 Agent；始终编译 `sztuthesis_main.tex`。包内的姓名、题目、摘要和正文都是占位内容，不能直接提交。

## 第一次使用

1. 完整解压 ZIP，不要在压缩包内编辑。路径建议简单清楚，例如 `Documents/MyThesis`。
2. 安装 TeX Live（Windows/Linux）或 MacTeX（macOS），确认包含 XeLaTeX、BibTeX 和 latexmk。字体检查脚本需要 Python 3.10 或更新版本，只使用标准库。
3. 准备合法获得的宋体、黑体、楷体、华文中宋，以及 Times New Roman 的常规、粗体、斜体、粗斜体。字体不随本包分发。可安装到系统，也可放入本工程的 `fonts.local/`。
4. 在本工程文件夹打开终端，执行一次完整编译：

```bash
# macOS / Linux
python3 scripts/build_thesis.py
```

```powershell
# Windows PowerShell
py -3 scripts/build_thesis.py
```

脚本先检查字体，再生成 `sztuthesis_main.pdf`。若字体放在其他目录，在上述命令后加 `--font-dir "你的字体目录"`。只检查环境时加 `--check-fonts`。检查会保存本机字体路径；换电脑后重新运行，不要把旧的 `sztu-fonts.local.tex` 复制过去。

首次检查通过后，可以在 Texifier、TeXstudio 或 VS Code LaTeX Workshop 中选择 XeLaTeX 和 BibTeX 编译。随包的 `.vscode/settings.json` 提供 latexmk 与手动四步编译方案。没有完整编译链时，目录、文献或交叉引用可能仍是旧结果。

## 写作时改哪些文件

| 文件 | 填写内容 |
| --- | --- |
| `content/info.tex` | 中英文题名、姓名、学号、学院、专业、导师及提交日期 |
| `content/abstractcn.tex` | 中文摘要、中文关键词 |
| `content/abstracten.tex` | 英文摘要、英文关键词 |
| `content/content.tex` | 正文章节、图表、公式与引用 |
| `thesis-references.bib` | 经核实的参考文献 |
| `content/additional.tex` | 致谢 |
| `content/appendix_example.tex` | 可选附录；保留纯注释时不生成附录页 |
| `images/` | 自己的插图；保留封面使用的 `school_title.pdf` |

`.tex` 中 `%` 后面的文字是注释，不会进入 PDF。注释解释命令作用和注意事项；替换正文占位时应保留外层环境。不要编辑 `.aux`、`.toc`、`.bbl` 等编译产物。

`SZTUthesis.cls` 负责学校版式，`sztuthesis_main.tex` 负责装订顺序。普通写作通常不需要修改它们。页边距、字号或学校固定文本需要变化时，先核对当届正式要求，并记录变更依据。

## 让 Agent 协助

把工程文件夹作为 Agent 的工作区，要求它先读 `AGENTS.md` 和本说明。例如：

> 请先阅读 README.md、AGENTS.md 和 content/ 下的注释。根据我提供的正文组织章节、插入图表和引用，保留研究事实。只改本次涉及的内容文件，完成后编译并检查错误、引用和分页。遇到缺数据或缺文献时列出待补项，不自行编造，也不要缩小学校规定的字号来塞内容。

Agent 是否自动读取 `AGENTS.md` 取决于工具，必要时主动指定。默认不要上传未公开论文、数据和个人资料到外部服务；如使用云端 Agent，应由你决定输入范围。

## 编译失败时

- **找不到 xelatex 或 latexmk**：检查 TeX Live/MacTeX 安装和终端 PATH，重新打开终端或编辑器。
- **缺字体**：运行 `scripts/build_thesis.py --check-fonts` 查看缺失项；安装或指定字体目录。不要改成另一种字体让错误消失。
- **Missing $ inserted / Undefined control sequence**：先看日志中第一个错误及对应源码行；常见原因是正文中 `_`、`&`、`%` 没有转义，或命令拼错。
- **引用显示问号**：核对 `\cite{key}` 与 `.bib` 的 key，再执行完整编译。图表 `\label` 放在 `\caption` 后。
- **Overfull / Missing character**：检查超宽表格、长 URL、路径或缺字。不要删除研究内容、压缩边距或隐藏日志。
- **已有 PDF 没变化**：失败编译可能留下旧 PDF，先检查命令是否成功和文件修改时间。

更多常用代码和排错方法见 `docs/写作与排版.md`。包中的 `template-manifest.json` 记录原始文件哈希，仅用于识别下载版本；你开始写作后文件变化是正常的。

## 提交前检查

删除所有占位信息，核对摘要与正文、图表单位、公式符号和引用来源。按当前收录规范核对参考文献不少于 10 篇、外文不少于 2 篇；编译成功不会自动检查这些内容要求。逐页查看 PDF 的封面、目录、摘要、图表、文献和页码，再按学院要求完成签署与导师审核。

本包生成 PDF，不承诺 Word 导出或自动匿名评审。适用年份为 2026，后续年份需重新核对学校通知。自动编译、中文字形检查、逐页版式和目标编辑器验证是不同结果，不能互相替代。

模板代码来源、修改范围和许可见 `NOTICE.md` 与 `LICENSE`。
