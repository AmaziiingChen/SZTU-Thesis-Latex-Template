# 字体配置与换机

字体目录允许不存在：程序会跳过不存在的搜索目录，继续查找；所有来源都找不到必需字体时，编译前一次列出缺失项和解决方法。不会用其他字体悄悄替换，也不会因字体检查失败删除已有 PDF。

## 平时怎么用

在项目根目录运行 `bash build.sh`，会先检查字体，再编译论文。仅检查环境、不生成论文：

```bash
bash build.sh --check-fonts
```

检查会显示每种字体的实际文件位置，并用 XeLaTeX 验证八个必需字体文件能否加载。第一次成功后，Texifier/TeXstudio 也能读取保存的路径；编辑器请选择外部 TeX Live/MacTeX 的 XeLaTeX 引擎。

## 新电脑找不到字体

可以按自己的使用方式选择：

- 同时使用 Word/WPS：优先把已有字体安装到系统。macOS 用“字体册”，Windows 使用字体文件的安装菜单。安装后重新打开编辑器，再检查。
- 只供本项目的 LaTeX 使用：把字体放入项目根目录 `fonts.local/`（没有就创建），再运行检查。
- 已经有独立字体文件夹：无需复制，直接指定，成功后会记住目录。

```bash
bash build.sh --check-fonts --font-dir "/你的字体文件夹"
```

去掉 `--check-fonts` 会在检查成功后继续生成论文。路径含空格时保留双引号。指定的目录可以只提供部分字体，其余仍会从系统等来源查找。

无需把字体塞进 TeX Live 或软件安装目录。自动检索包括用户/系统字体目录及常见 Office 安装目录；本机的楷体来自 PowerPoint 自带的字体目录。应用中的字体能供 LaTeX 直接加载，不代表 Word/WPS 一定已将它注册为可选字体。

## 配置与故障

- 必需字体：宋体、黑体、楷体、华文中宋，以及 Times New Roman 的常规、粗体、斜体和粗斜体。
- 搜索优先级：单字体环境变量 > 显式指定目录 > `SZTU_FONT_DIR`（未设置时使用记住的目录） > `fonts.local/` > 系统和应用目录。论文兼容项目根目录旧字体文件，作为最后补充。
- `sztu-fonts.local.json` 记录所选目录；`sztu-fonts.local.tex` 记录实际文件路径，供论文编辑器加载。这两个文件和 `fonts.local/` 都已被 Git 忽略。
- 换电脑、移动字体或卸载 Office 后，重新运行检查。之前记住的目录不存在时会提示并重新自动搜索，也可使用 `--font-dir` 指向新目录；要恢复默认自动搜索，删除 `sztu-fonts.local.json` 后重新检查。
- 找到文件但加载失败时，诊断日志保存在 `tmp/font-check/latest.log`；优先检查字体文件有效性和路径。含 TeX 特殊字符的路径会提示移动目录。
- `python3 scripts/check_fonts.py --no-save` 只诊断，不写入配置。

命令行检查需要 Python 3 和 XeLaTeX。过程文档共用字体搜索规则，也支持 `fonts.local/`、`SZTU_FONT_DIR` 及各自渲染器的字体目录参数；它们不读取论文编辑器的本机配置文件。

字体检查通过只说明渲染环境准备好了，结构检查、中文字形、逐页版式和 Word/WPS 验收仍分别记录。

## 测试与输出位置

- 字体体验回归：`python3 scripts/test_check_fonts.py`。
- 本轮回归日志：`tmp/font-ux/`。
- 论文 PDF：`tmp/thesis-tests/main/main-regression.pdf`。
- 文献压力案例 PDF：`tmp/thesis-tests/bibliography-stress/bibliography-stress-regression.pdf`。
- 先前目标编辑器验收材料：`tmp/acceptance-20260920/`；记录见 `docs/LOCAL_ACCEPTANCE_20260920.md`。
