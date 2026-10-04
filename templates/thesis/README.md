# 2026 届本科毕业论文（设计）LaTeX 校准版

本目录记录仓库根目录论文模板的校准规格与回归方法。学校当前发布的 Word 范例和书面
撰写规范是格式权威；五份本地历史论文只用于验证真实分页、页眉切换及图表压力场景，
不会复制到公开测试数据，也不会被修改或提交。

## 编辑入口

- `content/info.tex`：题名、作者、学院、专业、导师及日期；
- `content/abstractcn.tex`：中文摘要和关键词；
- `content/abstracten.tex`：英文摘要和关键词；
- `content/content.tex`：论文正文；
- `thesis-references.bib`：参考文献；
- `content/additional.tex`、`content/appendix_example.tex`：致谢和附录。

版式由根目录的 `SZTUthesis.cls` 和 `sztuthesis_main.tex` 统一控制。学生内容不应通过空格、
Unicode 上下标、手写页码或手工图表编号模拟格式。

## 必需字体

校准版要求精确使用以下字体，缺少时会停止编译，不允许静默替换：

- 宋体：SimSun；
- 黑体：SimHei；
- 楷体：KaiTi；
- 中文论文题名：STZhongsong；
- 西文：Times New Roman。

商业字体不进入 Git。macOS 用户可把已有合法授权字体安装到“字体册”；仓库的 `build.sh`
还会读取用户字体目录、系统字体目录以及 Microsoft Word 或 PowerPoint 的 `DFonts` 目录。Texifier 若无法
发现 Office 自带的 `Kaiti.ttf`，应先用“字体册”安装该字体，随后重新启动 Texifier。
Windows/TeXstudio 需要先在系统中安装同名字体。

## 编译

在仓库根目录执行：

```bash
bash build.sh --clean
```

编译器必须为 XeLaTeX；参考文献需要 BibTeX，`latexmk` 会自动完成所需轮次。开发阶段优先
检查 PDF，最终提交前仍需分别记录 macOS Texifier 与 Windows TeXstudio 的编译结果。

## 关键分页规则

- 封面、诚信声明和目录不显示页眉页脚；
- 中文摘要从罗马数字 `I` 开始，整页不显示页眉文字，也不绘制页眉横线；
- 英文摘要自然续排为 `II`、`III` 等，并从第一页起显示论文页眉和横线；
- 正文另起一页，页码重新从阿拉伯数字 `1` 开始；
- 正文页脚为 `第 x 页 共 y 页`，不使用中文逗号。

完整测量值见 `spec/artifact.md` 和 `spec/layout.json`。

## 公式、摘要、题注与参考文献

- 公式使用按章连接号编号，例如 `(2-1)`；使用 `equation`、`align` 等数学环境自动编号，
  不要手写编号或改成 `(2.1)`。
- 摘要正文标签为 `【摘要】`、`【关键词】`、`【Abstract】`、`【Key words】`；目录中的
  对应条目仍为不带括号的 `摘要` 和 `Abstract`。
- 图题和表题末尾不加句末标点。图题放在图下，表题放在表上，编号与交叉引用均由 LaTeX
  自动生成。
- 参考文献写入 `thesis-references.bib`，正文使用 `\cite{bibkey}`。模板固定使用
  GB/T 7714—2015 数字顺序制，按首次引用顺序生成文末条目；连续引用会压缩，不连续引用
  会排序，文末长条目自动使用悬挂续行。
- 参考文献条目之间没有额外空行；中文为五号楷体，英文和数字为五号 Times New Roman，
  1.5 倍行距。长 DOI 与 URL 可以自然断行。为避免跨物理页的 PDF 外链注释损坏，文末
  DOI/URL 保留可复制文本但不创建外部超链接。
- 提交前仍需检查文献不少于 10 篇、外文不少于 2 篇，并确认每一条都在正文真实引用；不要
  用 `\nocite{*}` 自动混入没有引用的资料。

## 回归测试

```bash
python3 templates/thesis/test.py
```

测试会分别在唯一 jobname 和独立输出目录中冷启动编译主论文与公开合成参考文献压力样例，
拒绝复用仓库根目录的陈旧 `.bbl`。检查范围包括 A4、精确字体嵌入、摘要正文/目录标签、
页眉横线、罗马与正文页码、公式连接号、题注末标点、GB/T 7714—2015 条目顺序与类型、
连续/不连续/重复引用、双位编号、跨页悬挂续行、条目间距、长 DOI/URL 右边界、编译告警和
中文字形。通过测试只代表结构与 LaTeX/PDF 门禁通过，不代表教师审核、Texifier 或
TeXstudio 验收完成。

## 字体检查与换机

编译前运行 `bash build.sh --check-fonts`；已有字体目录可用 `--font-dir "/字体目录"` 指定并记住。新电脑设置、编辑器使用与测试文件位置见[字体使用指南](../../docs/FONTS.md)。

## 学生下载包

桌面端分发完整可编译的源码 ZIP，学生在自己的编辑器或 Agent 中写作。维护仓库的
`content/` 保留回归演示；下载包用 `starter/` 的占位稿覆盖，不把演示作者或历史论文交给学生。
`package/` 维护中文使用说明、Agent 约定和写作示例，`package/files.json` 是唯一打包清单。

```bash
python3 scripts/build_thesis_package.py --output output/thesis/sztu-thesis-2026.zip --overwrite
python3 scripts/test_thesis_package.py
```

ZIP 包括版式引擎、学校题字、文献样式、内容片段、跨平台编译脚本、共享字体检查与中文说明；
排除商业字体、本机配置、旧 PDF、私有学生资料和历史样本。ZIP 内记录逐文件哈希，旁边的 JSON
记录版本、字节数和 SHA-256，供桌面端保存前检查。文件变化时需重建 ZIP 与 JSON，不手改两者。
学生入口是解压后的 `README.md`，编译入口是 `python3 scripts/build_thesis.py`（Windows 用 `py -3`）。
