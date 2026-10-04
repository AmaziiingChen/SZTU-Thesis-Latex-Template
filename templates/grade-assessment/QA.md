# 开发验证记录

2026-10-02，最后一轮为用户授权的满页手写版式校准；不宣称模板成熟。

| 门禁 | 证据 |
| --- | --- |
| 官方内容提取 | 原 .doc 文字、原二进制纸张/页边距/行高属性及受控 DOCX/FODT 已提取；原行高含自动/最小值，转换 PDF 实际短行高不视为固定高度权威 |
| 满页版式授权 | 用户授权扩大手写空间，保留 A4、页边距、表宽/grid、标签、字号、签名和日期；5/6/8 实测表格底部约271 mm，7保持原满页表格与页脚 |
| 数据/容量 | 最终74条模型/容量断言通过，含5类虚构样例、标题/正文超量、真实日期、分值、语义富文本和列表；超量显式拒绝 |
| 最新 PDF | 四种 blank/normal 共8份，严格单页A4，CJK门禁100%可见，三类官方字体嵌入 |
| 最新来源坐标 | 标题独立原件字盒±0.5 mm断言通过；第一标题X实际相对源差0.04 mm；固定提示语行首/行尾与Y坐标断言通过；院系字形距首条边框、签名靠近意见区底部、页脚与穿字线断言通过 |
| 最新 DOCX | 四种 blank/normal 共8份生成并重开；固定行高、原件grid、单主表、垂直居中、字体、标题拉丁黑体、签名字号及末尾1pt段落结构通过；答辩时间/地点标签为源黑体 |
| 全页视觉 | 父代理逐页审阅最新blank/normal PDF；自动字形/几何证据与人工审阅保持分开，最终人工记录由父代理汇总 |
| Word/WPS | 本轮按授权不打开WPS；Word结构与PDF检查不代表Word/WPS最终接受，用户验收仍单独记录 |
| 真实历史案例/教师确认 | 未加载真实学生内容、教师评论或签名，未通过此门，不宣称模板成熟 |

最新合成样例在 `tmp/assessment-fullpage-20261002/`。早期20PDF/20DOCX矩阵用于能力开发；最新满页与来源校准后按授权仅重新生成并检验4blank+4normal，不把早期矩阵标作最新全矩阵验收。当前rich/list、capacity和layout-stress完成最新模型预检；最新实际编译矩阵尚未全部重复。

可运行 `python templates/common/test_assessment_forms.py` 重现74条模型预检；`--render` 可在后续需要时运行完整20件PDF/Word矩阵，本轮未扩大此验证范围。私人输出和商业字体不提交。此处原有的“官方 Word 底稿不提交”约定已于 2026-10-04 按用户要求废止，空白底稿现随仓库提供。

缺陷闭环均有四项：原行高来源误读→spec的source_geometry/print_layout→按授权扩大手写行并压缩Word终止空段→blank/normal及独立底边栅格断言；院系栏偏高→官方字盒规则→共享排版与Word前导段距→blank/normal及实际间距断言；标题ASCII字体及中西文空隙→spec标题局部字距规则→共享标题字体/局部glue与标点控制→blank/normal与原件X/Y字盒断言；提示语行距/换行→逐表源坐标和字号规则→明确bp单位和区域标点/行距→blank/normal与源行首行尾/Y断言；答辩名单位置→源bbox规则→固定名单区域与Word段距→容量fixture/几何断言。

## 可编辑提示追加回归

2026-10-02：四种模板各6份editable-default/deleted/modified/styled/empty/heading-only-deleted，合计24 PDF +24 DOCX，实际生成和自动检查通过。原样默认提示只出现一次并保持原字号/黑宋混排；删除和改写不补文案；同字但bold/italic/super用户marks按正文保留，Word XML确认实际上标及10.5pt正文。固定signature/date/members区域与旧spec相等，PDF仍单页A4、CJK100%、满页边框和签名/页脚几何断言通过。74旧模型容量断言和新24fixture契约、boolean校验、旧数据false/missing兼容、编辑区overflow断言通过。Word/WPS未打开，不将这些结果视为目标编辑器接受。

可重现本追加矩阵：

```sh
python templates/common/test_assessment_forms.py --editable-render --output-dir tmp/assessment-editable-20261002
```

对应缺陷闭环：提示不可删除→spec可编辑正文契约→shared writing_plan与两renderer仅消费一次源格式段→默认/删/改fixtures及文字次数断言；同字样式被强制覆盖→无marks才识别来源段→split_writing_prompt保留marks与Word实际super/sub→styled fixtures与样式XML断言。

最终只读复检20editable PDF/Word全部通过，另4份仅删除提示保留正文的PDF/Word补验通过；原已验收8份legacy blank/normal的body.tex与当前共享渲染计算逐字节相同，未回退原件字形/坐标修复。全空状态Word锚段1pt/无字XML断言通过。

追加heading-only-deleted：三个表移除官方提示但保留原normal普通评价正文，advisor同时保留分工正文；defense保留原questions/answers。4PDF/4DOCX来源提示为0次、普通正文逐段完整断言通过。所有24份DOCX有新增通用断言：全部活跃可编辑paragraph/list run文字均在Word正文中完整保留。


## 固定标题与独立指导文字 v2 回归

2026-10-02 最终核心冻结后，四种模板各5份 guidance-default/deleted/modified/styled/empty，共20 PDF +20 DOCX 实际生成并检查通过。固定标题按官方源14pt黑体常规字重（bold=False），与同表14pt基本信息标签一致；5尾冒号保持宋体14pt，6尾冒号保持黑体14pt，原18pt标题和6学院/专业显式加粗保持。默认指导的源行首/行尾/Y坐标断言通过；删除指导只移除可编辑说明，固定标题和正文保留。所有普通正文独立宋体10.5pt、两字首行缩进，Word XML逐run核验用户bold/italic/super/sub，答辩无虚构标题或空14pt固定标题run。

20 PDF均单页A4、正文可提取、CJK字形门禁100%、连续满页边框与签名/成员固定区域检查通过；20 DOCX均结构检查通过。当前Word/WPS未打开，目标编辑器验收仍单独待验，不把这些结果当作Word/WPS视觉接受。

源格式指导（全文为region.value且没有用户marks）与null/空指导保持原标点行为。改写/marked指导仅局部关闭行末标点margin优化；宽度、字体、字号、行距、标点比例/kerning及全局政策保持。导师styled原标点字盒越框0.027mm的合成fixture保持；修复后右间距0.263mm，超过0.5pt边框半线宽0.0882mm。旧通用0.8mm字段留白断言不是官方指导文字的源尺寸，故仅改写/marked指导改用实际字盒与边框stroke不接触断言，其他字段仍要求0.8mm。默认指导继续严守原换行和源坐标。

本次缺陷闭环：误加强制字重→源run/style字重规范与guidance_style→shared固定label/suffix字体恢复→default/deleted和Word run属性断言；指导标点悬挂越框→局部bounded标点规范→仅改写/marks启用无margin悬挂→styled fixture与物理半线宽断言；答辩空标题run→源无标题规则→Word跳过空固定label→defense default/styled及run/字号断言。

可复现：

```sh
python templates/common/test_assessment_forms.py --guidance-render --output-dir tmp/assessment-guidance-v2-20261002
```

## 2026-10-04 长专业名称回归

新增 long-major 合成fixture（9字学院、8字专业）。旧版本Python容量检查与实际TeX盒均拒绝major；修复后只按identity_row规则重新分配两栏水平空白，Word制表位与PDF坐标来自同一共享计划。原空白/短名称计划保持逐值相等；表格、字号、页边距、日期与签名区域保持不变。超长名称与内部换行仍被拒绝。

通过74项基础容量断言、24组editable及20组guidance契约断言、新identity契约和实际PDF/DOCX生成检查。PDF中文已提取，150 DPI单页已检查，CJK门禁16/16通过。专业实际字形X范围115.662–177.519mm，学院31.790–99.271mm；两者各一行且基线对齐，专业未越178.25mm正文右边界。DOCX正文完整、16pt和共享制表位结构检查通过；尚未在Word/WPS目视验收。

后台19项assessment测试通过，错误消息只翻译允许的字段名，不透传原始诊断中的私有内容。另以临时持久工作区运行真实generate_preview，包含模板快照及PDF预览流程，调用成功。真实工作区只读容量复核通过，未改动用户数据。

复现：

```sh
python templates/common/test_assessment_forms.py --identity-render --output-dir tmp/grade-major-fix-20261004/verified
```

本次模板源码变更前备份及诊断输出留在tmp/grade-major-fix-20261004，均不作为发布内容。


## 2026-10-04 成绩同行与题目留白回归

官方依据为8号DOC（SHA256 ff4b9c2dec4e34265b314aa3e39afe759dbf2d4679b931fc78c1a0bf79a99d6b）。原DOC成绩段包含14pt黑体标签、10.5pt宋体说明、14pt黑体冒号。题目原行auto、上下cell padding均为0，但源行网格产生实际留白；不能将0 padding解读为文字可以贴边。相关5/6号同为auto题目行，7号为不同的12pt分列表头和固定行高，未套用本次8号的测量值。

运行 `templates/common/test_assessment_forms.py --grade-layout-render --output-dir tmp/grade-cell-alignment-20261004/regression`：74容量契约、24旧可编辑标题、20新指导段契约、学院/专业同行、新增成绩排版契约全部通过。6组合成样例（blank、normal、title-two-lines、layout-stress、rich-text-list、guidance-styled）生成PDF/DOCX通过；PDF中文字形门禁、单页、连续表线、签名锚点、标题留白、成绩同基线/行内居中几何检查通过。DOCX检查单段、无制表/换行、字体字号、居中、题目31.2pt行距及关闭继承网格。

双行题目PDF实测上留白3.111mm、下留白3.126mm；源诊断为3.360/2.882mm，差在0.4mm内。最终Word经显式SimSun/SimHei字体映射的后台转换，上留白3.378mm、下留白2.865mm，与同引擎源诊断差小于0.1mm。成绩字框中心PDF264.729mm、Word诊断264.713mm，相对成绩行中心264.735mm差小于0.1mm。两种输出中文均通过门禁，150DPI双行样例整页已检查。

关联回归：指导教师评审、评阅人评审、答辩记录各normal的PDF/DOCX通过；此前long-major的PDF/DOCX继续通过。没有重启桌面端，没有修改用户数据。下一次生成预览将读取更新模板。Word/WPS软件内最终验收尚未进行，后台转换不代表其验收。

复现资料、临时字体配置、原件转换和改动前恢复副本保留在 `tmp/grade-cell-alignment-20261004/`（均不提交）。


## 2026-10-04 四表题目换行与留白统一

本节替代此前题目行距验收结论。按本轮用户要求，题目采用字号的 1.3 倍行距（14 pt 对应 18.2 pt，答辩表 12 pt 对应 15.6 pt）、垂直居中及约 3 mm 最小上下留白；保留源字号和列宽。公共 title_row_plan 同时处理首行各单元格高度、连续竖边、后续信息行偏移及可写正文容量，表底与签名/成员区域坐标不变。规范先于测量参数修改，备份位于 tmp/assessment-title-spacing-20261004/before/。

四表各 normal/title-layout-long/title-layout-rich/title-layout-breaks 共 16 组 PDF/DOCX，完成中文提取、150 DPI 字形门禁、单页、题目字盒留白/行距、边框及固定区域几何断言；DOCX 完整文字、字号、显式行距、禁用网格和语义上下标/粗斜体断言通过。最终产物位于 tmp/assessment-title-spacing-20261004/final-verified/。本轮提供的答辩题目仅放入 tmp 下私有测试文件，PDF/DOCX 均已生成，未写入公共 fixture。

Office 后台转换可能忽略 autoSpaceDE/DN=false 而保留中西文间距；题目行高同时按 0.2 em 边界间距保守测量，避免 PDF 四行、Word 五行时再次贴边。只预留空间，不改输入文字或插入空格。答辩 rich fixture 自动断言五行容量。五份 DOCX 经显式字体映射的 LibreOffice 后台转换，题目字盒上下留白均超过 2.7 mm，单页、中文可提取、字形门禁通过；结果保存在 final-word/title-checks.json。已逐页检查题目区域，LibreOffice 诊断不是 Word/WPS 验收。

74 基础容量、24 可编辑标题、20 写作指导契约及长专业/题目合同回归通过；三表长专业与答辩长专业+指导文字的 PDF/DOCX 回归通过。答辩 capacity-boundary 使用单行合成标题隔离正文极限，并新增“长标题+极限正文”必须返回 sections.questions 容量错误的断言，防止挤占正文后静默裁切。

已知独立限制：两张评审表的 Word 后台转换仍有签名栏裁切，不能宣布整表 Word 版式通过。指导教师表短题目对照与长题目样例的签名字盒 Y 坐标完全相同（602.124764–616.110764 pt），确认与本轮题目增高无关。此项作为独立问题保留；WPS/Word 目标编辑器尚未验收。未启动、重启或切换前台应用。
