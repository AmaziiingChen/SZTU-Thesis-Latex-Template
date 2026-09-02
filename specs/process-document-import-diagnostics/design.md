# 过程文档输入诊断设计

## 模块边界

- `templates/common/python/import_diagnostics.py`
  - 读取单个 PDF 的最小结构证据；
  - 将本机对象键和路径不可逆匿名化；
  - 汇总三件套完整性、冲突、重复和证据状态。
- `scripts/build_process_document_manifest.py`
  - 从本机私有输入清单生成不含路径和原始键的 JSON 诊断结果；
  - 盐值通过本机文件读取，避免出现在命令行和输出中。
- `templates/common/fixtures/cross-document-manifest.json`
  - 只保存人工构造的匿名结构数据，不引用真实学生材料。

## 数据流

输入清单包含 `source_key`、`document_type` 和 `path`。这些字段仅在进程内用于分组和读取，
输出前使用 HMAC-SHA256 生成 `bundle_id` 与 `document_id`。输出文档项只保留：匿名 ID、
文档类型、SHA-256、页数、文字字符数、页面图像数、解析器和证据状态。
三件套之外的输入类型统一输出为 `unsupported`，原始类型只生成匿名摘要，避免任意输入
字符串进入可提交清单。

PDF 首选 `pypdf` 做结构读取。单个文件解析异常被转换为局部状态，不向批次外抛出。后续
混合 PDF 引擎回退属于 P2 能力，不在本阶段伪装成已经完成。

## 状态

- `text_layer`：存在可提取文字；只证明有文字层，不证明中文字形有效；
- `scan_only`：没有文字层但存在页面图像，需要 OCR/人工复核；
- `no_text_evidence`：既无文字层也无可确认页面图像，需要人工复核；
- `encrypted`：无法无密码打开；
- `parse_failed`：当前解析器无法读取。

## 安全与隐私

- 输出禁止路径、文件名、原始对象键和提取文字；
- 盐值最少 16 字节且不写入输出；
- CLI 输入清单、盐值和输出均应保存在 `references/private/`、`output/**/private/` 或
  `tmp/` 等不提交位置；
- 自动测试断言输出中不存在输入路径和原始键。

## 测试

- 公共匿名夹具覆盖完整三件套、缺件、同类冲突、跨类别重复、扫描件、解析失败和未知类型；
- 生成最小 PDF 验证 `text_layer`、`scan_only`/`no_text_evidence` 与坏文件隔离；
- 清单结果使用稳定排序，便于回归比较。
