# 实际v1.0.0手册截图

2026-10-05真实本机Browser操作截图；10个必需页面加1张ModelRun补图。截图由工具实际采集并视觉检查，未修改图像、未使用mockup。分辨率均1920×1080。这里包含既有Lab事实和本轮新A事实，不能假定各张图同一Incident或同一时点。关闭系统后截图只代表历史观察。

| 图片 | 来源说明 | SHA256 |
|---|---|---|
| [overview.png](overview.png) | 本轮新A首轮子环境；四项实际KPI 8/1/0/1；Sensor已清理、覆盖UNKNOWN，并非实时健康PASS。 | d057f6dead516b740d135c8c82dc055a960c3e0b6a8c76e60e8d85dcd94b6158 |
| [incident-list.png](incident-list.png) | 本轮打开的既有A Lab记录（inc-3e00…）；VERIFYING/搜索筛选状态。不是本轮新A的同一Incident。 | a0c51f94a914cb9b5ec61accaa25f193e5c0df88acb32b1c0e91a7bbb25c5f91 |
| [incident-detail.png](incident-detail.png) | 本轮新A首轮（inc-20293…）的实际事件详情与摘要；历史验证有效期仍如实显示。 | adf9f68c767f1b7110066b7074bbbf09426e158b9ab14d7b1dd8a90549559e59 |
| [timeline.png](timeline.png) | 既有A Lab记录（inc-3e00…）的实际112点时间线；UTC轴与来源时间语义。 | e08b93b60b35bc982e55b6c062fced2d819671282bdeb29a54bb824509da533a |
| [graph.png](graph.png) | 本轮新A首轮（inc-20293…）；默认两层59/94实体，真实引用/推断/UNKNOWN，非攻击因果图。 | 33354df265aee2cd7cc9ce55f90153a2cf57c393498261f1c6846ae57e8953b4 |
| [ai-decision.png](ai-decision.png) | 本轮新A首轮（inc-20293…）决策页顶部；上下文与模型分析，不是UI设计稿。 | 4e5959a46247e79b749e7f57d724f4a1c209b8153786f379597687916201d06d |
| [ai-modelrun.png](ai-modelrun.png) | 本轮新A首轮实际ModelRun字段；provider demo、model/revision/hash与45734ms可见。 | afabbe168fea1130bb028d171b1cc747be29606accba4b3dbf445ca35efae621 |
| [verification.png](verification.png) | 本轮新A首轮三维历史PASS均显示已过期；不能当作当前保证安全。 | 1ec94f6eb982052539f712da599e926ae7d02145b7f1a0849716b5ddcd3e387c |
| [report.png](report.png) | 既有A Lab记录（inc-3e00…）的实际报告页；八节未复核草稿，JSON/Markdown入口。 | 69c245d2cef7bb346e234598de5a964c5765572710f4d72b03e61887e503be8f |
| [demo.png](demo.png) | 登记控制环境的固定A–E目录；真实/脚本模型标签与预期可见，运行结果另见走查JSON。 | bdff4b298b98f2cf16c78f07eb983bdc6b2cce270e46d0b0bf961e769bcffd86 |
| [system-status.png](system-status.png) | 本轮新A首轮清理后的健康面板；DB AVAILABLE，过期Sensor及模型/WorkerUNKNOWN如实保留。 | 7a3520de7a04d90edbd001351aa8daa44161b97c66f19f47cbdf2604f4864920 |

[来源路径、文件时间与身份manifest](manifest.json)。file_mtime是实际文件采集时间，页面as_of以截图/关联JSON为准。验收结果见[完整走查](../FULL_PRODUCT_WALKTHROUGH_v1.0.0.md)。
