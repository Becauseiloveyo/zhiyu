# v1.0 Files Changed

对照正式v0.9 ZIP原字节，而非Git状态；baseline SHA `a33895ca9566f89be118ea8d4dc8600e7692286e49972e39300273d29cbd14b0`。所有实际交付成员的before/after SHA见 [机器清单](../artifacts/v1.0/files-changed.json)，派生自引用清单不纳入差异，仍在最终Manifest校验。

{'MODIFIED': 16, 'ADDED': 1821}

| 源码/配置/前端路径 | 实际变化 |
|---|---|
| `.dockerignore` | MODIFIED |
| `Dockerfile` | MODIFIED |
| `Dockerfile.release` | ADDED |
| `config/reference-build-wheel.json` | ADDED |
| `config/reference-profile.json` | ADDED |
| `frontend/package-lock.json` | MODIFIED |
| `frontend/package.json` | MODIFIED |
| `lab/real-sensors/Dockerfile` | MODIFIED |
| `lab/real-sensors/suricata_start.py` | MODIFIED |
| `pyproject.toml` | MODIFIED |
| `requirements-operator.lock` | ADDED |
| `src/zhiyu/__init__.py` | MODIFIED |
| `src/zhiyu/api/routes/health.py` | MODIFIED |
| `src/zhiyu/main.py` | MODIFIED |
| `tests/test_reference_ingress.py` | ADDED |
| `tests/test_release_profile.py` | ADDED |
| `tests/test_release_recovery_guards.py` | ADDED |
| `tests/test_release_wheels.py` | ADDED |
| `tools/m9_lab_adapter.py` | MODIFIED |
| `tools/reference_ingress.py` | ADDED |
| `tools/release_freeze.py` | ADDED |
| `tools/release_profile.py` | ADDED |
| `tools/release_recovery.py` | ADDED |
| `tools/release_wheels.py` | ADDED |
| `uv.lock` | MODIFIED |

27项新增发布工具测试保留原464；版本元数据/哈希依赖取得/参考配置与启动/完整备份恢复/日志脱敏/固定loopback ingress/Sensor HTTP2+SMTP+QP控制是本版变更。RC11 main.py仅import排版且AST等价，RC12 Dockerfile仅tests-stage COPY原operator lock。批准前端/Logo、ai.5、16迁移、响应/AI/独立验证核心行为不变。运维文档、SBOM/license、安全扫描/逐条处置、原失败/复验/浏览器/报告/封存记录随包交付；私密配置/操作日志/backup/cache/DB/权重不交付。
