# Dependencies — M1.1

运行时框架沿用 Skeleton，没有引入 Agent、AI、消息中间件或新数据库。`uv.lock` 是跨平台解析结果；`requirements-runtime.lock` / `requirements-dev.lock` 包含精确版本与制品哈希。构建依赖 setuptools 固定为 84.0.0；uv 只是开发锁定工具，不属于产品运行时依赖。

下表许可证来自本轮实际安装包的 distribution metadata；这是依赖登记，不代表已完成整个容器镜像、系统库和传递依赖的发布合规审查。

| 直接依赖 | 本轮版本 | License metadata | 目的 / 替代方案 | Runtime |
|---|---|---|---|---|
| FastAPI | 0.141.1 | MIT | 已有 HTTP API 框架；不替换为其他框架 | 是 |
| Uvicorn | 0.52.4 | BSD-3-Clause | 已有 ASGI 运行器 | 是 |
| Pydantic | 2.13.5 | MIT | ai.5 接口与验证真值；不手工复制校验器 | 是 |
| pydantic-settings | 2.15.0 | MIT | 已有配置入口 | 是 |
| SQLAlchemy | 2.0.52 | MIT | 已有数据库映射/事务；替代是重复手写 SQL | 是 |
| Alembic | 1.20.0 | MIT | 已有迁移；固定 revision 避免启动时 create_all | 是（部署工具） |
| psycopg / psycopg-binary | 3.3.5 | LGPL-3.0-only | 已有 PostgreSQL 驱动；binary 包包含需另登记的第三方二进制依赖 | 是 |
| jsonschema（新增直接依赖） | 4.26.0 | MIT | 测试全部 ai.5 JSON Schema 与 fixtures；替代是仅验证 Pydantic，不能发现 Schema 派生漂移 | 否，dev extra |
| PyYAML（新增直接依赖） | 6.0.3 | MIT | 测试 Compose/状态文件与运行 ai.5 自检；替代是另写 YAML 解析器或仅依赖 Docker | dev 直接依赖；Uvicorn standard 已可能传递依赖 |

pytest/httpx/ruff/mypy 沿用已有 dev extra。当前上游 Starlette 对 httpx TestClient 与 AnyIO BlockingPortal alias 有 2 条弃用警告，测试仍通过；本轮没有为消除警告再引入 httpx2 或更换测试栈。

容器基础镜像查询自 Docker Hub 官方 library API并锁定 manifest digest：Python 3.12.14-slim、PostgreSQL 17.11。实际本地数据库二进制来自 PostgreSQL Windows 下载页指向的 EDB 17.11 zip，SHA256 为 `4b8db0930c38f6ef845db919551dedda3b6b845aeb0927b3d79a6e8e9e4537cf`。本机未安装系统 PostgreSQL 服务。

工程语义参考：[SQLAlchemy PostgreSQL ON CONFLICT / JSONB](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html)、[SQLAlchemy 版本计数限制](https://docs.sqlalchemy.org/en/20/orm/versioning.html)、[PostgreSQL Windows 二进制来源](https://www.postgresql.org/download/windows/)。
