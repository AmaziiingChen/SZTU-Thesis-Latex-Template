# 本地待提交整理与验收记录（2026-09-20）

本次在 `feat/project-bootstrap`（起点 `4c9ebe6`）上整理已有改动，并完成公共能力、开题报告、任务书、中期检查表及论文的完整自动回归。未执行暂存、提交或推送。

## 建议提交分组

| 顺序 | 范围 | 内容 |
| --- | --- | --- |
| 1 | `.gitignore`、`Makefile`、`docs/PROJECT_PLAN.md` | 忽略本地输出和工作目录；构建失败正确返回；统一字体门禁说明 |
| 2 | `templates/common/`、`templates/proposal/`、`templates/task-book/`、`templates/midterm/` | 结构化内容、富文本及列表能力，文档规格、渲染器和回归一起提交 |
| 3 | `SZTUthesis.cls`、`sztuthesis_main.tex`、`content/` 的现有变更、`build.sh`、`README.md`、`templates/thesis/` | 论文官方规格校准、严格字体加载、参考文献压力样例与隔离回归 |
| 4 | 本记录 | 保存验收范围及证据索引 |

`scripts/mineru_batch_parse.py` 与 `scripts/organize_mineru_markdown.py` 单独归为 OCR 工具候选，不混入模板修复提交；本次没有执行远端 OCR 验收。

根目录已有修改的 `sztuthesis_main.pdf`、未跟踪的 `references/论文写作工具箱.xmind` 保留待单独确认。测试输出、字体和真实学生材料不纳入提交。完整文件清单在本地 `tmp/acceptance-20260920/pending-files.json`。

## 本次验收发现并修复

- 任务书：封面题名可用宽度扣除两侧单元格边距，避免 WPS 多换行后将封面信息挤到下一页。
- 中期表：取消继承的自动编号，避免 `1、1、`；保持固定评价文字加粗；签名区用明确缩进定位；评价标题与首项同页。
- 开题报告：图片与题注组成同一不可拆分段落，避免 WPS 跨页表格中题注脱离图片。
- 以上版式修复均同步规格、实现、复现样例及自动断言，保留规定字号、间距和签名空间。
- 论文：字体搜索增加本机 PowerPoint 的 `DFonts`。本机存在 `Kaiti.ttf`，先前失败来自搜索范围遗漏，并非机器没有楷体。现有旧 PDF 也嵌入了 KaiTi。保持当前校准规格的精确字体要求，不静默替换。
- Makefile：移除忽略 latexmk 失败的前缀；模拟失败已验证会返回非零退出码。

## 自动回归

使用可导入 Pillow、python-docx 等依赖的 Python 3，依次运行：

```sh
python3 templates/common/test.py
python3 templates/proposal/test.py
python3 templates/task-book/test.py
python3 templates/midterm/test.py
python3 templates/thesis/test.py
```

五套均通过。论文执行独立目录冷启动，主论文 25 页、参考文献压力样例 3 页。证据保存在 `tmp/acceptance-20260920/`：

- `common-after.log`
- `proposal-after.log`
- `task-book-after.log`
- `midterm-final.log`
- `thesis-after.log`
- `make-failure.log`

## 文档门禁

| 范围 | 内容提取 | 中文字形有效 | 逐页版式检查 | 目标编辑器 |
| --- | --- | --- | --- | --- |
| 开题、任务书、中期表共 30 个公开样例 | 通过 | 通过 | 120 页覆盖 | WPS 原生 PDF 导出后复核通过 |
| 论文主样例 | 通过 | 通过 | 25 页通过 | Texifier 1.9.32 (850)，外部 XeLaTeX + BibTeX，0 错误、0 警告 |
| 参考文献压力样例 | 通过 | 通过 | 3 页通过 | 独立 Texifier 编译未验证；TeX Live/XeLaTeX 回归通过 |

所有最终 PDF 先提取中文，再以 180 DPI 渲染单页并运行 `scripts/validate_cjk_render.py`。视觉检查使用单页原图；完全相同的 PNG 按 SHA-256 复用已检查页的证据，覆盖全部最终页面。未用联系表判断可读性或裁切。

WPS 最终证据为 `final-wps-results.json`：21 份非中期文档来自 `wps-revised/`，9 份最终中期文档来自 `wps-final-midterm/`。初轮诊断 PDF 保留，不能与最终版本混用。论文证据为 `thesis-results.json` 与 `thesis-render/`。

本记录证明本机所列测试输入的结果。Windows TeXstudio、Microsoft Word、真实学生成稿及教师最终审核不属于本次通过范围。

## Texifier 验证环境

主论文使用 `tmp/acceptance-20260920/texifier-main/` 中的源文件副本，关闭“隐藏临时文件”，让编译在项目目录解析字体；本地 `Kaiti.ttf` 链接指向已安装 PowerPoint 的字体，`STZhongsong.ttf` 链接指向仓库已有的本地字体。字体未安装、上传或加入 Git，根目录原 PDF 未被此次 GUI 编译覆盖。

`texifier-results.json` 记录字形门禁与 PDF 摘要；`texifier-main-comparison.json` 记录 25 页逐页 PNG 与已检查回归版本完全一致。已在 Texifier 实际查看最终 PDF。

参考文献压力样例已完成独立命令行回归与 3 页视觉检查；GUI 打开过程中未获得独立压力工程编译完成证据，故不将该项标为 Texifier 已验证。

## 字体使用体验改进后的自动复核

- `build.sh` 与 Makefile 编译入口先检查必需字体，支持 `--check-fonts`、`--font-dir`；论文类读取本机解析配置。查找失败发生在清理辅助文件之前，`--clean` 使用保留 PDF 的 `latexmk -c`。
- 指定目录成功后记住；旧目录消失则提示并重新自动查找。相同配置不重写，避免触发不必要的全量编译。字体文件及本机配置均被 Git 忽略。
- 本机实际字体加载检查通过，包括 PowerPoint 目录中的 KaiTi；论文编译记录确认读取 `sztu-fonts.local.tex`。
- 字体专项 9 项测试通过，涵盖目录优先级、含空格路径、目录记忆/搬迁、缺字体/加载失败、只诊断模式、增量配置和 `--clean` 失败保留原 PDF/辅助文件。
- common、proposal、task-book、midterm 全部自动回归通过；论文 25 页和文献压力案例 3 页自动回归通过，包含 180 DPI 中文字形门禁。日志位于 `tmp/font-ux/`。
- 本轮字体实现改动后未重做目标编辑器目视验收；此前的 WPS/Texifier 验收证据保留，不作为本轮编辑器重新验收通过的声明。
