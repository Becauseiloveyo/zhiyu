// Presentation utilities only. No synthetic business records or fallback data.
import {eventTitle} from './presentation';
export const absoluteTime=at=>Number.isFinite(Date.parse(at))?new Intl.DateTimeFormat('zh-CN',{timeZone:'Asia/Shanghai',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false}).format(new Date(at))+' +08:00':'未记录';
export const relativeTime=at=>{if(!Number.isFinite(Date.parse(at)))return'未记录';const seconds=Math.round((Date.now()-Date.parse(at))/1000);if(seconds<0)return'来源时间在未来';if(seconds<60)return'刚刚';if(seconds<3600)return`${Math.floor(seconds/60)} 分钟前`;if(seconds<86400)return`${Math.floor(seconds/3600)} 小时前`;return`${Math.floor(seconds/86400)} 天前`;};
export const statusMap={NEW:{label:'待研判',tone:'warn'},TRIAGED:{label:'已分诊',tone:'neutral'},INVESTIGATING:{label:'调查中',tone:'info'},PLANNED:{label:'计划已生成',tone:'info'},WAITING_APPROVAL:{label:'等待审批',tone:'warn'},EXECUTING:{label:'执行中',tone:'info'},VERIFYING:{label:'验证中',tone:'info'},CONTAINED:{label:'已遏制',tone:'neutral'},RESOLVED:{label:'已解决',tone:'ok'},CLOSED:{label:'已关闭',tone:'neutral'},HUMAN_REVIEW:{label:'待复核',tone:'warn'},REOPENED:{label:'重新打开',tone:'warn'}};
export const checkLabels=['安全目标','业务健康','观测有效性'];
export const objectiveLabels={DETECTION:'检测确认',CONTAINMENT:'临时遏制',REMEDIATION:'修复',RECOVERY:'恢复',CLEANUP:'清理'};
export const isTodo=r=>['NEW','WAITING_APPROVAL','HUMAN_REVIEW','REOPENED'].includes(r.status);
export const ordered=items=>[...items].sort((a,b)=>a.priority.localeCompare(b.priority)||Date.parse(b.at)-Date.parse(a.at));
export function verificationState(record,asOf=Date.now()){
 const expired=!!record.validUntil&&Date.parse(record.validUntil)<=asOf;const checks=record.checks||['未提供','未提供','未提供'];
 const hasChecks=checks.some(value=>value!=='未提供');const complete=checks.every(value=>value==='PASS')&&!!record.validUntil&&!expired&&record.verificationStatus==='PASS';
 const verdict=expired?'历史结果已过期':complete?'独立验证通过':checks.includes('FAIL')?'独立验证失败':hasChecks?'验证尚不能确认通过':'尚未形成验证结论';
 return{expired,hasChecks,complete,verdict,rows:checkLabels.map((label,i)=>({label,value:checks[i],effective:expired?'过期，不能证明当前状态':checks[i]==='未提供'?'未提供检查记录':checks[i]==='INCONCLUSIVE'?'证据不足，保持存疑':record.validUntil?'针对指定目标与有效期':'有效期未提供',tone:expired||checks[i]==='未提供'?'neutral':checks[i]==='PASS'&&record.validUntil?'ok':checks[i]==='FAIL'?'danger':'warn'}))};
}
export const factsOf=(snapshot,...kinds)=>(snapshot?.facts||[]).filter(f=>kinds.includes(f.kind));
export function latest(snapshot,kind){
 const facts=factsOf(snapshot,kind);if(facts.length<2)return facts[0];
 const dated=facts.map(fact=>({fact,at:Date.parse(fact.fields.finished_at||fact.fields.completed_at||fact.fields.created_at||fact.fields.observed_at||fact.fields.started_at||'')}));
 // Missing or tied source timestamps do not establish a latest record. IDs are not clocks.
 if(dated.some(item=>!Number.isFinite(item.at)))return undefined;
 dated.sort((a,b)=>b.at-a.at);return dated[0].at===dated[1].at?undefined:dated[0].fact;
}
export function incidentView(row,snapshot){
 const verification=latest(snapshot,'verification'),result=latest(snapshot,'result'),attempt=latest(snapshot,'attempt'),authorization=latest(snapshot,'authorization'),proposal=latest(snapshot,'proposal');
 return{id:row.incident_id||snapshot?.incident_id,name:eventTitle(row.title),status:row.status,priority:row.priority,at:row.updated_at,asset:(row.affected_asset_ids||[]).join(' · ')||'资源绑定未提供',riskScore:row.risk_score??null,
  checks:verification?[verification.fields.security_status,verification.fields.business_status,verification.fields.observation_status]:['未提供','未提供','未提供'],validUntil:verification?.fields.valid_until,verificationStatus:verification?.fields.status,objective:verification?.fields.objective_type,claim:verification?.fields.claim,
  execution:result?.fields.execution_outcome||(factsOf(snapshot,'result').length?'多条执行回执，最新顺序未确定':attempt?.fields.status||'未读取到执行回执'),policy:authorization?`${authorization.fields.outcome} · ${authorization.fields.assessed_risk}`:factsOf(snapshot,'authorization').length?'多条授权决定，请按动作查阅':'未读取到授权决定',decision:proposal?.fields.status||(factsOf(snapshot,'proposal').length?'多条提案，最新顺序未确定':'未读取到 AI 提案'),
  sources:[...new Set(factsOf(snapshot,'event').map(f=>f.fields.source_type))],snapshot};
}
export function recordTimeline(record){return record.snapshot?.timeline||[];}
