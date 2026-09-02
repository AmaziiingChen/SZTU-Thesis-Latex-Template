# 过程文档页数上界回归设计

## 方法

`templates/common/fixtures/page-range-stress-recipes.json` 只记录基础夹具、各正文区目标块数、
参考文献目标条数和预期 PDF 页数窗口。测试通过
`templates/common/python/regression_fixtures.py` 深复制基础数据，循环使用其中的普通匿名
段落，并为每个副本添加稳定序号。参考文献使用固定的虚构著录格式重新生成。

生成后的数据是三类模板原有 Schema 的普通 JSON，并同时交给 Word 与 LaTeX 渲染器；
生产代码不读取压力配方。

## 稳定性

- 配方使用目标块数而不是目标字符截断，生成结果确定；
- 页数断言使用窄窗口，允许不同 TeX 发行版产生一页以内的合理差异；
- 现有 A4、字体、字形、边框、固定栏目和无 Overfull/Missing-character 门禁继续执行；
- 如果未来正式模板测量值变化，应先更新文档专属规格，再重新标定压力配方，不能直接放宽
  页数窗口掩盖回归。

## 隐私

配方、公共帮助函数和生成结果均不得读取 `references/private/`。生成的临时完整数据与
PDF 只写入 `tmp/`，不进入 Git。
