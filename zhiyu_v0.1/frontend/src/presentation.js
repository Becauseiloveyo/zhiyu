// Display labels only; canonical identifiers and evidence semantics stay intact.
export const shortId=(value,head=12,tail=6)=>{
 const text=String(value??'未记录');
 return text.length>head+tail+1?`${text.slice(0,head)}…${text.slice(-tail)}`:text;
};
const kinds={incident:'安全事件',resource:'资源',event_resource:'事件资源关联',group_member:'分组成员',event:'事件记录',evidence:'证据',raw:'原始记录',normalization:'标准化',group:'事件分组',correlation:'关联记录',context:'分析上下文',ai_context:'模型上下文',model_request:'模型请求',model_receipt:'模型回执',model_run:'模型运行',analysis:'模型分析',proposal:'模型提案',decision:'决策记录',plan:'处置计划',task:'任务',authorization_context:'授权上下文',authorization:'授权决定',risk:'风险评估',approval:'审批记录',action:'处置动作',attempt:'执行尝试',result:'执行回执',verification_spec:'验证定义',check:'检查项',observation:'观测记录',verification:'独立验证',state_update:'状态更新',state:'状态记录',state_relation:'状态关联',replan:'重规划',audit:'审计记录'};
export const kindLabel=kind=>kinds[kind]||kind;
const healthLabels={HEALTHY:'正常',UNKNOWN:'未知',AVAILABLE:'可用',UNAVAILABLE:'不可用',OFF:'关闭',SHADOW:'影子模式',STALE:'已过期',DEGRADED:'降级',ERROR:'异常'};
export const healthLabel=value=>healthLabels[value]||value;

// These labels translate known schema values, never rewrite the stored facts.
const values={HEALTHY:'正常',NORMAL:'正常',CONTROLLED_AUTONOMY:'受控自主',NEW:'待研判',TRIAGED:'已分诊',INVESTIGATING:'调查中',PLANNED:'计划已生成',WAITING_APPROVAL:'等待审批',EXECUTING:'执行中',VERIFYING:'验证中',CONTAINED:'已遏制',RESOLVED:'已解决',CLOSED:'已关闭',HUMAN_REVIEW:'待复核',REOPENED:'重新打开',OBSERVED:'实际观测',DERIVED:'由记录计算生成',MODEL_INFERENCE:'模型推断',EXPLICIT_REFERENCE:'明确引用',UNKNOWN:'未知',CURRENT:'快照时有效',EXPIRED:'有效期已结束',STALE:'已过期',PASS:'通过',FAIL:'未通过',INCONCLUSIVE:'证据不足',NOT_RUN:'未运行',NOT_VALIDATED:'尚未验证',REFERENCE_GROUNDED:'引用已核对，内容尚未核实',MODEL_SELF_REPORTED:'模型自报，未校准',MODEL_SELF_REPORTED_UNCALIBRATED:'模型自报，未校准',SHADOW:'仅生成建议',OFF:'关闭',ALLOW:'允许',DENY:'拒绝',DENIED:'拒绝',EXECUTION_SUCCESS:'执行成功',SUCCEEDED:'执行完成',FAILED:'执行失败',RUNNING:'进行中',PENDING:'待处理',COMPLETE:'完整',PARTIAL:'不完整',TRUSTED:'时钟可信',VERIFIED_ORIGIN:'来源已核验',SOURCE_ASSERTION:'来源声明',OBSERVATION:'观察结果',SYNTHETIC:'合成数据',NETWORK_ENDPOINT:'网络端点',LOW:'低',MEDIUM:'中',HIGH:'高',LAB_PATH:'受控测试路径',CONTAINMENT:'临时遏制',LIVE:'实时读取',RECORDED_REPLAY:'历史回放'};
export const displayValue=value=>typeof value==='boolean'?(value?'是':'否'):values[value]||value;
export const basisLabel=value=>value==='UNKNOWN'||!value?'证据性质未标注':displayValue(value);
export const modeLabel=value=>value==='RECORDED_REPLAY'?'历史回放':value==='LIVE'?'实时读取':'读取模式未知';
export const historyLabel=value=>value==='COMPLETE'?'历史记录完整':value==='PARTIAL'?'历史记录不完整':'历史完整性未知';
export function eventTitle(title){
 const match=/^authentication:\s*(\[.*\])$/.exec(title||'');
 if(match){try{const addresses=JSON.parse(match[1]);if(Array.isArray(addresses)&&addresses.length&&addresses.every(x=>typeof x==='string'))return `认证活动 · ${addresses.join('、')}`;}catch{}}
 return title||'未提供事件名称';
}
export const eventSearchQuery=query=>['认证','认证活动'].includes(query.trim())?'authentication':query;
export const resourceName=resource=>resource?.fields?.display_name==='Real controlled Lab login service'?'受控测试登录服务':resource?.fields?.display_name||resource?.fields?.name||resource?.id||'资源名称未提供';
export const modelText=value=>({'The evidence for the affected resources is not provided.':'模型指出受影响资源的证据不足。','Independent confirmation of temporary Lab test-path restriction, business availability and observation coverage':'独立确认临时测试路径限制、业务可用性与观察覆盖。','Retain VERIFYING; human assessment of residual risk':'保持验证中，由人工复核剩余风险。','The affected resource is a network endpoint, as evidenced by the observed events and the correlation rules. The proposed task is to perform a safe HTTP probe on the affected resource to verify its reachability.':'模型将受影响资源判断为网络端点，建议进行只读的网页可达性检查。'})[value]||value;
export const limitationText=value=>String(value).replaceAll('CONTROLLED LAB','受控测试环境').replaceAll('PARTIAL','不完整').replaceAll('REFERENCE_GROUNDED 不等于 SEMANTICALLY_CORRECT','引用已核对不代表分析内容正确').replaceAll('confidence','置信度').replaceAll('Windows Sensor','Windows 采集器').replaceAll('Cloud','云环境').replaceAll('OT/ICS','工业控制系统').replaceAll('SLA','服务可用性约定').replaceAll('Hash','哈希');
export const relationLabel=value=>({AFFECTS_RESOURCE:'影响资源',EVENT_TARGET:'目标资源',BELONGS_TO_INCIDENT:'归属事件',EVIDENCE_FROM:'来源记录',EVIDENCE_REFERENCE:'引用证据',ANALYSIS_CONTEXT:'分析上下文',MODEL_RUN:'模型运行',MODEL_REQUEST:'模型请求',PRODUCED_STATE:'生成状态',ANALYSIS_REFERENCE:'引用分析',TARGETS_RESOURCE:'目标资源',TASK_REFERENCE:'关联任务',ACTION_REFERENCE:'关联动作',AUTHORIZATION_CONTEXT:'授权上下文',EXECUTION_RECEIPT:'执行回执',PLAN_REFERENCE:'关联计划',ACTION_RESULT:'执行结果',CHECKS_SPEC:'验证方案',CHECK_OBSERVATION:'检查观察',OBSERVATION_EVIDENCE:'观察证据',VERIFIES_RESOURCE:'验证资源',VERIFICATION_RESULT:'验证结果',ROOT_PLAN:'初始计划',PARENT_PLAN:'上级计划'})[value]||'其他记录引用';
export const timeLabel=value=>({source_timestamp:'来源时间',observed_at:'观测时间',first_seen_at:'首次关联时间',first_observed_at:'首次观测时间',last_seen_at:'最后关联时间',ingested_at:'入库时间',collected_at:'采集时间',created_at:'生成时间',received_at:'接收时间',timestamp:'记录时间',triaged_at:'分诊时间',started_at:'开始时间',completed_at:'完成时间',finished_at:'结束时间',queued_at:'排队时间',investigation_started_at:'开始调查时间',claimed_at:'领取时间',updated_at:'更新时间',checked_at:'检查时间'})[value]||'其他来源时间';
export const stageLabel=value=>({DETECTION:'检测',NORMALIZATION:'标准化',CORRELATION:'关联',INCIDENT:'事件',CONTEXT:'分析上下文',AI_ANALYSIS:'AI 分析',PROPOSAL:'建议',AUTHORIZATION:'授权',EXECUTION:'执行',VERIFICATION:'验证',STATE_UPDATE:'状态更新',REPLAN:'后续计划',EVIDENCE:'证据',AUDIT:'审计'})[value]||'其他阶段';
export const decisionLabel=value=>typeof value==='string'?value.replace(/^(ALLOW|DENY|SHADOW|EXECUTION_SUCCESS)(?=\s|$)/,match=>displayValue(match)):value;
