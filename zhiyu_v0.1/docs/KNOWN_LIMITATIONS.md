# v1.0 已知限制与正式主张

仅 CONTROLLED LAB；Stable Prototype 不等于Production Ready、Enterprise HA、MSSP多租户或99.99% SLA。当前最终Gate状态见 [V1.0_STATUS](../V1.0_STATUS.json)，历史PASS不能替代当前候选签署。

| 项目 | 正式边界 |
|---|---|
| Production / customer deployment / long-term SLA | NOT VALIDATED |
| Cloud / Windows Sensor / OT/ICS | NOT VALIDATED |
| HA / multi-tenancy | NOT IMPLEMENTED |
| Linux实体主机Clean Install | NOT_RUN；Linux容器结果不替代第二台真实主机 |
| general AI semantic correctness | NOT PROVEN |
| AI closed-loop superiority | NOT CLAIMED；只主张辅助分析/规划/建议 |
| G0人工/原设备对照 | NOT INCLUDED IN V1.0 CLAIM |
| 公网或跨机TLS部署 | NOT VALIDATED；Reference HTTP仅回环 |
| 会话/内存快照 | API重启丢失，需重新登录/创建；持久录制按原档案恢复 |
| 备份完全离线重建整机 | NOT VALIDATED；权重、镜像及运行依赖不打进逻辑备份 |
| 图谱与时间线 | 真实引用/时间语义，不证明攻击因果；有界截断与历史不完整标记 |
| 报告 | UNREVIEWED_DRAFT，无人工签名或批准发布 |
| 依赖扫描 | 扫描时点/数据库覆盖的已知漏洞；未检出不证明不存在漏洞 |

默认AI OFF，启用默认SHADOW，高风险自主执行0。固定A–E含明确SCRIPTED_NOT_AI案例，用于安全拒绝/验证边界，不冒充真实模型能力。REFERENCE_GROUNDED只表示引用约束通过，confidence非校准概率。详见 [AI Value最终处置](AI_VALUE_FINAL_POSITION_v1.0.md)。

最终v1.0全Gate PASS后停止，不自动进入v1.1/v2、HA、多租户、新Agent或新Sensor。

第三方镜像仍有520个Critical/High package/target告警出现项，按固定可信CONTROLLED LAB运行路径逐条评估，未声称组件普遍不受影响、已修复或零漏洞。PCRE/libpcap/OpenSSL、Wazuh内置库等运行路径仍有剩余风险；禁止接入任意恶意流量/陌生Lab peer或公开服务后沿用本版结论。[全部决策与补丁](DEPENDENCY_SECURITY_REVIEW_v1.0.md)。

基础镜像已按digest冻结，Python/npm按锁/hash校验且前端重建bytes一致；Sensor apt软件仓库后续可能更新包，未主张未来重建Docker镜像字节完全相同。交付记录本次实际镜像ID/SBOM/扫描和生效配置，重建后须重新盘点与运行复验。
