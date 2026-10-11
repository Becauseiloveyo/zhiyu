# v1.0 Final Evidence Index

v1.0.0 PASS / STABLE PROTOTYPE。历史失败/NOT_RUN/脚本反例保持原标签，不能当作真实生产或模型能力证据。

| 内容 | 实际证据 | SHA256 |
|---|---|---|
| Candidate | [RC_STATE_v1.0.0.json](../artifacts/RC_STATE_v1.0.0.json) | `ecc46957a1ca29e73da486c5dcb6761d9bfed5f36ad85fa6d9d612d3c75cfa1e` |
| Gate B clean install | [gate-b-final.json](../artifacts/v1.0/gate-b-final.json) | `1c0e91900a7c52b471459af672cd9f9b38726ea193fa9b24986428bffe2fb2a4` |
| Gate B current delta | [gate-b-rc11-targeted-revalidation.json](../artifacts/v1.0/gate-b-rc11-targeted-revalidation.json) | `5603e9d8b96be704a87257b44546199ec56ce6c057d8299b43903591d4f69528` |
| Gate C historical/backup/restore | [gate-c-final.json](../artifacts/v1.0/gate-c-final.json) | `a075e358cb3212739dc75914808c7a271dc7b36722fc139e3f1029f642e80c75` |
| RC9 real recovery | [gate-c-rc9-logging-restore.json](../artifacts/v1.0/gate-c-rc9-logging-restore.json) | `93f53ebff1583a7040b95b89a89fbcc07ab386fb4682ef1d1c9458f861db218c` |
| Failed upgrade controls | [gate-c-recovery-faults.json](../artifacts/v1.0/gate-c-recovery-faults.json) | `2cae5c20eedab284c21fb2bcfcc78962bf025b9253fa507cd18f356f5b8e82c8` |
| Gate D | [gate-d-final.json](../artifacts/v1.0/gate-d-final.json) | `a24b13686036ee1ea18d98a3592b50426e26ce7d6130db306a05b55ddefe919b` |
| SBOM schema | [sbom-validation.json](../artifacts/v1.0/security/sbom-validation.json) | `cf8547a8f8af5524b864f55402b83c5639816236a6234192fe8f535aa4467e06` |
| Dependency decisions | [vulnerability-disposition.json](../artifacts/v1.0/security/vulnerability-disposition.json) | `5c8c83a23db5c01826241ee94b467cc68a2d580cdb0cf24f4f1ca78b9bfaffc4` |
| Service inventory | [service-inventory.json](../artifacts/v1.0/security/service-inventory.json) | `8927e86dcf8902799c689585397495c72298acb214c05d689ae9fab994304492` |
| Host backend | [final-backend.xml](../artifacts/v1.0/final-backend.xml) | `383123c6d53665289548441a0a69901279dd0d24bb18fe1c3ad4c888d92e47e3` |
| Linux backend | [test-results.xml](../docs/m5-runtime/zhiyu-smoke-397c45f14058/test-results.xml) | `eb68685f82c2c25300760782e83f2192d8a09d5976c6043bef870ff12f67af5e` |
| Docker189 + real model24 | [result.json](../docs/m5-runtime/zhiyu-smoke-397c45f14058/result.json) | `0d86475c504e92dc41c9882bc0b39e57355d6614d4eb31cbdbba931651b4ca54` |
| Original tests retained | [final-test-retention.json](../artifacts/v1.0/final-test-retention.json) | `72ea2de28281cbd3211f540654bba5b0d2710667ef023e30efcb584dc757cdfd` |
| Frontend/static | [final-frontend.json](../artifacts/v1.0/final-frontend.json) | `3337ae13619f0654dc3c851457ddfc8d0b42f7f8b11adeae18e3ae91242152d6` |
| Browser pages | [gate-e-browser-navigation.json](../artifacts/v1.0/gate-e-browser-navigation.json) | `3033e2437483053ab66a8b03c0c23081fef35ef502629a12e0d9cdfc2476b6be` |
| Browser honest health | [gate-e-browser-system-status.json](../artifacts/v1.0/gate-e-browser-system-status.json) | `b9d5f4868d686f7ad7919d520f27d5f67c54516ba9200a930ca88bc66136540a` |
| Browser errors | [gate-e-browser-errors.json](../artifacts/v1.0/gate-e-browser-errors.json) | `dbd66eea606fa0b619e3fa06c8d40600dc2fb1aa871d075f2d12192a97109fb7` |
| Real API stop/recovery | [gate-e-api-stop-recovery.json](../artifacts/v1.0/gate-e-api-stop-recovery.json) | `044fc8ce56cc2e4dff6a2a30b7d7a875c5c8b11dc0174fe78cc04bc915ca46d7` |
| Real Sensor stop/recovery | [gate-e-sensor-stop-recovery.json](../artifacts/v1.0/gate-e-sensor-stop-recovery.json) | `8cb36fb01733297ad14f75affecc30006bb61873b7f57009115dfa32088e9baf` |
| A-E + cleanup/replay/report | [gate-e-demo-replay-cleanup.json](../artifacts/v1.0/gate-e-demo-replay-cleanup.json) | `a123c1e38e5e565e27d63bb591eb89dcd46c3bbf6dbca054e8afb676b12f24a4` |
| LIVE exports | [gate-e-report-export-integrity.json](../artifacts/v1.0/gate-e-report-export-integrity.json) | `a3662ac77b3aab819e8c1007f119d8bf6d95751ec53dbe11ebe0c3faacc1dc5e` |
| A reset | [gate-e-browser-reset-a.json](../artifacts/v1.0/gate-e-browser-reset-a.json) | `06acef3a414f8fc5b764c8269954d164dcf91ae0f6d6ac33cbe11e46f93c0411` |
| Final canonical risk/audit | [gate-e-final-product-acceptance.json](../artifacts/v1.0/gate-e-final-product-acceptance.json) | `791967641a4de7bfa76d1b7b900ccf1a1d42774ab9fa2825d44db762c0f018ff` |
| Performance concurrent | [api-performance.json](../artifacts/v1.0/api-performance.json) | `ab71a67fb9a2d8c100655f809170e0cf454b54b6c3c52db08dbf7f0f8aa23cf9` |
| Performance idle | [api-performance-idle.json](../artifacts/v1.0/api-performance-idle.json) | `f3e7553e439d32f9cf6fd00e9434724005f1f5656859508fa31e77e29ca304f4` |
| Raw source/images/UI | [final-source-correspondence.json](../artifacts/v1.0/final-source-correspondence.json) | `9f075ca7eb825de0e0989158aa156b6070f1909dec75a9131859a18fe8f4da05` |
| Private log redaction | [operator-log-redaction.json](../artifacts/v1.0/security/operator-log-redaction.json) | `7f50042c1b4853bd44f84a46de1c218e688cf7c3bcb26c739d7ed8a976c72845` |
| Gate D final current docs/scan impact | [gate-d-final-revalidation.json](../artifacts/v1.0/gate-d-final-revalidation.json) | `5a23172df0585478f2afa5f5a3c61eacc67cd4829640a0552128fd0ee0fefec4` |

A–E各17项HTTP/source/recording只读校验分别为 `artifacts/v1.0/gate-e-scenario-{a,b,c,d,e}-http.json`；现场源证据在 `artifacts/v1.0/lab/<run_id>/`，封存快照在 `artifacts/v1.0/recordings/`，报告实际下载在 `output/playwright/downloads/v1-live-report.*` 和 `v1-replay-{A,B,C,D,E}.*`。完整各文件SHA见包内Manifest。

[A01–A15](A01_A15_FINAL_REVALIDATION_v1.0.md)、[文档/安全](SECURITY_BASELINE_v1.0.md)、[License](THIRD_PARTY_LICENSES.md)、[SBOM](../artifacts/SBOM_v1.0.0.cdx.json)、[最终ZIP验证](../artifacts/PACKAGE_VALIDATION_v1.0.0.json)、[Whole-ZIP SHA](../artifacts/SHA256SUMS_v1.0.0.txt)。最后两项随ZIP外置交付，不在ZIP内自引用。
