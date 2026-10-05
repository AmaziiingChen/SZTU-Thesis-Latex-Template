# 评阅人评审表格式与打印规则

## 2026-10-05 评阅提示行距调整

按用户要求，将“评阅教师评语（从选题价值……水平与规范性等方面进行评述）：”提示段的固定行距从 31.2 pt 调整为 18.2 pt。该段混排最大字号为 14 pt，采用其 1.3 倍行距；提示文字仍为 10.5 pt 宋体，固定标签/末冒号仍为 14 pt 黑体，保留原字重、位置和宽度。Word、PDF、默认提示及显式 writing_guidance 共用该数值。

此项是用户批准的打印版覆盖，不再以原件的双倍行距作为该提示段的验收目标。正文自身行距、其他表单、表格边框、签名和日期区域均保持原规则。用两行默认指导文字检查 PDF 同字号文字基线差为 18.2 pt，以及 Word 段落为 364 twips 固定行距。

官方内容及结构权威：2026届毕业档案相关表格 `6 评阅人评审表.doc`，SHA-256 `14a590d5a564d718672cc4d6a4fd0fbd83a1aeb8c2f24dbaec8aba18bb59595c`。原件保留不改。

## 2026-10-02 独立复核

直接解开原DOC的Compound File并读取WordDocument section SPRM：纸张11906×16838 twips（约210.009×297.004 mm，A4），上下1440 twips（25.4 mm），左右1800 twips（31.75 mm）。受控DOCX与从原DOC直转FODT一致。Apple textutil另转WordML会落入Letter默认尺寸，不能作为原纸张证据。二进制及FODT证据留在 `tmp/assessment-source-audit-20261002/`。

原始行高属性：`[null, null, null, {"twips": 7281, "rule": "atLeast"}, null]`。空项表示由内容和空段落确定；positive rowheight是minimum，negative才是exact。参见[Microsoft DOC section properties](https://learn.microsoft.com/en-us/openspecs/office_file_formats/ms-doc/46c3ec54-53ff-4c0a-b0d6-07ad15d2546e)及[table properties](https://learn.microsoft.com/ca-es/openspecs/office_file_formats/ms-doc/b39a6648-501c-4361-8366-4f042f579469)。

旧实现把LibreOffice诊断实际高度固化为exact，不能据此证明原WPS的行高/分页；诊断表顶58.420 mm、表底231.817 mm。当前PDF的学院字形下界51.55 mm，距表顶6.87 mm，诊断原件下界55.88 mm，距离2.54 mm（答辩记录无这行）。这属于文字包围盒与版心坐标混用，不是Letter缩放导致。

## 已授权打印覆盖

用户明确要求整页利用手写区，因此本打印版本覆盖原auto/minimum行高，保留官方结构、表宽150.319 mm、合并网格、0.5 pt连续边框、字体字号、页边距及签名/日期字号和至少30 mm签名宽度；不声称严格复制原Word/WPS版式。

表格目标底边271.000 mm，逐行高度和各字段坐标以layout.json为准。前三份含学院表（指导/评阅/成绩）在A4底边保留约26 mm，学院/专业实际字形下界到表顶约2.54 mm。新增空间分配给评语、分工、成员签名手写区；签名随评语行底边保留固定下方空间。答辩记录原已覆盖整页，保留表底及页底署名位置，成员区域容量扩到实际可用区。

Word同步新行高与语义结构、末空段落的最小占位。最终Word/WPS由用户确认，不以结构或LibreOffice诊断代替验收。PDF必须独立提取中文、150 DPI、字形门禁、实际边线/文字bbox几何断言与逐页视觉检查。超量返回SINGLE_PAGE_OVERFLOW，不缩字、不裁剪、不增加第2页。

签名区X坐标、字号与手写最小宽度，以及答辩页底关闭Word网格/自动间距等通用规则，均继续保留在layout.json；填充日期采用真实YYYY-MM-DD。公共fixtures全为虚构，学生原始内容、字体和签名不提交；四类表单的空白官方 Word 底稿已由用户明确授权随渲染器提交。

学院/专业标签按原件字形X位置：学院34.61 mm、专业122.1 mm；评阅表两标签保持原件黑体16 pt bold，其余两表为黑体16 pt非bold。

顶部源式校准：实际标题字形首行y=27.883–34.227 mm、次行y=38.890–45.233 mm，18 pt黑体bold；ASCII括号同黑体，不用Times New Roman。位置按实际glyph bbox标定，字体采用Word物理point（bp），不改变学院/专业坐标或表顶。

固定提示与用户正文分开：5/6提示标签及尾冒号14 pt，其余宋体10.5 pt，15.6 pt文档行网格使混合字号两行基线间距31.2 pt（11.0067 mm）；7纯10.5 pt提示基线间距15.6 pt；8提示混合14/10.5 pt，实测两段文字基线间距22 pt。各提示的行距/字体/标点独立记于regions，用户正文按官方15.6 pt网格行距，不再用14 pt一律覆盖。

标题拉丁括号与汉字均使用原件黑体，标题局部关闭中西文自动间距；正文保留原有中西文排版规则。固定提示语按原件文字包围盒与换行校准，成绩考核表随签名区域扩大向下平移 10 mm。

## 可编辑写作提示契约

`sections.editable_headings` 为可选boolean。true表示提示是comments（advisor/reviewer/grade）、division_of_work（advisor）或comments中的答辩intro（defense）的真实正文；不补入缺失提示。首个paragraph全文恰为对应region的label+value+suffix.text时只渲染一次，按官方黑体标题/宋体说明及字号排版；改写按共享正文样式，删除后正文从原提示顶部开始。表格、签名、日期、成员名单及基本信息标签保持固定。false或省略保留旧静态提示行为，旧defense comments继续不参与输出。富文本/列表语义保留，过量仍拒绝，不缩小字号或挤压签名。

默认提示的来源格式识别还要求首段全部run没有bold/italic/super/sub用户marks；同字加样式属于用户编辑，按共享正文保留marks，不覆盖为静态格式。

清空提示与正文时，Word使用不可见1pt空段锚定后续签名/成员段的明确段前距，并从位置计算中扣除其高度；保留手写空间。对应editable-empty/deleted回归，不把空段视为写作提示。

## v2：固定标题 / 可编辑提示 / 正文分离（当前契约）

`sections.writing_guidance` 可选map只允许comments、division_of_work、questions，值是ParagraphInput或null；null、空字符串、空runs明确删除提示。缺map或活跃key保持旧static/v1调用。显式活跃key启用v2：对应固定label始终为官方黑体14pt常规字重、无首行/左缩进；colon/suffix按源字体14pt常规字重；只有提示可删。提示紧接label同段同行，任意修改仍按原宋体10.5和原段落行距/标点格式，保留用户bold/italic/script。原默认仅括号文字写进map（advisor/reviewer不含末colon）；defense用questions key保存原完整说明，源无独立黑体标题，保留源2.5字缩进。普通comments/division_of_work正文独立两字缩进，绝不识别或消费整段prompt文本；defense额外comments作为说明后的普通intro正文，questions再后。按guide实际度量调整正文起点/容量，原signature/date/member区域保持不变。旧v1识别仅用于没有对应guidance key的兼容调用。

## 官方字重与指导标点

固定标题是官方14pt黑体常规字重，bold=False；与同表姓名/学号/职称/签名等14pt黑体一致。官方原件这些run未设bold，Normal/DocDefaults亦未开启bold。原5末冒号为宋体14pt常规，原6末冒号黑体14pt常规，按guidance_style.fixed_suffix源式保留。只取消误加的fixed-label/suffix加粗；原18pt标题及原6学院/专业16pt显式bold仍保留，用户guide/body富文本bold/italic/script仍生效，全局AutoFakeBold=3政策不变。

v2 guidance的text与原region.value完全相同且无bold/italic/script时保留官方原标点与margin优化；null/空guide也保留源规则。只有改写或有marks的指导段局部关闭行末标点margin优化，保留原半角/.75比例与kerning、宽度、字体/字号/行距，不改全局或正文。此处仅识别明示的guide字段，不猜测或消费body。styled fixture验证实际字盒距离边框中心大于半条0.5pt边框线宽，防止触线；普通字段仍保留0.8mm断言。旧通用0.8mm margin不是官方指导文字的源尺寸，不能据它缩字或改列宽。默认指导继续用原件换行与Y坐标断言。


## 2026-10-04 专业名称同行容量

沿用成绩考核表已验证的公共identity_row_plan。短字段保持本表原坐标（学院34.61mm、专业122.10mm），长字段按16pt字体实测字宽共享同行空白；右界178.25mm，最小字段间隔5.645mm，测量余量0.5mm。Word制表位与PDF文本框同步移动；评阅表原黑体bold保留。字号、行高、表宽、页边距、签名/日期不变；合计仍超宽时报出具体字段。此为正常专业名称的授权适配，不将调整后的X坐标声称为官方空白表坐标。


## 2026-10-04 四表题目换行统一（替代此前题目行距规则）

本次用户明确要求统一题目换行后的疏密，授权调整题目行距：四套均采用字号的1.3倍（14pt题目为18.2pt，答辩12pt为15.6pt），上下各约3mm文字留白，整块垂直居中。保留官方字体、字号、表宽、列宽及原最小行高；此为用户批准的题目行距覆盖，不宣称仍使用原Word隐式网格的31.2pt双倍间距。

题目行按实际字号和行数增长；答辩首行所有格子共享这一行高与1.3倍行距，教师姓名标签不再继承隐藏的双倍网格。PDF用物理point，Word显式关闭行网格/中西文自动间距，并设置段落字形在行框内居中。换行和上下标保留为结构化语义，不删除字符、压字号、插空格或限制正常长标题为两行。表内随后基本信息及提示区域整体下移，从可伸缩正文区域扣除相同空白，表底和签名/日期区域不移动；若剩余正文容量不足仍拒绝，而非裁剪或挤占签名。

跨排版器容量规则：题目行高采用无额外字距与 Office 中西文边界最多 0.2 em 字距两种测量结果的较大值；此项只预留高度，不插入空格、不改变输入或字号。上下 3 mm 为最小留白，较少换行的排版器将多出的空间对称分配。保留 Word 关闭自动字距设置，但不依赖转换器一定遵守该设置。

## Word 底稿版本管理

2026-10-04 按用户明确要求，空白 `word/official-template.docx` 纳入 Git；此前仅保留在本机的约定已废止。当前底稿 SHA-256：`c18b7338353208a3743f5279732278893190ab879ffd96bcf7aaced57aebeeb3`。本次仅补齐分发文件，不修改其内容或版式。
