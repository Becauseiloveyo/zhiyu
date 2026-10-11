# 智御 v1.0.0 Final Validation Report

v1.0.0 PASS / STABLE PROTOTYPE。所有结果由实际证据与明确的影响承接支撑。

## Environment

实际运行日期2026-10-05（Asia/Shanghai）。Windows操作员 + WSL2内核6.6.87.2 + Docker Desktop 4.92.0 / Engine29.8.0 Linux containers；Python3.12.14、Node24.18.0、npm11.16.0、PostgreSQL17.11。浏览器为headed Chromium。Reference端口18010；最终独立验收副本18014。第二台Linux实体主机Clean Install = NOT_RUN。

## Release Candidate

RC12_v1.0.0。[冻结391个控制文件](../artifacts/RC_STATE_v1.0.0.json)，后端source `3525c9d70f7c5b8b38ae9d368671ab7ebba78b1c9b1ba9037904b42e210aa73e`，前端build `da3bfd776289f94cb2360f3ec6fd837e56d008100836d3515b6c6a24b849219b`。schema/head=0016_lab_remediation；28冻结文件和83个原测试/fixture文件字节不变。

## Product Architecture

Linux-native Control Plane + Browser Web Console；PostgreSQL为canonical source。AI Proposal ≠ Authorization；Action必须通过Authorization/Risk/Gateway；执行成功 ≠ 安全成功；Verification独立；Sensor不足=>INCONCLUSIVE；确定性防御不依赖模型在线。已批准UI、原项目Logo、ai.5、schema、场景和报告模板未改变。

## Version History

v0.2 Deterministic Event Intelligence；v0.3 Deterministic Response Control；v0.4 Continuous Verification & Re-plan；v0.5 AI Decision Brain；v0.6 Reliability / Security / Real Sensor；v0.9 Competition-ready Product；v1.0 Stable Prototype / Final Release Freeze。各版本历史验收独立保留。

## Gate A

PASS。固定最终范围/AI OPTION B/已知限制，冻结身份与计划符合性复核。RC1→RC12仅最小发布阻断修复，每次候选身份和失败记录保留；原464项不删除/跳过，未扩展核心产品功能。

## Gate B

PASS。[RC6全新安装](../artifacts/v1.0/gate-b-final.json)使用空目录、新venv/npm cache、重新构建三种镜像、新Compose项目和空PG volume。后续候选仅按受影响范围复验，不把复用安装冒充第二次Clean Install；[RC11实际镜像/启动数据摘要](../artifacts/v1.0/gate-b-rc11-targeted-revalidation.json)、[RC12影响证明](../artifacts/v1.0/rc12-change-impact.json)。

## Gate C

PASS。[实际历史升级/恢复](../artifacts/v1.0/gate-c-final.json)、[日志修复后第三次空库恢复](../artifacts/v1.0/gate-c-rc9-logging-restore.json)。74表逐项摘要、外键、审计链、历史录制/报告保持。恢复代码和冻结迁移后续不变，RC11仅版本import布局且AST等价，RC12仅测试镜像COPY既有锁。

## Gate D

PASS。完整运维指南、实际服务库存、CycloneDX1.6 schema验证、真实Python/npm/六镜像漏洞扫描、逐条处置/补丁记录、License UNKNOWN清单。新候选同六镜像/依赖，SBOM已同步RC12。520个Critical/High告警出现项明确保留受控运行剩余风险，不宣称零漏洞。

## Gate E

PASS（最终发布包已完成独立字节读回校验）

## Clean Install

Reference windows-docker-linux-reference/1，RC6实测1224.25秒。28份官方wheel按固定hash取得、独立操作员环境、281次npm cache miss、15前端测试/lint/types/build；原proxy故障、截断索引、Sensor源DNS、internal port不发布的失败均保留，最小修复后重新从空环境执行成功。不是未经验证的一键安装。见 [安装指南](INSTALLATION_GUIDE.md)。

## Upgrade

真实v0.9历史数据库只读导出：13Incident、18ModelRun、234Raw/Normalized、14DemoRuns（12COMPLETED +2NEEDS_RECONCILIATION），所有CLEAN，失败状态保留。0016→0016是无DDL变化的应用升级，不能描述为新schema迁移。原库74表摘要前后完全一致，未在原库注入故障。

## Backup / Restore

完整逻辑备份含PG custom dump、config/密钥（私密）、reports/artifacts、scenario/public manifest和hash清单。每次1493成员、CRC/成员SHA通过；三次新空volume实际恢复。12注册历史录制×LIVE/REPLAY×7投影=168只读访问/恢复副本，并有headed浏览器报告下载。外部模型权重/镜像/依赖不在逻辑备份中；未主张整机完全离线重建。

## Failure Recovery

五种实际故障仅在恢复副本执行：事务0017失败并回滚；有7个LAB_PATH回执时0016→0015降级被23514拒绝并回滚；API启动exit73后恢复READY；坏config先拒绝再恢复；错误wheel hash被pip拒绝且依赖未变。[故障证据](../artifacts/v1.0/gate-c-recovery-faults.json)。另有当前API实际停止/重启/重新登录且74表不变。

## Documentation

安装、部署、升级、备份恢复、用户、管理员、比赛演示、排障、安全基线、限制、架构/API、许可证、AI主张、变更、证据与完整报告齐备。[最终链接检查](../artifacts/v1.0/final-doc-links.json)按实际包成员验证；全ZIP校验与SHA文件在包旁交付，避免自引用hash。

## Security Baseline

[实际服务库存](../artifacts/v1.0/security/service-inventory.json)：宿主暴露仅127.0.0.1；固定无凭据TCP ingress桥接8000/5432；控制面内部网络；API/ingress非root/readonly/cap-drop ALL/no socket。PG默认初始化/root与local trust按实际记录，network SCRAM；受控Lab自签名TLS，Reference loopback API/DB/内部模型HTTP无TLS。公网/跨机TLS未验收。详见 [安全基线](SECURITY_BASELINE_v1.0.md)。

## SBOM

[CycloneDX1.6](../artifacts/SBOM_v1.0.0.cdx.json)实际schema PASS：1629组件，48 Python锁定平台/dev/build包、306完整npm、六镜像身份与容器内包、本地模型。241个License UNKNOWN显式保留，非法律认证。[license inventory](../artifacts/LICENSE_INVENTORY_v1.0.0.csv)。

## Dependency Security

OSV对48个固定Python版本实际返回0 advisory；npm官方audit 0 findings；Trivy0.75.0六个精确镜像实扫，DB更新时间2026-10-04T14:28:15.152965452Z。2175告警出现项/632唯一CVE，其中520 Critical/High：254 NO_REGISTERED_TRIGGER、262 RETAINED_CONTROLLED_RUNTIME_RISK、4 MITIGATED_FEATURE_DISABLED。Suricata HTTP2/SMTP/QP实际禁用，其余未称全关闭/已补丁。可信固定Lab范围内逐项工程处置，不是假装负责人批准生产风险。[全部处置](DEPENDENCY_SECURITY_REVIEW_v1.0.md)。

## Backend Regression

[host JUnit](../artifacts/v1.0/final-backend.xml)：491 passed /0 failed /0 skipped，2864秒。原464 nodeids全部保留，27个发布工具测试新增；[Linux JUnit](m5-runtime/zhiyu-smoke-397c45f14058/test-results.xml)490 passed /0 failed /0 skipped，405.881秒。两条上游TestClient deprecation warning显式保留，未为消警更新冻结依赖。[保留证明](../artifacts/v1.0/final-test-retention.json)。

## Frontend Regression

[15原测试/lint/typecheck/production build](../artifacts/v1.0/final-frontend.json)全部PASS；build逐字节与批准产物相同，原Logo SHA=3d6ee6aa0192a5c6de142e908dfe62e5add970fdcd9966169cfe9f98b5ad8c40。RC11实际运行，RC12仅后端tests-stage COPY锁，前端输入/产物不变，因此明确承接这次结果。另Ruff/mypy全源码PASS。

## Docker Runtime

[新项目zhiyu-smoke-397c45f14058](m5-runtime/zhiyu-smoke-397c45f14058/result.json)189 checks PASS。新空PG/schema、build/bootstrap/API/确定性链/响应/独立验证/恢复/真实本地模型/24评估案例。构建no_cache=false如实记录，Gate B才是独立无缓存安装；旧M5框架真实Sensor字段NOT_RUN，真实Sensor验收使用当前独立A/C Lab，不能混为同一次运行。容器停止移除、volume保留。

## Browser E2E

当前18014正式API、headed Chromium实际DOM验收：Overview、Incident List/Detail五页签、Timeline真实时间、Graph有界非因果/两层血缘、AI SHADOW/Authorization/Risk、Verification三维、System Status UNKNOWN诚实标注、八章节草稿报告。1920×1080/1366×768无外层溢出、CtrlK/Escape/可见键盘focus。真实403/404/410/空态；500/503/malformed/timeout是明确浏览器故障注入。另实际API停止后撤旧指标，重启丢会话需重新登录后正常。

## A01–A15 Re-validation

[最终原文矩阵](A01_A15_FINAL_REVALIDATION_v1.0.md)：A01/A08/A10/A14/A15为REVALIDATED；其余10项UNAFFECTED / EVIDENCE CARRIED FORWARD，逐项说明原证据、当前全回归和源码影响。不是把旧15/15自动当作当前PASS，也未重写Acceptance。

## Real Sensor

最终A真实Suricata7.0.10/Wazuh4.14.7原始文件/采集器/hash/OBSERVED provenance和adapter入库PASS。[C实际stop/recovery](../artifacts/v1.0/gate-e-sensor-stop-recovery.json)在有效worker lease/fence内停止两Sensor，状态降级；恢复生成新证据后均HEALTHY；随后固定C停止Agent，独立结果INCONCLUSIVE。不是任意设备/Windows Sensor/生产流量证明。

## AI Runtime

A两次真实本地模型调用、SHADOW proposal、REFERENCE_GROUNDED引用约束；E实际停止模型得到FALLBACK保留确定性计划；B/D是SCRIPTED_NOT_AI安全反例。当前189包括真实本地valid/hallucination/injection/down/claims-success，当前491包括cross-environment reject。24小规模原评估15 REFERENCE_GROUNDED/9 REJECTED，cloud_calls=0；非通用语义正确率。高风险执行实时全环境SQL=0且审计链有效。

## AI Value Position

OPTION B：[AI-assisted analysis / planning / recommendation](AI_VALUE_FINAL_POSITION_v1.0.md)。closed-loop superiority NOT CLAIMED；G0 NOT INCLUDED IN V1.0 CLAIM；AI default OFF / enabled default SHADOW。不存在为追求PASS提高自主权限的变化。

## Demo / Replay

当前浏览器开始A/B/C/D/E，结果依次PASS/REJECTED/INCONCLUSIVE/FAIL/FALLBACK；A reset新ID保留原A，合计6次COMPLETED/CLEAN。实际owned容器/网络/volume均零残留。5次Browser历史回放+10份JSON/Markdown下载，封存文件SHA、facts SHA、report canonical SHA、服务端export SHA与实际下载bytes一致；74表摘要完全不变，没有新增ModelRun/Action。[汇总](../artifacts/v1.0/gate-e-demo-replay-cleanup.json)。

## Performance Regression

7接口×10样本、实际PG+HTTP读取，对比v0.9。最初与完整回归并发：detail1.336×、graph1.488×、report1.715×等较高；原结果保留。结束后idle复测：7接口中位数7.197–41.715ms，v0.9比例0.363–0.625，未观察持续退化。负载与新loopback ingress不同是可见条件差异，不能断言唯一因果或性能提升百分比/SLA；数据量/as_of也不同。两份[并发](../artifacts/v1.0/api-performance.json)/[idle](../artifacts/v1.0/api-performance-idle.json)均交付，未重跑无变化路径的100k/soak。

## Known Limitations

[正式限制](KNOWN_LIMITATIONS.md)：CONTROLLED LAB；Production/customer/long-term SLA/cloud/Windows Sensor/OT/ICS NOT VALIDATED；HA/multi-tenancy NOT IMPLEMENTED；通用AI语义正确性NOT PROVEN；模型闭环优势NOT CLAIMED。仍有未补丁Critical/High基础包，禁止把本版可信固定Lab结论推广到恶意任意流量或公网服务。

## Architecture Findings

No ai.5 architecture change required. 未引入新引擎、Kafka/Temporal/Neo4j重写、多Agent重构、任意shell/防火墙/渗透、生产自主处置或桌面厚客户端。最小发布阻断修复及原失败见 [RBF记录](RELEASE_BLOCKING_FINDINGS_v1.0.md)。

## Source Correspondence

[实际独立构建images原字节证明](../artifacts/v1.0/final-source-correspondence.json)。新M5 API和tests images中的129源文件/全部tools与workspace一致；tests还核对原测试及锁。Reference release image `sha256:84c687d5bad5c4d0ead08e8d1d73df8a418e23b696c90cc61eb54b60540d0a5f` 内源码相同且15个frontend产物bytes一致。M5 API是backend-only，未伪称其中有UI；最终包391控制文件/83原测试/28冻结文件/15build逐文件对照。

## Package Validation

最终ZIP CRC、Manifest逐项SHA256、重复/安全路径、55个以上本地已知真实凭据与精确格式复核、源码/镜像/UI/ZIP对应、SBOM/license/文档/16迁移/前端byte复现全部PASS。Whole-ZIP SHA和机器验证在ZIP旁交付；不置于自身内避免递归hash。

## Final Release Decision

v1.0.0 PASS / STABLE PROTOTYPE。完成后停止当前V1路线，不自动进入v1.1/v2或新增功能。仅Stable Prototype / CONTROLLED LAB，非Production Ready。
