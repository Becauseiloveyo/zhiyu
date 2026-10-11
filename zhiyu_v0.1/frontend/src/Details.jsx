import React,{useId} from 'react';
import {ArrowUpRight,Info,ArrowRight} from 'lucide-react';
import {factsOf,verificationState,absoluteTime} from './data';
import {displayValue,modelText,resourceName} from './presentation';
import {Status,Time,Tabs,CheckRows} from './ui';
import {FactList,SnapshotNote} from './ProductUI';

const tabs=[['summary','概况'],['decision','研判与处置'],['verification','独立验证']];
export function summarizeSnapshot(snapshot){
 const events=factsOf(snapshot,'event'),root=factsOf(snapshot,'incident')[0],ids=root?.fields.affected_asset_ids||[];
 const resources=ids.map(id=>factsOf(snapshot,'resource').find(f=>f.id===id)||{id});
 const denied=events.filter(f=>f.fields.outcome==='DENIED').length,uncertainty=factsOf(snapshot,'analysis').map(f=>f.fields.uncertainty).filter(Boolean);
 return{events,resources,denied,uncertainty,evidenceCount:factsOf(snapshot,'evidence').length,fixedWindow:factsOf(snapshot,'group').some(f=>/^fixed-window\//.test(f.fields.algorithm_version||''))};
}
export default function Details({record,initialTab='summary',onTabChange,onNavigate,full=false}){
 const uid=useId(),tab=['evidence','records'].includes(initialTab)?initialTab:tabs.some(([id])=>id===initialTab)?initialTab:'summary';
 const snapshot=record.snapshot,summary=summarizeSnapshot(snapshot),verification=verificationState(record),authorization=factsOf(snapshot,'authorization'),results=factsOf(snapshot,'result');
 return <div className={`incident-detail ${full?'full-detail embedded-detail':''}`}>
  {!full?<><div className="detail-identity"><div className="identity-meta"><span className={`priority ${record.priority.toLowerCase()}`}>{record.priority}</span><Status status={record.status}/></div><h2>{record.name}</h2><div className="detail-subline"><Time at={record.at}/><button className="text-button" onClick={()=>onNavigate('incident',{incident:record.id,tab})}>打开事件<ArrowUpRight/></button></div></div><Tabs id={uid} items={tabs} value={tabs.some(([key])=>key===tab)?tab:'summary'} onChange={onTabChange}/></>:null}
  <div className="detail-body" {...(!full?{role:'tabpanel',id:`${uid}-panel`,'aria-labelledby':`${uid}-tab-${tab}`}:{})}>
   {tab==='summary'?<>
    <div className="decision-callout"><Info/><div><strong>{verification.expired?'需要复核剩余风险':verification.verdict}</strong><p>{record.validUntil?`上次验证有效至 ${absoluteTime(record.validUntil)}。`:'尚未提供验证有效期。'}{verification.expired?'当前结论需重新复核。':'结论仅适用于指定目标与有效期。'}</p></div><button className="button secondary" onClick={()=>onTabChange('verification')}>查看验证详情<ArrowRight/></button></div>
    <section className="section event-summary"><div className="section-heading"><h2>事件摘要</h2></div><p>{summary.events.length?`快照已读取 ${summary.events.length} 条事件记录${summary.denied===summary.events.length?'，记录结果均为拒绝':summary.denied?`，其中 ${summary.denied} 条记录结果为拒绝`:''}。`:'这份快照没有读取到关联事件记录。'}{summary.resources.length?`当前事件标记了 ${summary.resources.length} 个受影响资源。`:'受影响资源未提供。'}</p>
     <div className="event-summary-columns"><div><h3>涉及的资源</h3>{summary.resources.length?summary.resources.map(resource=><p key={resource.id}>{resourceName(resource)}</p>):<p>资源绑定未提供</p>}<button className="text-button" onClick={()=>onNavigate('graph',{incident:record.id,node:summary.resources.length===1?snapshot.facts.find(f=>f.kind==='resource'&&f.id===summary.resources[0].id)?.ref:null})}>查看资源关联<ArrowRight/></button></div><div><h3>待补充的证据</h3><p>{summary.uncertainty.length?summary.uncertainty.every(value=>modelText(value)!==value)?[...new Set(summary.uncertainty.map(modelText))].join(' '):'模型保留了不确定性，需要核对分析原文。':'当前快照未提供可读的模型不确定性说明。'}历史记录与引用范围不足时，不能据此确认攻击成功或更广泛的影响。</p><button className="text-button" onClick={()=>onTabChange('decision')}>查看分析依据<ArrowRight/></button></div></div>
     <div className="event-summary-meta"><span>优先级 {record.priority}</span><span>{summary.events.length} 条事件记录 · {summary.evidenceCount} 条证据</span>{summary.fixedWindow?<span>按时间窗口关联；具体触发原因未提供</span>:null}</div>
    </section>
    <section className="section processing-records"><div className="section-heading"><h2>处理记录</h2></div><table><thead><tr><th>阶段</th><th>记录结果</th><th>详情</th></tr></thead><tbody>
     <tr><td>AI 建议</td><td>{displayValue(record.decision)}</td><td><button className="text-button" onClick={()=>onTabChange('decision')}>查看建议</button></td></tr>
     <tr><td>策略授权</td><td>{authorization.length===1?`${displayValue(authorization[0].fields.outcome)}该次动作`:authorization.length?`${authorization.length} 条授权，按动作核对`:'未读取到授权'}</td><td><button className="text-button" onClick={()=>onTabChange('decision')}>查看授权</button></td></tr>
     <tr><td>动作执行</td><td>{results.length===1?displayValue(results[0].fields.execution_outcome):results.length?`${results.length} 条回执，按动作核对`:'未读取到执行回执'}</td><td><button className="text-button" onClick={()=>onTabChange('decision')}>查看执行</button></td></tr>
     <tr><td>独立验证</td><td>{verification.verdict}</td><td><button className="text-button" onClick={()=>onTabChange('verification')}>查看验证</button></td></tr>
    </tbody></table></section>
   </>:null}
   {tab==='decision'?<><div className="decision-callout"><Info/><div><strong>建议、授权与执行分别核对</strong><p>模型自报的置信度未经校准；引用核对不代表分析内容正确。仅生成建议的提案不能授权动作。</p></div></div><section className="detail-section"><h3>AI 分析与建议</h3><FactList facts={factsOf(snapshot,'analysis','proposal')} title="分析与建议"/></section><details className="record-fields"><summary>模型输入与运行记录</summary><FactList facts={factsOf(snapshot,'context','ai_context','model_request','model_receipt','model_run')} title="模型运行记录"/></details><section className="detail-section"><h3>策略授权与风险</h3><FactList facts={factsOf(snapshot,'authorization','risk','approval')} title="授权记录"/></section><section className="detail-section"><h3>动作与执行结果</h3><FactList facts={factsOf(snapshot,'action','attempt','result')} title="执行记录"/></section><details className="record-fields"><summary>计划与授权上下文</summary><FactList facts={factsOf(snapshot,'decision','plan','authorization_context')} title="计划与授权上下文"/></details></>:null}
   {tab==='verification'?<><div className="decision-callout"><Info/><div><strong>{verification.verdict}</strong><p>{record.validUntil?`验证有效截止：${absoluteTime(record.validUntil)}`:'验证有效期未提供，不能证明当前状态。'}</p></div></div><CheckRows record={record}/><FactList facts={factsOf(snapshot,'verification')} title="验证结论"/><details className="record-fields"><summary>检查方案、断言与观察记录</summary><FactList facts={factsOf(snapshot,'verification_spec','check','observation')} title="检查与观察"/></details><section className="detail-section"><h3>后续处理</h3><FactList facts={factsOf(snapshot,'state_update','state','replan')} title="状态与后续处理"/></section></>:null}
   {tab==='evidence'||tab==='records'?<FactList facts={tab==='evidence'?factsOf(snapshot,'evidence'):factsOf(snapshot,'raw','normalization','event','group','correlation','incident','audit')} title="来源记录"/>:null}
   {!full?<SnapshotNote snapshot={snapshot}/>:null}
  </div>
 </div>;
}
