# 成绩考核表格式与打印规则

官方内容及结构权威：2026届毕业档案相关表格 `8 成绩考核表.doc`，SHA-256 `ff4b9c2dec4e34265b314aa3e39afe759dbf2d4679b931fc78c1a0bf79a99d6b`。原件保留不改。

## 2026-10-02 独立复核

直接解开原DOC的Compound File并读取WordDocument section SPRM：纸张11906×16838 twips（约210.009×297.004 mm，A4），上下1440 twips（25.4 mm），左右1800 twips（31.75 mm）。受控DOCX与从原DOC直转FODT一致。Apple textutil另转WordML会落入Letter默认尺寸，不能作为原纸张证据。二进制及FODT证据留在 `tmp/assessment-source-audit-20261002/`。

原始行高属性：`[null, null, null, null, {"twips": 704, "rule": "atLeast"}]`。空项表示由内容和空段落确定；positive rowheight是minimum，negative才是exact。参见[Microsoft DOC section properties](https://learn.microsoft.com/en-us/openspecs/office_file_formats/ms-doc/46c3ec54-53ff-4c0a-b0d6-07ad15d2546e)及[table properties](https://learn.microsoft.com/ca-es/openspecs/office_file_formats/ms-doc/b39a6648-501c-4361-8366-4f042f579469)。

旧实现把LibreOffice诊断实际高度固化为exact，不能据此证明原WPS的行高/分页；诊断表顶58.420 mm、表底198.289 mm。当前PDF的学院字形下界51.55 mm，距表顶6.87 mm，诊断原件下界55.88 mm，距离2.54 mm（答辩记录无这行）。这属于文字包围盒与版心坐标混用，不是Letter缩放导致。

## 已授权打印覆盖

用户明确要求整页利用手写区，因此本打印版本覆盖原auto/minimum行高，保留官方结构、表宽150.319 mm、合并网格、0.5 pt连续边框、字体字号、页边距及签名/日期字号和至少30 mm签名宽度；不声称严格复制原Word/WPS版式。

表格目标底边271.000 mm，逐行高度和各字段坐标以layout.json为准。前三份含学院表（指导/评阅/成绩）在A4底边保留约26 mm，学院/专业实际字形下界到表顶约2.54 mm。新增空间分配给评语、分工、成员签名手写区；签名随评语行底边保留固定下方空间。答辩记录原已覆盖整页，保留表底及页底署名位置，成员区域容量扩到实际可用区。

Word同步新行高与语义结构、末空段落的最小占位。最终Word/WPS由用户确认，不以结构或LibreOffice诊断代替验收。PDF必须独立提取中文、150 DPI、字形门禁、实际边线/文字bbox几何断言与逐页视觉检查。超量返回SINGLE_PAGE_OVERFLOW，不缩字、不裁剪、不增加第2页。

签名区X坐标、字号与手写最小宽度，以及答辩页底关闭Word网格/自动间距等通用规则，均继续保留在layout.json；填充日期采用真实YYYY-MM-DD。公共fixtures全为虚构，学生原始内容、字体、签名和官方Word底稿不提交。

学院/专业标签按原件字形X位置：学院31.79 mm、专业119.27 mm；评阅表两标签保持原件黑体16 pt bold，其余两表为黑体16 pt非bold。

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

## 2026-10-04 学院／专业同行容量修复

8字专业名称加“专业：”在原60.852mm区域会换成两行，而该行只预留7.6mm。按本次正常专业名称适配要求，仅对成绩考核表启用同行空白再分配：空白或短名称仍使用原学院/专业X坐标；超出原栏宽时，以规定字体的实际字宽计算两字段所需宽度，在学院起点31.79mm到页面正文右边界178.25mm内调整专业起点。字段之间至少保留一个16pt汉字宽（5.645mm），测量另留0.5mm余量。Word制表位和PDF文本框使用同一计算结果。

此规则只调整学院／专业行的水平空白，不缩字号、不改变行高、表格、页边距、日期或签名位置。若两项合计仍放不下，继续拒绝并指出具体字段。长名称适配属于授权修正，不宣称与官方空白表的专业标签X位置完全相同。


## 2026-10-04 题目行留白与成绩同行校准

再次核对官方8号DOC（上述SHA256不变）：题目行是auto，14pt字体受15.6pt网格影响，两行基线间距31.2pt。原件后台转换的单行高11.176mm；合成双行题目行高22.183mm，字形距上边约3.360mm、下边约2.882mm。题目每增加一行，行高增加31.2pt（11.0067mm）；不将多行挤进原11.176mm行。Word/PDF共用按官方字体实际字宽计算的行数和行高。正文手写区相应减少同等空白，表底、成绩行、签名和日期位置不变；容量不足仍报错，不缩字或侵占签名空间。此修正只启用成绩考核表，其他表需各自官方测量后独立启用。

成绩栏是一个左对齐段落：14pt常规黑体“毕业论文（设计）成绩”、10.5pt宋体括号说明、14pt黑体冒号、14pt宋体整数成绩。所有run共用基线，整行在12.53mm成绩行内垂直居中，水平方向沿用1.905mm单元格边距。不再将说明和成绩放进两个顶对齐文本区，不插空格或制表位模拟间隔；空成绩仍保留同样一行说明。保持原有四舍五入逻辑。PDF使用物理point（bp）并对整行做容量检查，Word关闭隐式网格以避免单行再次跳格。

视觉证据：官方DOC及合成双行题目DOCX后台转换后，分别通过17/17、18/18中文字形探针；150DPI整页已检查。转换依赖显式SimSun/SimHei字体映射，不将此认作WPS验收。

Word题目段还需设置textAlignment=center，使字形在明确31.2pt行框内居中；仅cell vAlign=center仍会将大部分行间空白置于字形上方。官方同引擎诊断的双行标题上/下留白为3.360/2.882mm，修正后3.378/2.865mm。该属性不应用于混合字号成绩段，成绩各run保持共同基线。


## 2026-10-04 四表题目换行统一（替代此前题目行距规则）

本次用户明确要求统一题目换行后的疏密，授权调整题目行距：四套均采用字号的1.3倍（14pt题目为18.2pt，答辩12pt为15.6pt），上下各约3mm文字留白，整块垂直居中。保留官方字体、字号、表宽、列宽及原最小行高；此为用户批准的题目行距覆盖，不宣称仍使用原Word隐式网格的31.2pt双倍间距。

题目行按实际字号和行数增长；答辩首行所有格子共享这一行高与1.3倍行距，教师姓名标签不再继承隐藏的双倍网格。PDF用物理point，Word显式关闭行网格/中西文自动间距，并设置段落字形在行框内居中。换行和上下标保留为结构化语义，不删除字符、压字号、插空格或限制正常长标题为两行。表内随后基本信息及提示区域整体下移，从可伸缩正文区域扣除相同空白，表底和签名/日期区域不移动；若剩余正文容量不足仍拒绝，而非裁剪或挤占签名。

跨排版器容量规则：题目行高采用无额外字距与 Office 中西文边界最多 0.2 em 字距两种测量结果的较大值；此项只预留高度，不插入空格、不改变输入或字号。上下 3 mm 为最小留白，较少换行的排版器将多出的空间对称分配。保留 Word 关闭自动字距设置，但不依赖转换器一定遵守该设置。
