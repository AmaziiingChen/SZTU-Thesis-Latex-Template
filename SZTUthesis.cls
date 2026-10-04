% SZTU 本科毕业论文排版核心。学生先读 README.md，再编辑 content/ 下的内容。
% 给维护者和 Agent：这里规定“怎样排版”，不要把学生姓名、题目和研究正文写进来。
% 文件地图：字体、页面和段落、封面、声明、目录、摘要、图表、参考文献。
% 使用上述关键词搜索相应分区；正文内容在 content/ 中修改。
% 修改格式前，先核对 templates/thesis/spec/ 中的规格（下载包见 docs/）。
% 字体缺失属于环境问题；不要用缩小字号、替换字体或删除内容来掩盖编译错误。
% 本类基于 article：论文的“章”使用 \section，“节”使用 \subsection，
% 三级标题使用 \subsubsection；不要使用 book/report 才有的 \chapter。
% 上游：https://github.com/SZTU-ACM/SZTU-Thesis-Latex-Template
% 本地校准与注释维护保留上游 GPL-3.0 许可；下载包 NOTICE.md 记录来源。
% 本模版依据深圳技术大学本科生毕业论文（设计）撰写规范编排。
% 主体装订顺序（与主文件 sztuthesis_main.tex 一致）：
% 1.封面；2.诚信声明；3.目录；4.中文摘要与关键词；5.英文摘要与关键词；
% 6.正文；7.参考文献；8.致谢；9.附录（必要时，示例见 content/appendix_example.tex）。


\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{SZTUthesis}[2026/10/04 v1.1 SZTU undergraduate thesis class]
\ProcessOptions\relax
%% 读取基类
\LoadClass[a4paper,12pt]{article}
\RequirePackage{ifxetex}
\RequireXeTeX
\ifxetex\else
\ClassError{SZTUthesis}{You must use the `xelatex' driver\MessageBreak Please choose `xelatex'}{%
Just choose `xelatex', no `pdflatex' or `latex' and so on.}
\fi
% 相关宏包 %
% ------------------------------------%
% 支持中文的 ctex 宏包
\RequirePackage[fontset=none]{ctex}
% 页面布局
\RequirePackage{geometry}
% 数学宏包
\RequirePackage{amsmath}
\RequirePackage{ntheorem}
\RequirePackage{amsfonts}
\RequirePackage{amssymb}
\RequirePackage{bm}
% 自定义关键词
\RequirePackage{pgfkeys}
% 设置目录
\RequirePackage{titletoc}
% 设置字体
\RequirePackage{fontenc}
% 设置颜色
\RequirePackage{xcolor}
% 设置页眉和页脚
\RequirePackage{fancyhdr}
% 设置标题格式
\RequirePackage{titlesec}
% 超链接 hyperref 的设置
\RequirePackage{hyperref}
% 插入图片
\RequirePackage{graphicx}
% 表格
\RequirePackage{array}
% 长表格
\RequirePackage{longtable}
% % 弹性表格
% \RequirePackage{tabularx}
% booktabs 提供了\toprule 等命令.
\RequirePackage{booktabs}
% multirow 支持在表格中跨行
\RequirePackage{multirow}
% 调整间隔, 让表格更好看些
\RequirePackage{bigstrut}
%在跨行表格中输入定界符
\RequirePackage{bigdelim}
% 保护脆落命令
\RequirePackage{cprotect}
% 设置代码环境
\RequirePackage{listings}
% 首行缩进
\RequirePackage{indentfirst}
% warning: ccaption宏包不能出现在 caption 宏包之后
% % 设置中英文标题
% \RequirePackage{ccaption}
% 设置浮动体的标题
\RequirePackage{caption}
\RequirePackage{subcaption}
% 定制列表环境
\RequirePackage{enumitem}
% 提供\AtBeginEnvironment以方便全局调整一些结构的设置
\RequirePackage{etoolbox}
% 下划线（\underline会执行box逻辑，下划线文字无法换行。ulem的\uline为替代品）
\RequirePackage[normalem]{ulem}
% 动态宽度包，代替minipage
\RequirePackage{varwidth}
% % 尺寸计算
% \RequirePackage{calc}
% 为 figure/table 的 [H]（就地固定）提供 Here 浮动体类型；algorithm 亦依赖 float，此处显式引入以免删去算法章节后失效
\RequirePackage{float}
% 算法编号
\RequirePackage{algorithm}
% 获取总页数
\RequirePackage{lastpage}
% 控制元素编号与章节的关系
\RequirePackage{chngcntr}
% 字符串处理
\RequirePackage{xstring}

% 2026 届模板固定使用 GB/T 7714—2015 数字顺序制（随仓库版本 v2.1）。
% 来自https://github.com/CTeX-org/gbt7714-bibtex-style
% \RequirePackage{natbib} % gbt7714.sty已经包含了natbib宏包
\RequirePackage[sort&compress]{gbt7714}

% 2026 官方范例要求精确使用宋体、黑体、楷体、华文中宋和
% Times New Roman。缺失时停止编译，不允许静默回退到系统默认字体或
% Fandol。macOS 的 Microsoft Word 自带未注册到系统字体册的 KaiTi，
% 因此允许从其合法安装目录直接加载。
\def\sztu@font@cjkmain{SimSun}
\def\sztu@font@cjksans{SimHei}
\def\sztu@font@cjkmono{SimSun}
\def\sztu@font@cjkkai{KaiTi}
\newif\ifsztu@mainfile
\newif\ifsztu@sansfile
\newif\ifsztu@kaifile
\newif\ifsztu@timesfile
\sztu@mainfilefalse
\sztu@sansfilefalse
\sztu@kaifilefalse
\sztu@timesfilefalse

\def\sztu@font@zhongsong{STZhongsong.ttf}
\def\sztu@font@times{Times New Roman.ttf}
\def\sztu@font@timesbold{Times New Roman Bold.ttf}
\def\sztu@font@timesitalic{Times New Roman Italic.ttf}
\def\sztu@font@timesbolditalic{Times New Roman Bold Italic.ttf}
\def\sztu@path@cjkmain{}
\def\sztu@path@cjksans{}
\def\sztu@path@cjkkai{}
\def\sztu@path@zhongsong{}
\def\sztu@path@times{}
\def\sztu@path@timesbold{}
\def\sztu@path@timesitalic{}
\def\sztu@path@timesbolditalic{}
\newif\ifsztu@configured
\sztu@configuredfalse
\InputIfFileExists{sztu-fonts.local.tex}{}{}
\ifsztu@configured
  \sztu@mainfiletrue
  \sztu@sansfiletrue
  \sztu@kaifiletrue
  \sztu@timesfiletrue
  \let\sztu@font@cjkmono\sztu@font@cjkmain
  \def\sztu@checkfont#1{%
    \IfFileExists{\csname sztu@path@#1\endcsname\csname sztu@font@#1\endcsname}{}{%
      \ClassError{SZTUthesis}{Configured font #1 is missing}%
        {Run python3 scripts/check_fonts.py to refresh local font paths.}}}
  \sztu@checkfont{cjkmain}
  \sztu@checkfont{cjksans}
  \sztu@checkfont{cjkkai}
  \sztu@checkfont{zhongsong}
  \sztu@checkfont{times}
  \sztu@checkfont{timesbold}
  \sztu@checkfont{timesitalic}
  \sztu@checkfont{timesbolditalic}
\else
\IfFontExistsTF{simsun.ttf}{%
  \sztu@mainfiletrue
  \def\sztu@font@cjkmain{simsun.ttf}%
  \def\sztu@font@cjkmono{simsun.ttf}%
}{%
  \IfFontExistsTF{SimSun}{}{%
    \ClassError{SZTUthesis}{Required font SimSun is missing}%
      {Install the official SimSun font before compiling. Font substitution is forbidden.}%
  }%
}
\IfFontExistsTF{simhei.ttf}{%
  \sztu@sansfiletrue
  \def\sztu@font@cjksans{simhei.ttf}%
}{%
  \IfFontExistsTF{SimHei.ttf}{%
    \sztu@sansfiletrue
    \def\sztu@font@cjksans{SimHei.ttf}%
  }{\IfFontExistsTF{SimHei}{}{%
    \ClassError{SZTUthesis}{Required font SimHei is missing}%
      {Install the official SimHei font before compiling. Font substitution is forbidden.}%
  }}%
}
\IfFontExistsTF{simkai.ttf}{%
  \sztu@kaifiletrue
  \def\sztu@font@cjkkai{simkai.ttf}%
}{\IfFontExistsTF{Kaiti.ttf}{%
  \sztu@kaifiletrue
  \def\sztu@font@cjkkai{Kaiti.ttf}%
}{\IfFontExistsTF{KaiTi}{}{%
    \ClassError{SZTUthesis}{Required font KaiTi is missing}%
      {Run python3 scripts/check_fonts.py before compiling. Font substitution is forbidden.}%
}}}
\IfFileExists{STZhongsong.ttf}{}{%
  \ClassError{SZTUthesis}{Required font STZhongsong.ttf is missing}%
    {Restore STZhongsong.ttf in the project root before compiling.}}
\IfFontExistsTF{Times New Roman.ttf}{%
  \sztu@timesfiletrue
}{\IfFontExistsTF{Times New Roman}{}{%
    \ClassError{SZTUthesis}{Required font Times New Roman is missing}%
      {Install Times New Roman before compiling. Font substitution is forbidden.}%
}}

\fi

\ifsztu@mainfile
  \setCJKmainfont[Path={\sztu@path@cjkmain},AutoFakeBold]{\sztu@font@cjkmain}
  \setCJKmonofont[Path={\sztu@path@cjkmain},AutoFakeBold]{\sztu@font@cjkmain}
\else
  \setCJKmainfont[AutoFakeBold]{\sztu@font@cjkmain}
  \setCJKmonofont[AutoFakeBold]{\sztu@font@cjkmono}
\fi
\ifsztu@sansfile
  \setCJKsansfont[Path={\sztu@path@cjksans},AutoFakeBold]{\sztu@font@cjksans}
\else
  \setCJKsansfont[AutoFakeBold]{\sztu@font@cjksans}
\fi
\ClassInfo{SZTUthesis}{CJK fonts: main=\sztu@font@cjkmain,
  sans=\sztu@font@cjksans, mono=\sztu@font@cjkmono,
  kai=\sztu@font@cjkkai}

% 页面布局 %
% -------------------------------------------------------%
\geometry{top=25.4mm,bottom=25.4mm,left=31.7mm,right=31.7mm}
% 给页眉留足空间（否则会有 \headheight is too small的warning）
\setlength{\headheight}{14.5pt}
% “磅”是衡量印刷字体大小的单位,约等于七十二分之一英寸。
% 而 1英寸＝25.4毫米，则1磅＝25.4/72≈0.353毫米。
% 磅和 LaTeX的 pt- points (大约 1/72 inch) 是一致的。
\renewcommand*{\baselinestretch}{1.5}   % 几倍行间距
\setlength{\baselineskip}{16pt}         % 基准行间距
\setlength{\parskip}{7.8pt}             % Word 段前段后 0.5 行的有效段间距


% 设置字体 %
% -------------------------------------------------------%
\ifsztu@timesfile
  \setmainfont[
    Path={\sztu@path@times},
    BoldFeatures={Path={\sztu@path@timesbold}},
    ItalicFeatures={Path={\sztu@path@timesitalic}},
    BoldItalicFeatures={Path={\sztu@path@timesbolditalic}},
    BoldFont={\sztu@font@timesbold},
    ItalicFont={\sztu@font@timesitalic},
    BoldItalicFont={\sztu@font@timesbolditalic}]
    {\sztu@font@times}
\else
  \setmainfont{Times New Roman}
\fi
\IfFontExistsTF{Courier New}
  {\setmonofont{Courier New}}
  {\setmonofont{TeX Gyre Cursor}}
\IfFontExistsTF{Arial}
  {\setsansfont{Arial}}
  {\setsansfont{TeX Gyre Heros}}
\renewcommand\normalsize{%
	\@setfontsize\normalsize{12pt}{14.45}%
	\abovedisplayskip 12\p@ \@plus3\p@ \@minus7\p@
	\abovedisplayshortskip \z@ \@plus3\p@
    \belowdisplayshortskip 6.5\p@ \@plus3.5\p@ \@minus3\p@
}

% 重定义ctex定义好的宋体和黑体，以支持伪加粗AutoFakeBold
% 即支持类似word里的给黑体、宋体等中文字体加粗的操作，用\bfseries
\let\heiti\relax
\ifsztu@sansfile
  \newCJKfontfamily[hei]\heiti{\sztu@font@cjksans}[Path={\sztu@path@cjksans},AutoFakeBold]
\else
  \newCJKfontfamily[hei]\heiti{\sztu@font@cjksans}[AutoFakeBold]
\fi
\let\songti\relax
\ifsztu@mainfile
  \newCJKfontfamily[song]\songti{\sztu@font@cjkmain}[Path={\sztu@path@cjkmain},AutoFakeBold]
\else
  \newCJKfontfamily[song]\songti{\sztu@font@cjkmain}[AutoFakeBold]
\fi
\let\kaishu\relax
\ifsztu@kaifile
  \newCJKfontfamily[kai]\kaishu{\sztu@font@cjkkai}[Path={\sztu@path@cjkkai},AutoFakeBold]
\else
  \newCJKfontfamily[kai]\kaishu{\sztu@font@cjkkai}[AutoFakeBold]
\fi

% 华文中宋用于中文摘要上方的论文题名，路径由字体检查脚本解析。
% 上游还声明了华文行楷、华文新魏，但本论文没有使用它们；不再强制加载，
% 避免下载包在不携带这两份无用字体的情况下无法编译。
\let\huawenzhongsong\relax
\newCJKfontfamily[hwzs]\huawenzhongsong{\sztu@font@zhongsong}[Path={\sztu@path@zhongsong},AutoFakeBold]


% 每行缩进两个汉字
\setlength{\parindent}{2em}

%  中文标题名称
\newcommand*{\sztu@cap@contentsname}{目录}
\newcommand*{\sztu@cap@listfigurename}{插图清单}
\newcommand*{\sztu@cap@listtablename}{附表清单}
\newcommand*{\sztu@cap@refname}{参考文献}
\newcommand*{\sztu@cap@indexname}{索引}
\newcommand*{\sztu@cap@figurename}{图}
\newcommand*{\sztu@cap@tablename}{表}
\newcommand*{\sztu@cap@appendixname}{附录}
\newcommand*{\sztu@cap@abstractname}{摘要}
 %%%  中文关键字
\newcommand*{\sztu@cap@keywordsname}{关键字}


% 定制titlepage
% 定义命令和定义相应的宏。
%----------------------------------------------------------------------%
% 预定义全局使用的文字，如姓名、专业等信息，在content/info.tex中定义
%----------------------------------------------------------------------%
% 以下定义封面相关命令和相应的宏，以titleen为例，\titleen为实际在源码中使用的命令，一旦执行就会因为\gdef\@titleen{#1}使得其产生一个\@titleen的宏，而该宏能够在后续的环境中使用。
\newcommand*{\titlecn}[1]{\gdef\@titlecn{#1}}                           % 中文标题
\newcommand*{\titlecnSingleLine}{\StrSubstitute{\@titlecn}{\\}{}}         % 中文标题去掉换行“\\”
\newcommand*{\titleen}[1]{\gdef\@titleen{#1}}                           % 英文标题
\newcommand*{\titleenSingleLine}{\StrSubstitute{\@titleen}{\\}{}}         % 英文标题去掉换行“\\”
\newcommand*{\priormajor}[1]{\gdef\@priormajor{#1}}                     % 一级学科（学科专业）
\newcommand*{\minormajor}[1]{\gdef\@minormajor{#1}}                     % 二级学科（学科方向）
\newcommand*{\interestmajor}[1]{\gdef\@interestmajor{#1}}               % 研究方向，关键词组
\newcommand*{\department}[1]{\gdef\@department{#1}}                     % 二级培养单位
\newcommand*{\supervisor}[1]{\gdef\@supervisor{#1}}                     % 导师
\newcommand*{\supervisortitle}[1]{\gdef\@supervisortitle{#1}}           % 导师职称
\newcommand*{\subsupervisor}[1]{\gdef\@subsupervisor{#1}}               % 副导师
\newcommand*{\studentid}[1]{\gdef\@studentid{#1}}                       % 学号

\newcommand*{\clcnumber}[1]{\gdef\@clcnumber{#1}}                       % 中图分类号 Chinese Library Classification
\newcommand*{\schoolcode}[1]{\gdef\@schoolcode{#1}}                     % 学校代码
\newcommand*{\udc}[1]{\gdef\@udc{#1}}                                   % UDC
\newcommand*{\academiccategory}[1]{\gdef\@academiccategory{#1}}         % 学术类别


% 封面 %
% \makecoverpage 只读取 info.tex 已定义的信息。校名图 images/school_title.pdf
% 是上游封面素材。题目过长先检查自然换行；不要插入空格定位、缩小官方字号。
% 如果学院要求不同的封面，应单独核对规格后修改此处，不能仅改学生字段来模拟。
% -------------------------------------------------------------%

% 论文日期
% 采用key-value对的方式来制定存储信息的pgf路径
\pgfkeys{/thesisdate/pgf/.cd, % 定义pgf路径
    year/.store in = \year, % 指定关键词year的存储位置为\year
    month/.store in = \month, % 指定关键词month的存储位置为\month
    day/.store in = \day
}
% 利用上述的pgf的key-value定制论文日期命令
\newcommand{\thesisdate}[1] {
    \pgfkeys{/thesisdate/pgf/.cd,#1} % 指定使用/thesisdate/pgf/.cd来解释参数，然后在后文能直接使用存储位置来指定解释的内容
    \gdef\@thesisdate{\year{} 年 \month{} 月 \day{} 日} % 将构建好的日期存储到宏（\@thesisdate）中
}

% 以下为本科毕业论文（设计）封面所用字段与版式

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% 定义 \makecoverpage 实现封面的重新绘制
% -----------------------------------------------%
\newcommand{\makecoverpage} {
    \thispagestyle{empty}
    {
        \hbadness=10000  % Suppress "Underful \hbox ..."
        \centering
        \linespread{1.5}
        \begin{figure}[H]
            \centering
            \includegraphics[width=0.75\textwidth]{school_title.pdf}
        \end{figure}
        \vspace{-1cm}
        {\zihao{2} \bfseries \songti 本科毕业论文（设计） \par} % 二号宋体
        \vspace{2.5cm} % 空行
        \begin{minipage}{\textwidth}
            \centering
            \bfseries
            {\zihao{3} \heiti 题目：} 
            \begin{varwidth}[t]{0.85\textwidth}
                \zihao{2} \kaishu \uline{\@titlecn} 
            \end{varwidth}

        \end{minipage}
        \vskip 3.5cm
        {
            \zihao{3} \heiti
            \begin{tabular}{ll}
                \makebox[5em][s]{姓名}      & \parbox[t]{14em}{\bfseries \kaishu \uline{\centering \hfill \@author \hfill}} \\
                \makebox[5em][s]{学院}      & \parbox[t]{14em}{\bfseries \kaishu \uline{\centering \hfill \@department \hfill}} \\
                \makebox[5em][s]{专业}      & \parbox[t]{14em}{\bfseries \kaishu \uline{\centering \hfill \@priormajor \hfill}} \\
                \makebox[5em][s]{学号}      & \parbox[t]{14em}{\bfseries \kaishu \uline{\centering \hfill \@studentid \hfill}} \\
                \makebox[5em][s]{指导教师}  & \parbox[t]{14em}{\bfseries \kaishu \uline{\centering \hfill \@supervisor \hfill}} \\
                \makebox[5em][s]{职称}      & \parbox[t]{14em}{\bfseries \kaishu \uline{\centering \hfill \@supervisortitle \hfill}} \\
                \makebox[5em][s]{提交日期}   & \parbox[t]{14em}{\bfseries \kaishu \uline{\centering \hfill \@thesisdate \hfill}} \\
            \end{tabular}
        }
        \par
    }
}

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% 2. 本科毕业论文（设计）诚信声明
% -----------------------------------------------%
% 单独设一页，排在扉页后
% 按模板，标题二号，内容四号，这里学校没有特别强调字体字号，
% 应该有一定自由度。

\newcommand{\announcement}{

    \linespread{1.5} % 这部分的行间距跟正文不一样

    \vspace*{2.5cm}
    {\centering \zihao{-2} \bfseries \heiti 深圳技术大学本科毕业论文（设计）诚信声明 \par}

    \vspace{2cm}

    \hbadness=10000  % Suppress "Underful \hbox ..."
    \setlength{\parindent}{2em} % 首行缩进
    {
        \zihao{4}
        本人郑重声明：所呈交的毕业论文（设计），题目《\titlecnSingleLine》 是本人在指导教师的指导下，独立进行研究工作所取得的成果。对本文的研究做出重要贡献的个人和集体，均已在文中以明确方式注明。除此之外，本论文不包含任何其他个人或集体已经发表或撰写过的作品成果。本人完全意识到本声明的法律结果。

        \vspace{4cm}

        \begin{flushright}
                毕业论文（设计）作者签名：\makebox[5em][c]{} \\
                日期：\makebox[5em][c]{}\makebox[6em][s]{年月日}
        \end{flushright}
        
    }

    \vspace{1cm}

}


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% 3. 目录 %
% 目录来自各级标题和 .toc 辅助文件；目录页码需要多轮编译才能稳定。
% 不要在 content/ 中手写目录，也不要编辑 .toc。章节标题不要写“1.”等手工编号。
% -----------------------------------------------%
% 目录由论文（设计）的章、节、附录等序号、名称和页码组成。单独成页。四号宋体，1.5倍行距分散对齐排版。 
% “目录”两字居中（三号黑体），下空两行为章、节、小节及其开始页码（靠右顶格）。章、节、小节分别以阶梯式排列：1（第1章）、1.1、1.1.1依次标出。章、节、小节的题名与页码之间用“．．．．．．”连接。除“目录”两字外，其余字体均为小四号宋体。

\setcounter{secnumdepth}{3}
% 定义作为标题的格式
% \titleformat{command}[shape]%定义标题类型和标题样式
%               {format}%定义标题格式
%               {label}%定义标题的标签，即标题的标号等
%               {sep}%定义标题和标号之间的水平距离
%               {before-code}%定义标题前的内容
%               [after-code]%定义标题后的内容
\newcommand{\sectionbreak}{\clearpage}  % 大章前分页
\titleformat{\section}{\zihao{-2}\centering \bfseries \heiti}{\thesection.}{1em}{}
\titleformat{\subsection}{\zihao{3} \bfseries \heiti}{\thesubsection}{1em}{}
\titleformat{\subsubsection}{\zihao{-3} \bfseries \heiti}{\thesubsubsection}{1em}{}
% 设置章节标题的段间距，默认0.5段间距足够了，去掉章节标题自带的段间距
\titlespacing{\section}{0pt}{7.8pt}{7.8pt}
\titlespacing{\subsection}{0pt}{7.8pt}{7.8pt}
\titlespacing{\subsubsection}{0pt}{7.8pt}{7.8pt}
% 定义在目录中的格式
% \titlecontents{标题名}
%               [左间距]
%               {标题格式}
%               {标题标志}
%               {无序号标题}
%               {指引线与页码}
\titlecontents{section}
              [0.75em] % 按样例目录左侧是和前置部分文字左侧对齐的
              {\zihao{4} \songti}
              {\contentslabel[\thecontentslabel.]{1.5em}}
              {\hspace*{-1em}}
              {\titlerule*[0.5pc]{.}\contentspage}

\titlecontents{subsection}
    [2.5em]
    {\zihao{4} \songti} % note that 3.8 = 1.5 + 2.3
    {\contentslabel{2.2em}}
    {\hspace*{-3em}}
    {\titlerule*[0.5pc]{.}\contentspage}

\titlecontents{subsubsection}
    [4em]
    {\zihao{4} \songti} % note that 3.8 = 1.5 + 2.3
    {\contentslabel{3.0em}}
    {\hspace*{-5em}}
    {\titlerule*[0.5pc]{.}\contentspage}

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% % 正文标题+作者信息
% \newcommand{\infotitle}{
%     \linespread{1.5}
%     \begin{center} \zihao{2} \bfseries \huawenzhongsong \titlecnSingleLine \end{center}
%     % \begin{center} \zihao{5} \kaishu \@department-\@priormajor \quad  \@author \end{center}
%     % \begin{center} \zihao{-5} \kaishu 学号：\@studentid \end{center}
% }
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% 页眉
% 页眉去掉题目中显式的换行符。中文摘要、英文摘要、正文的切换由主文件调用，
% 必须先出完上一分区页面再更改页码，否则短摘要可能继承错误页式。
\newcommand{\setheader}{
    \pagestyle{fancy}
    \fancyhf{}
    \renewcommand{\headrulewidth}{0.75pt}
    \fancyhead[C]{\songti \zihao{-5} 深圳技术大学本科毕业论文—\titlecnSingleLine}
}
% 摘要页码格式
\newcommand{\setabstractfooter}{
    \pagestyle{fancy}
    \fancyhf{}
    \renewcommand{\headrulewidth}{0pt}
    \pagenumbering{Roman}
    \fancyfoot[C]{\zihao{-5} \thepage}
}
% 英文摘要恢复文字页眉和横线，但延续中文摘要的 Roman 页码。
\newcommand{\setenglishabstractheader}{
    \setheader
    \fancyfoot[C]{\zihao{-5} \thepage}
}
% 正文页码格式
\newcommand{\setfooter}{
    \setheader
    \pagenumbering{arabic}
    \fancyfoot[C]{\zihao{-5} 第 \thepage\ 页 共 \pageref{LastPage}\ 页}
}
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% 4. 中文摘要
% -----------------------------------------------%
% 【摘要】【关键词】：【】内四号楷体加粗，【】外小四号楷体；环境内使用 1.5 倍行距（见 abstractcn 中 \linespread）。

\newcommand*{\keywordscn}[1]{\gdef\@keywordscn{#1}} % 定义中文关键词
\newcommand*{\categorycn}[1]{\gdef\@categorycn{#1}} % 定义中文分类
\newenvironment{abstractcn} { % 定义中文摘要环境

    \linespread{1.5}

    \begin{center} \zihao{2} \bfseries \huawenzhongsong \@titlecn \end{center}

    \vspace{0.5cm}

    \noindent {\zihao{-4}\kaishu【{\zihao{4}\bfseries 摘要}\zihao{-4}】}
    \zihao{-4}\kaishu \noindent % 内容为小四号楷体
}
% 显示中文关键词和分类号
{
    \begin{flushleft}
        \noindent 
        {\zihao{-4}\kaishu【{\zihao{4}\bfseries 关键词}\zihao{-4}】}
        {\zihao{-4} \kaishu \@keywordscn} \par % 内容为小四号楷体
    \end{flushleft}
}

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% 4. 英文摘要
% -----------------------------------------------%
% 英文摘要与中文摘要对应；题名居中、英文为 Times New Roman。【Abstract】【Key words】为四号加粗，其余小四号（见 abstracten）。
\newcommand*{\keywordsen}[1]{\gdef\@keywordsen{#1}} % 英文关键词
\newcommand*{\categoryen}[1]{\gdef\@categoryen{#1}} % 英文摘要页分类号（可与中文侧中图分类号对应）
\newenvironment{abstracten} { % 新建英文摘要环境
    \linespread{1.5}

    \begin{center} \zihao{2} \bfseries \@titleen \end{center}

    \vspace{0.5cm}

    \noindent {\zihao{-4}【{\zihao{4}\bfseries Abstract}\zihao{-4}】~}
    \zihao{-4} \noindent % 小四号
}
{
    \begin{flushleft}
        \noindent 
        {\zihao{-4}【{\zihao{4}\bfseries Key words}\zihao{-4}】~}
        {\zihao{-4} \@keywordsen} \par % 小四号
    \end{flushleft}
}


% 5. 论文正文 %
% -------------------------------------------------------%
% 论文正文是主体，主体部分应从另页右页开始，每一章应另起页。一般由序号标题、文字叙述、图、表格和公式等五个部分构成。
% 写作形式可因研究内容的性质不同而变化，一般可包括绪论（或综述）、理论分析、计算方法、实验装置和测试方法、实验结果分析和讨论、研究成果、结论及意义等。
% 该部分由用户编写
% 一级标题字体不大于小二号，黑体加粗； 
% 二级标题比一级标题小半号，黑体加粗； 
% 三级标题比上一级标题小半号，黑体加粗； 
% 正文内容小四号宋体。 
% 以上内容一律1.5倍行距、段前段后0.5行、两端对齐排版。 

% 图表等浮动环境设置 %
% 浮动体允许 LaTeX 在邻近页面安排图片/表格，以避免大块空白。
% [htbp] 是位置偏好，不是保证；[H] 强制固定位置，应只在确有需要时使用。
% \caption 产生编号，\label 必须紧随其后，正文用 \ref 引用。
% position=top/bottom 只影响题注间距，实际位置由作者把 \caption 写在图表前后决定。
% ----------------------------------------------------------%
% 图、表按章编号，题号形如「图 1-1」「表 2-3」；\thefigure / \thetable 在主文件中设定。
% 默认情况下, \LaTeX{} 要求每页的文字至少占据 20%,否则该页就只单独放置一个浮动环境,
% 而这通常不是我们想要的, 我们将这个要求降低到 5%.
\renewcommand*{\textfraction}{0.05}
% 有时如果多个浮动环境连续放在一起, \LaTeX{}
% 会将它们分在几个不同页，即使它们可在同一页放
% 得下. 我们可以通过修改 |\topfraction| 和 |\bottomfraction| 分别设置顶端和底端的浮
% 动环境的最大比例.
 \renewcommand*{\topfraction}{0.9}
 \renewcommand*{\bottomfraction}{0.8}
% 有时\LaTeX{}会把一个浮动环境单独放在一页,
% 我们要求这个环境至少要占据 85% 才能单独放在一页.
% 注意:  |\floatpagefraction| 的数值必须小于 |\topfraction|.
 \renewcommand*{\floatpagefraction}{0.85}
% 关于图片 graphicx
 % 如果图片没有指定后缀, 依次按下列顺序搜索
\DeclareGraphicsExtensions{.pdf,.eps,.jpg,.png,.tif}
 % 设置图表搜索路径, 可以给图表文件夹取如下名字
\graphicspath{{figures/}{figure/}{pictures/}%
  {picture/}{pic/}{pics/}{image/}{images/}}


% 插图格式
% ------------------------------------------------------%
% \captionsetup[subfigure]{labelfont=normalfont,textfont=normalfont,singlelinecheck=off,justification=raggedright}
% singlelinecheck=off 表示即使caption只有一行， justification 也生效
% justification=raggedright 使子图 caption 靠左对齐，而caption的上下位置由\caption标签的位置决定，以此实现了学校要求的子图标签在左上角显示。
% 这部分功能由 subcaption 这个包实现，而这个包不能和 subfigure 同时使用，所以子图的写法也与 subfigure 包的不大一样。 
% \captionsetup[subfigure]{singlelinecheck=off,justification=raggedright} % 左对齐
\captionsetup[subfigure]{singlelinecheck=off,justification=centering}   % 居中

% 图下方描述的字体
\DeclareCaptionFont{song}{\songti}
\DeclareCaptionFont{sfive}{\zihao{5}}
% 图、表序号格式（章号-序号）在 sztuthesis_main.tex 中于 \numberwithin 之后定义。


\captionsetup[figure]{
	format=plain,      % 标题从第二行开始是否缩进，plain无缩进，hang有缩进
	labelsep=quad,     % 分隔符是一个空格
	font={song,sfive},   % 图的字体, 宋体小五
	position=bottom    % position=bottom, 不代表标题放在下面, 标题仍放在你放\caption的位置.
}
% 表格格式
% ------------------------------------------------------%
\captionsetup[table]{
	format=plain,      % 标题从第二行开始是否缩进，plain无缩进，hang有缩进
	labelsep=quad,     % 分隔符是一个空格
	font={song,sfive},   % 图的字体, 宋体小五
	position=top
}
% 算法
% ------------------------------------------------------%
\floatname{algorithm}{算法}
% \renewcommand{\thealgorithm}{\arabic{section}-\arabic{algorithm}}
% \renewcommand {\thealgorithm} {\thesection-\arabic{algorithm}}
\captionsetup[algorithm]{
	format=plain,      % 标题从第二行开始是否缩进，plain无缩进，hang有缩进
	labelsep=quad,     % 分隔符是一个空格
	font={song,sfive},   % 图的字体, 宋体小五
	position=top
}

% 列表环境设置 %
% ------------------------------------------------------------------%
% \RequirePackage{listings}
\setlist{%
	topsep=0.3em, % 列表顶端的垂直空白
	partopsep=0pt, % 列表环境前面紧接着一个空白行时其顶端的额外垂直空白
	itemsep=0ex plus 0.1ex, % 列表项之间的额外垂直空白
	parsep=0pt, % 列表项内的段落之间的垂直空白
	leftmargin=1.5em, % 环境的左边界和列表之间的水平距离
	rightmargin=0em, % 环境的右边界和列表之间的水平距离
	labelsep=0.5em, % 包含标签的盒子与列表项的第一行文本之间的间隔
	labelwidth=2em % 包含标签的盒子的正常宽度；若实际宽度更宽，则使用实际宽度。
}

% 表格 %
% ------------------------------------------------------%
% 修改tabular 环境, 设置表格中的行间距为正文行间距.
\let\sztu@oldtabular\tabular
\let\sztu@endoldtabular\endtabular
\renewenvironment{tabular} {
    \bgroup
	\renewcommand{\arraystretch}{1.38}
    \sztu@oldtabular
} {
    \sztu@endoldtabular\egroup
}

% 表格字号应比正文小，一般五号/10.5pt，但是暂时没法再cls里设置（不然会影响到封面等tabular环境）
% 所以目前只好在主文件里局部\AtBeginEnvironment

% 数学环境, 定理等设置 %
% 数学变量放在 $...$ 中；独立公式用 equation/align，引用用 \eqref{标签}。
% 用 x_{i}、x^{2} 表达上下标，不用 Unicode 的 ₂、² 模拟数学结构。
% -------------------------------------------------------%
% 数学定理相关的常量
\newcommand*{\sztu@cap@definition}{定义}
\newcommand*{\sztu@cap@theorem}{定理}
\newcommand*{\sztu@cap@lemma}{引理}
\newcommand*{\sztu@cap@corollary}{推论}
\newcommand*{\sztu@cap@assumption}{假设}
\newcommand*{\sztu@cap@conjecture}{猜想}
\newcommand*{\sztu@cap@axiom}{公理}
\newcommand*{\sztu@cap@principle}{定律}
\newcommand*{\sztu@cap@problem}{问题}
\newcommand*{\sztu@cap@example}{例}
\newcommand*{\sztu@cap@proof}{证明}
\newcommand*{\sztu@cap@solution}{解}

\newtheorem{definition}{\sztu@cap@definition}
\newtheorem{theorem}{\sztu@cap@theorem}
\newtheorem{lemma}{\sztu@cap@lemma}
\newtheorem{corollary}{\sztu@cap@corollary}
\newtheorem{assumption}{\sztu@cap@assumption}
\newtheorem{conjecture}{\sztu@cap@conjecture}
\newtheorem{axiom}{\sztu@cap@axiom}
\newtheorem{principle}{\sztu@cap@principle}
\newtheorem{problem}{\sztu@cap@problem}
\newtheorem{example}{\sztu@cap@example}
\newtheorem*{proof}{\it{\sztu@cap@proof}}
\newtheorem{solution}{\sztu@cap@solution}



% 编号分章节。如需要连续编号，注释\makeatletter下面对应内容即可。
% \renewcommand{\theequation}{\arabic{section}-\arabic{equation}}

\makeatletter
\@addtoreset{figure}{section}
\@addtoreset{table}{section}
\@addtoreset{equation}{section}
\makeatother

% 6. 参考文献 %
% 正文 \cite{key} 对应 .bib 中的 key。BibTeX 生成 .bbl，不要直接编辑 .bbl。
% 此处只负责排序、编号和外观，不能验证文献真实性、引用是否准确或外文数量。
% 文献条目应从出版商/数据库核实后导入，缺少资料时报告待补项，不生成虚构引用。
% ------------------------------------------------------%
% 可选参数为 BibTeX 数据库名；正式论文默认读取 thesis-references，公开压力样例
% 可以复用同一版式实现而不触碰学生数据。
\newcommand{\setreference}[1][thesis-references]{%
    \begingroup
    \renewcommand{\refname}{参考文献}%
    \renewcommand{\bibsection}{%
        \clearpage
        \phantomsection
        \addcontentsline{toc}{section}{参考文献}%
        \vspace*{7.8pt}% 段前 0.5 行
        {\centering\zihao{-2}\bfseries\heiti 参考文献\par}%
        \vspace{7.8pt}% 段后 0.5 行
    }%
    % 文献编号用小四楷体；正文五号，中文楷体、西文 Times New Roman。
    % natbib 的数字列表使续行与编号后的条目正文起点对齐。
    \renewcommand{\bibnumfmt}[1]{{\zihao{-4}\kaishu[##1]}\hfill}%
    \renewcommand{\bibfont}{%
        \zihao{5}\kaishu
        \linespread{1.5}\selectfont
        \setlength{\parindent}{0pt}%
        \setlength{\parskip}{0pt}%
    }%
    \setlength{\bibsep}{0pt}% 条目之间不增加额外段距
    \urlstyle{same}% URL 保持 Times New Roman，并沿 gbt7714 的断行点换行
    % xdvipdfmx 无法让同一个外链注释跨物理页；参考文献中的长 URL/DOI
    % 保留可复制文本但不创建外链，避免条目恰好跨页时产生损坏的 PDF 注释。
    \let\url\nolinkurl
    \def\href##1##2{##2}%
    \bibliographystyle{gbt7714-numerical}%
    \bibliography{#1}%
    \clearpage
    \endgroup
}
% 7. 致谢 %
% 作者对给予指导、各类资助和协助完成研究工作以及提供各种对论文工作有利条件的单位及个人表示感谢。
% 「致谢」标题居中，小二号黑体加粗（与正文一级标题一致）；正文为小四号宋体，1.5 倍行距（见 thankscontent）。

\newenvironment{thankscontent} { % 定义致谢环境

    \linespread{1.5}

    \vspace{0.5cm}
    \phantomsection % 使得hyperref目录能够跳转到正确的位置
    \addcontentsline{toc}{section}{致谢}
    {\centering \zihao{-2} \bfseries \heiti 致谢 \par}
    \vspace{0.5cm}
    \zihao{-4} \songti
}

% 9. 附录（必要时）%
% -------------------------------------------------------%
% 附录用于不宜放入正文的冗长推导、辅助图表、程序说明等；装订在致谢之后，见主文件末尾与 content/appendix_example.tex。


% 篇眉和页码要求 %
% ---------------------------------------------------------%
% 篇眉宋体小五号居中，深圳技术大学本科毕业论文—论文标题

% \pagestyle{fancy}
% \fancyhf{} % 清空原有格式
% \fancyhf[RH]{\small\leftmark} % 设置所有（奇数和偶数）右侧页眉
% \fancyhf[LH]{深圳技术大学博士学位论文} % 设置所有（奇数和偶数）左侧页眉
% \fancyhf[CF]{\thepage} % 所有（奇数和偶数）中间页脚


\endinput
