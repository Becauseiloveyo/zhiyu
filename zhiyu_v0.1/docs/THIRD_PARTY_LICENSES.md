# v1.0 Third-party license inventory

基于实际锁文件、版本匹配的METADATA、精确镜像Scout/Trivy包清单与固定模型README生成。未确认项记UNKNOWN，不猜许可证或宣称已完成再分发许可审查。

完整逐组件清单：[CSV](../artifacts/LICENSE_INVENTORY_v1.0.0.csv)；[CycloneDX SBOM](../artifacts/SBOM_v1.0.0.cdx.json)；[schema/覆盖验证](../artifacts/v1.0/security/sbom-validation.json)。

| 来源 | 组件数 |
|---|---:|
| Python frozen lock | 48 |
| npm frozen lock | 306 |
| exact container identity | 6 |
| container wazuh | 336 |
| container postgres | 148 |
| container model | 393 |
| container wazuh-agent | 115 |
| container sensor | 145 |
| container backend | 131 |
| external model weights | 1 |

UNKNOWN组件数：241（含项目自身、镜像聚合身份及无法证实的包metadata）；其具体name/version/purl/source保留在CSV与SBOM。模型权重不在发布包中，仅记录固定外部身份及其上游声明。

## Python lock inventory

| Name | Version | License metadata |
|---|---|---|
| alembic | 1.20.0 | MIT |
| annotated-doc | 0.0.5 | MIT |
| annotated-types | 0.8.0 | MIT |
| anyio | 4.15.1 | MIT |
| attrs | 26.1.0 | MIT |
| certifi | 2026.7.22 | MPL-2.0 |
| click | 8.5.0 | BSD-3-Clause |
| colorama | 0.4.6 | BSD License |
| fastapi | 0.141.1 | MIT |
| greenlet | 3.5.5 | MIT AND PSF-2.0 |
| h11 | 0.16.0 | MIT |
| httpcore | 1.0.9 | BSD-3-Clause |
| httptools | 0.8.0 | MIT |
| httpx | 0.28.1 | BSD-3-Clause |
| idna | 3.19 | BSD-3-Clause |
| iniconfig | 2.3.0 | MIT |
| jsonschema | 4.26.0 | MIT |
| jsonschema-specifications | 2025.9.1 | MIT |
| librt | 0.15.0 | MIT |
| mako | 1.4.1 | MIT |
| markupsafe | 3.0.3 | BSD-3-Clause |
| mypy | 1.20.2 | MIT |
| mypy-extensions | 1.1.0 | MIT |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause |
| pathspec | 1.1.1 | Mozilla Public License 2.0 (MPL 2.0) |
| pluggy | 1.6.0 | MIT |
| psycopg | 3.3.5 | LGPL-3.0-only |
| psycopg-binary | 3.3.5 | LGPL-3.0-only |
| pydantic | 2.13.5 | MIT |
| pydantic-core | 2.46.5 | MIT |
| pydantic-settings | 2.15.0 | MIT |
| pygments | 2.21.0 | BSD-2-Clause |
| pytest | 9.1.1 | MIT |
| python-dotenv | 1.2.3 | BSD-3-Clause |
| pyyaml | 6.0.3 | MIT |
| referencing | 0.37.0 | MIT |
| rpds-py | 2026.6.3 | MIT |
| ruff | 0.16.7 | MIT |
| sqlalchemy | 2.0.52 | MIT |
| starlette | 1.6.0 | BSD-3-Clause |
| typing-extensions | 4.16.0 | PSF-2.0 |
| typing-inspection | 0.4.4 | MIT |
| tzdata | 2026.3 | Apache-2.0 |
| uvicorn | 0.52.4 | BSD-3-Clause |
| uvloop | 0.22.1 | UNKNOWN |
| watchfiles | 1.2.0 | MIT |
| websockets | 17.1 | BSD-3-Clause |
| setuptools | 84.0.0 | MIT |

npm条目来自锁文件的license字段或同版本package.json；image条目来自实际扫描/包版权metadata，工具自动识别不等同法律判定。没有下载新版本替代冻结依赖。包含开发/构建/平台可选依赖，未全部进入浏览器bundle或生产容器；以组件scope与image_id区分。
