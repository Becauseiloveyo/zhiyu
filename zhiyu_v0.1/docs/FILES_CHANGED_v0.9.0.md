# v0.9.0 文件变更清单

对照正式 v0.6.0 ZIP 的原始字节；不是对照未经提交的 Git 状态。v0.6 包 SHA256：`3afd802e3bee0945591d3b7f1e02303bafda33a63679e4fe543a4a72609003a5`。

机器清单：[files-changed.json](../artifacts/v0.9/files-changed.json)，含每个文件的 before/after SHA256。最终全包逐文件校验以 `MANIFEST_v0.9.0.sha256` 为准；历史 `MANIFEST.sha256` 保留，不适用于本版本。

变更计数：MODIFIED 10，ADDED 2476。清单自身、包验证与摘要等派生文件不纳入差异自引用；它们仍全部纳入最终 Manifest。

## 实现范围

- 真实只读产品投影、访问隔离、不可变快照、时间线、图谱、报告与回放。
- 原前端连接正式 API、错误/权限状态、原 Logo、固定 Demo 操作和下载校验。
- 同一 PostgreSQL 的独立演示元数据 schema、固定受控 Lab Worker、重置/清理/历史留存。
- 83 项新增后端测试与 15 项前端测试，浏览器脚本、截图、原始失败及最终通过证据。
- 项目版本0.9.0、锁文件项目版本、构建上下文排除、最终文档及交付校验。

原381项测试全通过；74个原测试/fixture文件和28个冻结文件字节不变；依赖未因版本字段修改而升级。原核心schema/迁移和ai.5不变。

## 源码、配置与前端文件

| 路径 | 变化 |
|---|---|
| `.dockerignore` | MODIFIED |
| `CHANGELOG.md` | MODIFIED |
| `Dockerfile` | MODIFIED |
| `PROJECT_STATE.yaml` | MODIFIED |
| `README.md` | MODIFIED |
| `V0.9_STATUS.json` | ADDED |
| `frontend/.gitignore` | ADDED |
| `frontend/dist/assets/AnalysisPages-Doy8JcBZ.js` | ADDED |
| `frontend/dist/assets/CommandMenu-B-HPVeNZ.js` | ADDED |
| `frontend/dist/assets/DemoPage-BrCv8ZVl.js` | ADDED |
| `frontend/dist/assets/ReportsPage-BTzU2Zyn.js` | ADDED |
| `frontend/dist/assets/ReportsPage-CFAWaRiv.css` | ADDED |
| `frontend/dist/assets/index-DhpNEp14.css` | ADDED |
| `frontend/dist/assets/index-ROnvzsxl.js` | ADDED |
| `frontend/dist/assets/inter-latin-400-normal-C38fXH4l.woff2` | ADDED |
| `frontend/dist/assets/inter-latin-400-normal-CyCys3Eg.woff` | ADDED |
| `frontend/dist/assets/inter-latin-500-normal-BL9OpVg8.woff` | ADDED |
| `frontend/dist/assets/inter-latin-500-normal-Cerq10X2.woff2` | ADDED |
| `frontend/dist/assets/inter-latin-600-normal-CiBQ2DWP.woff` | ADDED |
| `frontend/dist/assets/inter-latin-600-normal-LgqL8muc.woff2` | ADDED |
| `frontend/dist/brand/zhiyu-logo.png` | ADDED |
| `frontend/dist/index.html` | ADDED |
| `frontend/eslint.config.js` | ADDED |
| `frontend/index.html` | ADDED |
| `frontend/package-lock.json` | ADDED |
| `frontend/package.json` | ADDED |
| `frontend/public/brand/zhiyu-logo.png` | ADDED |
| `frontend/src/AnalysisPages.jsx` | ADDED |
| `frontend/src/App.jsx` | ADDED |
| `frontend/src/BrandMark.jsx` | ADDED |
| `frontend/src/Charts.jsx` | ADDED |
| `frontend/src/CommandMenu.jsx` | ADDED |
| `frontend/src/DemoPage.jsx` | ADDED |
| `frontend/src/Details.jsx` | ADDED |
| `frontend/src/Overview.jsx` | ADDED |
| `frontend/src/ProductUI.jsx` | ADDED |
| `frontend/src/Recordings.jsx` | ADDED |
| `frontend/src/ReportsPage.jsx` | ADDED |
| `frontend/src/api.js` | ADDED |
| `frontend/src/data.js` | ADDED |
| `frontend/src/demo.js` | ADDED |
| `frontend/src/demo.test.js` | ADDED |
| `frontend/src/final.css` | ADDED |
| `frontend/src/main.jsx` | ADDED |
| `frontend/src/product.css` | ADDED |
| `frontend/src/product.test.jsx` | ADDED |
| `frontend/src/report.css` | ADDED |
| `frontend/src/report.js` | ADDED |
| `frontend/src/report.test.js` | ADDED |
| `frontend/src/routing.js` | ADDED |
| `frontend/src/styles.css` | ADDED |
| `frontend/src/test-setup.js` | ADDED |
| `frontend/src/tokens.css` | ADDED |
| `frontend/src/ui.jsx` | ADDED |
| `frontend/tsconfig.json` | ADDED |
| `frontend/vite.config.js` | ADDED |
| `frontend/vitest.config.js` | ADDED |
| `pyproject.toml` | MODIFIED |
| `requirements-build.lock` | ADDED |
| `schema/product/0001_demo_control_postgresql.sql` | ADDED |
| `src/zhiyu/__init__.py` | MODIFIED |
| `src/zhiyu/api/routes/demo.py` | ADDED |
| `src/zhiyu/api/routes/product.py` | ADDED |
| `src/zhiyu/db/demo_control.py` | ADDED |
| `src/zhiyu/main.py` | MODIFIED |
| `src/zhiyu/product/__init__.py` | ADDED |
| `src/zhiyu/product/access.py` | ADDED |
| `src/zhiyu/product/budgets.py` | ADDED |
| `src/zhiyu/product/contracts.py` | ADDED |
| `src/zhiyu/product/demo_contracts.py` | ADDED |
| `src/zhiyu/product/demo_control.py` | ADDED |
| `src/zhiyu/product/demo_store.py` | ADDED |
| `src/zhiyu/product/demo_worker.py` | ADDED |
| `src/zhiyu/product/projections.py` | ADDED |
| `src/zhiyu/product/queries.py` | ADDED |
| `src/zhiyu/product/recordings.py` | ADDED |
| `src/zhiyu/product/registry.py` | ADDED |
| `src/zhiyu/product/reports.py` | ADDED |
| `src/zhiyu/product/sessions.py` | ADDED |
| `src/zhiyu/product/snapshots.py` | ADDED |
| `src/zhiyu/product/web.py` | ADDED |
| `tests/test_product_api.py` | ADDED |
| `tests/test_product_boundaries.py` | ADDED |
| `tests/test_product_demo.py` | ADDED |
| `tests/test_product_full_chain.py` | ADDED |
| `tests/test_product_graph_timeline.py` | ADDED |
| `tests/test_product_projections.py` | ADDED |
| `tests/test_product_recordings.py` | ADDED |
| `tests/test_product_reports.py` | ADDED |
| `tests/test_product_sessions.py` | ADDED |
| `tools/m6_sensor_capture.py` | MODIFIED |
| `tools/m9_console_dev.py` | ADDED |
| `tools/m9_demo.py` | ADDED |
| `tools/m9_demo_evidence.py` | ADDED |
| `tools/m9_lab_adapter.py` | ADDED |
| `tools/m9_lab_phase.py` | ADDED |
| `tools/m9_local_validation.py` | ADDED |
| `tools/m9_product_migrate.py` | ADDED |
| `tools/m9_source_correspondence.py` | ADDED |
| `uv.lock` | MODIFIED |

## 文档与证据

当前验收入口为 [最终报告](VALIDATION_REPORT_v0.9.0.md)、[UI验收](UI_E2E_REPORT_v0.9.0.md)、[使用指南](USER_GUIDE_v0.9.0.md) 和 [演示指南](COMPETITION_DEMO_GUIDE.md)。全部文档、截图、sample report、recorded replay和运行日志的细项及hash见机器清单与最终Manifest；历史失败不覆盖或冒写为PASS。
