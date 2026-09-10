# 真实 VLM 升级验收（2026-09-10）

- 原 checkout 与远端起点：`334e90ae912256d36773539cf409294ec05459cc`。
- `reports/qa.json` 的预先存在修改（时间戳与 files_scanned）保持逐字一致，未暂存，不覆盖。
- 历史 `data/sample`、`reports/demo` 与规则适配器相对起点无差异；旧规则全量重建验证通过。
- 真实模型 144 条输出已实际运行；固定权重经官方 SHA-256 核对；无系统异常，原始输出全保存。
- 51 项测试通过，包括输入边界、分组/图像泄漏、缓存、解析、失败分母、真实证据完整性及两个 Dashboard 模式。
- Ruff check/format 通过，发布内容隐私扫描通过。
- Streamlit 实际启动，本机浏览器已操作规则历史与真实实验页，检查 holdout 指标和失败图像；AppTest 同时覆盖 dev 切换。
- CI 不执行真实权重推理；远端 Actions 状态以最终提交对应的 GitHub run 为准。
