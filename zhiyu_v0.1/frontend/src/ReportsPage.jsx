import React,{useEffect,useRef,useState} from 'react';
import {flushSync} from 'react-dom';
import {toast} from 'sonner';
import {Info,Download,Printer,ArrowDown} from 'lucide-react';
import {queryPath,useRemote,ApiError,errorMessage} from './api';
import {validateReport,reportExport,saveExport} from './report';
import {absoluteTime,incidentView,verificationState,factsOf,objectiveLabels} from './data';
import {FactList,ReadState,FieldValue} from './ProductUI';
import {Status,numberToken} from './ui';
import {ReportFacts,ReportSection,VerificationMatrix,ReportRecords,ReportIndex} from './ReportElements';
import BrandMark from './BrandMark';
import RecordReference from './RecordReference';
import {displayValue,decisionLabel,modeLabel,historyLabel,timeLabel,stageLabel,basisLabel,limitationText} from './presentation';
import './report.css';
import './report-layout.css';

const sections=[['summary','执行摘要'],['scope','范围与方法'],['evidence','事实与证据'],['timeline','时间与来源'],['response','决策与授权'],['execution','执行回执'],['verification','独立验证'],['followup','状态与重规划'],['limits','限制与文档控制']];
/** @type {Array<[string,string,string[]]>} */
const sourceGroups=[
 ['evidence','证据与事件',['evidence','event']],
 ['lineage','原始来源与关联',['raw','normalization','group','group_member','correlation','event_resource','audit']],
 ['model','模型输入与分析',['context','ai_context','model_request','model_receipt','model_run','analysis']],
 ['proposal','提案与计划',['proposal','decision','plan']],
 ['authorization','授权与风险',['authorization_context','authorization','risk','approval']],
 ['execution','动作与执行',['task','action','attempt','result']],
 ['verification','独立验证',['verification_spec','check','observation','verification']],
 ['followup','状态与重规划',['state_update','state','state_relation','replan']]
];
export default function ReportsPage({snapshot,params,onReload,contextPicker=null}){
 const state=useRemote(queryPath(`snapshots/${encodeURIComponent(snapshot.snapshot_id)}/report`,params),value=>{validateReport(value);if(value.snapshot_id!==snapshot.snapshot_id||value.content_sha256!==snapshot.content_sha256)throw new ApiError(0,'report_snapshot_mismatch');return value;});
 return <ReadState state={state} onRetry={onReload}>{report=><ReportDocument key={report.snapshot_id} report={report} params={params} contextPicker={contextPicker}/>}</ReadState>;
}
export function ReportDocument({report,params,contextPicker}){
 const snapshot=report.snapshot,[exporting,setExporting]=useState(null),[active,setActive]=useState('summary'),[printing,setPrinting]=useState(false),pending=useRef(null),article=useRef(null),scrollFrame=useRef(null);
 useEffect(()=>()=>{pending.current?.abort();cancelAnimationFrame(scrollFrame.current);},[]);
 useEffect(()=>{
  const before=()=>flushSync(()=>setPrinting(true)),after=()=>setPrinting(false);
  addEventListener('beforeprint',before);addEventListener('afterprint',after);
  return()=>{removeEventListener('beforeprint',before);removeEventListener('afterprint',after);};
 },[]);
 useEffect(()=>{
  const container=article.current?.closest('.main-scroll');if(!container)return;
  let frame;
  const update=()=>{cancelAnimationFrame(frame);frame=requestAnimationFrame(()=>{const offset=container.getBoundingClientRect().top+numberToken('--s6');let current='summary';for(const [id] of sections){const node=article.current?.querySelector(`#report-${id}`);if(node?.getBoundingClientRect().top<=offset)current=id;}setActive(current);});};
  container.addEventListener('scroll',update,{passive:true});update();
  return()=>{cancelAnimationFrame(frame);container.removeEventListener('scroll',update);};
 },[]);
 const download=async format=>{if(exporting)return;setExporting(format);const controller=new AbortController();pending.current=controller;try{const result=await reportExport(report,params,format,controller.signal);if(!controller.signal.aborted){saveExport(result);toast.success('报告已校验，开始下载');}}catch(error){if(!controller.signal.aborted)toast.error(errorMessage(error));}finally{if(!controller.signal.aborted)setExporting(null);}};
 const root=snapshot.facts.find(fact=>fact.kind==='incident'),record=incidentView({incident_id:snapshot.incident_id,...root?.fields},snapshot),verdict=verificationState(record,Date.parse(snapshot.as_of));
 const groups=Object.fromEntries(sourceGroups.map(([id,,kinds])=>[id,factsOf(snapshot,...kinds)]));
 const jump=id=>{
  const section=article.current?.querySelector(`#report-${id}`),container=article.current?.closest('.main-scroll');if(!section||!container)return;
  cancelAnimationFrame(scrollFrame.current);setActive(id);section.querySelector('h3')?.focus({preventScroll:true});
  const from=container.scrollTop,to=Math.max(0,Math.min(container.scrollHeight-container.clientHeight,from+section.getBoundingClientRect().top-container.getBoundingClientRect().top-numberToken('--s6')));
  if(matchMedia('(prefers-reduced-motion: reduce)').matches){container.scrollTo({top:to,behavior:'instant'});return;}
  const start=performance.now(),duration=numberToken('--motion-panel');
  const draw=now=>{const progress=Math.min(1,(now-start)/duration);container.scrollTo({top:from+(to-from)*(1-(1-progress)**5),behavior:'instant'});if(progress<1)scrollFrame.current=requestAnimationFrame(draw);};
  scrollFrame.current=requestAnimationFrame(draw);
 };
 const documentFacts=[['报告编号',report.report_id],['报告 JSON SHA-256',report.report_sha256],['快照 ID',snapshot.snapshot_id],['内容 SHA-256',snapshot.content_sha256],['生成依据时间',absoluteTime(snapshot.as_of)],['读取有效至',absoluteTime(snapshot.expires_at)],['环境与读取范围',`${snapshot.environment_id} / ${snapshot.scope_id||'获准整环境'}`],['事件 ID',record.id]];
 const referenceLabels=new Set(['报告编号','报告 JSON SHA-256','快照 ID','内容 SHA-256','事件 ID']);
 return <>
  <div className="page-tools report-tools">{contextPicker}<div className="tools-spacer"/><button className="button secondary report-print-button" onClick={()=>window.print()}><Printer/>打印 / 存为 PDF</button>{['json','markdown'].map(format=><button key={format} className="button secondary" disabled={!!exporting} aria-busy={exporting===format} onClick={()=>download(format)}><Download/>{exporting===format?'校验与下载中…':`下载 ${format==='json'?'JSON':'Markdown'}`}</button>)}<p className="report-export-note sr-only">JSON / Markdown 保留同一快照的原始记录与完整性校验。</p></div>
  <div className="report-layout document-layout"><nav className="report-toc document-toc" aria-label="报告目录"><span className="eyebrow">阅读目录</span>{sections.map(([id,title],i)=><button key={id} aria-current={active===id?'location':undefined} onClick={()=>jump(id)}><span>{String(i+1).padStart(2,'0')}</span>{title}</button>)}<p>固定快照 · 未复核草稿<br/>所有时间为 UTC+08:00</p></nav>
   <article ref={article} className="report-paper document-paper formal-report" aria-label="安全事件响应与独立验证报告"><div className="document-sheet">
    <header className="document-cover"><div className="document-brand"><BrandMark/><span className="document-wordmark">智御</span><span className="brand-descriptor">网络安全自主决策与持续验证平台</span><span className="small-badge">未复核草稿</span></div><h2>安全事件响应与独立验证报告</h2><div className="report-cover-meta"><strong>{record.name}</strong><span className={`priority ${record.priority.toLowerCase()}`}>{record.priority}</span><Status status={record.status}/><span>依据时间 {absoluteTime(snapshot.as_of)}</span></div><div className="document-disclosure"><Info/><span>受控测试环境 · {modeLabel(snapshot.run_mode)} · {historyLabel(snapshot.history_completeness)} · {snapshot.truncated?'已截断':'预算内'} · 仅覆盖当前授权快照，不代表生产验收。</span></div><div className="print-only document-print-control"><ReportFacts rows={documentFacts}/></div></header>
    <ReportSection id="summary" number="01" title="执行摘要"><div className="document-verdict"><span className="eyebrow">快照时最新验证记录</span><strong>{verdict.verdict}</strong><p>结论以 {absoluteTime(snapshot.as_of)} 的固定快照为准。</p></div><VerificationMatrix verdict={verdict}/><ReportFacts className="report-status-grid" rows={[["事件状态",<Status key="status" status={record.status}/>],["AI 提案状态",displayValue(record.decision)],["授权决定",decisionLabel(record.policy)],["执行回执",displayValue(record.execution)]]}/><p className="report-boundary">AI 提案不构成授权；执行成功不等于独立验证通过。授权、执行与验证分别记录。</p><button className="report-anchor text-button" onClick={()=>jump('verification')}>查阅验证目标与有效期<ArrowDown/></button></ReportSection>
    <ReportSection id="scope" number="02" title="范围与方法" description="明确本份报告覆盖的对象、读取边界与数据完整性。"><ReportFacts className="report-brief" rows={[["受影响资源",record.asset],["读取范围",snapshot.scope_id||'获准整环境'],["授权策略版本",snapshot.access_policy_version],["历史完整性",displayValue(snapshot.history_completeness)||'未知'],["数据截断",snapshot.truncated?`已截断 · ${snapshot.omitted_count??'数量未知'} 条省略`:'预算内'],["读取有效至",absoluteTime(snapshot.expires_at)]]}/><p>仅使用系统明确引用的同一事务快照。缺失、未知、过期与截断不等于没有风险；文本相似和时间相邻不建立攻击因果。</p></ReportSection>
    <ReportSection id="evidence" number="03" title="事实与证据" description="来源类型、声明与信任状态按原记录呈现；哈希只能用于关联完整性。"><ReportFacts className="report-brief" rows={[["证据记录",factsOf(snapshot,'evidence').length],["事件记录",factsOf(snapshot,'event').length],["来源类型",record.sources.filter(Boolean).join(' · ')||'未提供']]}/><ReportIndex facts={groups.evidence} fields={['source_type','outcome','claim_kind','trust_status','data_origin']} title="事实与证据索引"/><ReportRecords facts={groups.evidence}/></ReportSection>
    <ReportSection id="timeline" number="04" title="时间与来源" description="时间保留原始语义与时钟状态；排列顺序不表示攻击步骤。"><div className="report-table-scroll" tabIndex={0} role="region" aria-label="报告时间线"><table className="document-table"><thead><tr><th>来源时间 / 语义</th><th>阶段 / 对象</th><th>状态 / 依据</th></tr></thead><tbody>{report.timeline.map(entry=><tr key={entry.id}><td>{absoluteTime(entry.at)}<small>{timeLabel(entry.time_semantics)}</small></td><td>{stageLabel(entry.stage)}<RecordReference value={entry.object_ref} label="时间点对象引用"/></td><td>{displayValue(entry.status)||'未记录'}<small>{basisLabel(entry.basis)} · {displayValue(entry.clock_status)}</small></td></tr>)}</tbody></table></div><p className="document-note">页面与打印保留全部 {report.timeline.length} 个已读取时间点；原始导出包含同一快照记录{report.timeline_truncated?'（快照时间线本身已截断）':''}。时间相邻不代表因果。</p><ReportRecords facts={groups.lineage} title="原始来源与关联记录"/></ReportSection>
    <ReportSection id="response" number="05" title="决策与授权" description="模型分析、方案校验和确定性授权分别记录，不能互相替代。"><ReportFacts className="report-brief" rows={[["AI 提案状态",displayValue(record.decision)],["授权决定",decisionLabel(record.policy)],["审批记录",`${factsOf(snapshot,'approval').length} 条已读取记录（不据此判断是否需要审批）`]]}/><h4>模型与方案</h4><ReportIndex facts={[...groups.model.filter(fact=>fact.kind==='analysis'),...groups.proposal]} fields={['status','mode','incident_summary','uncertainty','semantic_correctness','confidence_semantics']} title="模型与方案索引"/><p className="report-boundary">模型置信度为模型自报、未经校准。引用已核对不代表分析内容正确。</p><ReportRecords facts={groups.model} title="模型输入与分析记录"/><ReportRecords facts={groups.proposal} title="提案与计划记录"/><h4>授权与风险</h4><ReportIndex facts={groups.authorization.filter(fact=>['authorization','approval','risk'].includes(fact.kind))} fields={['action_id','outcome','status','assessed_risk','human_approval_required','business_impact','denied_dimensions','policy_version','scope_id','reasons']} title="授权与风险索引"/><ReportRecords facts={groups.authorization} title="完整授权与风险记录"/></ReportSection>
    <ReportSection id="execution" number="06" title="执行回执" description="本节记录动作及回执，不据此宣称安全目标已经实现。"><ReportFacts className="report-brief" rows={[["执行回执",displayValue(record.execution)],["动作 / 尝试 / 回执",`${factsOf(snapshot,'action').length} / ${factsOf(snapshot,'attempt').length} / ${factsOf(snapshot,'result').length}`]]}/><ReportIndex facts={groups.execution} fields={['status','execution_outcome','scope_id','policy_version']} title="执行记录索引"/><ReportRecords facts={groups.execution}/></ReportSection>
    <ReportSection id="verification" number="07" title="独立验证" description="安全目标、业务健康与观测有效性共同约束验证结论。"><VerificationMatrix verdict={verdict}/><ReportFacts className="report-brief" rows={[["验证目标",objectiveLabels[record.objective]||record.objective||'未提供'],["验证声明",record.claim?<FieldValue field="claim" value={record.claim}/>:'尚未读取到验证声明'],["独立验证有效至",record.validUntil?absoluteTime(record.validUntil):'未提供，不能证明当前状态'],["快照时结论",verdict.verdict]]}/><ReportIndex facts={groups.verification} fields={['status','security_status','business_status','observation_status','execution_status','assertion_status','assertions','reason']} title="独立验证记录索引"/><ReportRecords facts={groups.verification}/></ReportSection>
    <ReportSection id="followup" number="08" title="状态与重规划" description="状态变化与受限重规划按原记录保留；本报告不自动关闭事件或创建处置任务。"><ReportIndex facts={groups.followup} fields={['status','claim_kind','replan_count','reason','scope_id','policy_version']} title="状态与重规划索引"/><ReportRecords facts={groups.followup}/></ReportSection>
    <ReportSection id="limits" number="09" title="限制与文档控制"><ul className="document-limits">{report.limitations.map(text=><li key={text}>{limitationText(text)}</li>)}</ul><details className="record-fields"><summary>查看原始限制说明</summary><ul>{report.limitations.map(text=><li key={text}>{text}</li>)}</ul></details><div className="document-metadata"><h4>文档信息与完整校验值</h4><ReportFacts rows={documentFacts.map(([label,value])=>[label,referenceLabels.has(label)?<RecordReference key={label} value={value} label={label}/>:value])}/></div><p className="document-note">可视化报告重排同一快照的记录；JSON / Markdown 原始导出保留服务端内容。打印附录保留全部 {snapshot.facts.length} 条已读取来源记录及完整字段。</p><ReportRecords facts={snapshot.facts} title="全部已读取来源记录"/></ReportSection>
    {printing?<section className="report-source-appendix print-only" aria-label="完整来源记录打印附录"><h2>附录 · 完整来源记录</h2><p>同一固定快照的 {snapshot.facts.length} 条已读取记录。原始字段按记录保留，缺失不补齐。</p><h3>原始限制说明</h3><ul className="document-limits">{report.limitations.map(text=><li key={text}>{text}</li>)}</ul><FactList facts={snapshot.facts} title="完整来源记录"/></section>:null}
    <div className="document-folio"><span>{snapshot.snapshot_id} / {modeLabel(snapshot.run_mode)}</span><span>报告协议 0.9.0 · 未复核草稿</span></div>
   </div></article>
  </div>
 </>;
}
