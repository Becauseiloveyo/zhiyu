import React from 'react';
import {Radio,ShieldCheck,Info,Activity,Database,Clock,ScanLine,ChevronRight} from 'lucide-react';
import ActivityChart,{Spark} from './Charts';
import {ordered,isTodo} from './data';
import {Count,Status,Time,Empty,LinkButton,useMedia} from './ui';
import {ReadState} from './ProductUI';
import RecordReference from './RecordReference';
import {healthLabel} from './presentation';

export function Health({state,onReload}){
 return <section className="section health-section" id="health">
  <div className="section-heading"><div><h2>环境健康</h2><p>实际心跳与覆盖记录</p></div><Activity/></div>
  <ReadState state={state} onRetry={onReload}>{health=><>
   <dl className="health-rows">
    {health.sensors.map(sensor=><div className="sensor-row" key={sensor.sensor_id}>
     <dt><Radio/><div className="sensor-identity"><strong>{sensor.sensor_id}</strong><small className="health-source">心跳 <Time at={sensor.last_heartbeat_at}/></small><RecordReference value={sensor.config_version} label="配置版本"/></div></dt>
     <dd title={sensor.effective_status}><i className={`status-dot ${sensor.effective_status==='HEALTHY'?'ok breathing':'warn'}`}/>{healthLabel(sensor.effective_status)}</dd>
    </div>)}
    {[['数据库',health.database],['模型影响模式',health.ai_mode],['模型服务',health.model_runtime_status||'UNKNOWN'],['后台进程',health.worker_status||'UNKNOWN'],['采集覆盖',health.runtime_status]].map(([label,value])=><div key={label}><dt>{label}</dt><dd title={value}>{healthLabel(value)}</dd></div>)}
   </dl>
   {!health.sensors.length?<p className="caption">未读取到当前范围的采集器心跳，状态未知。</p>:null}
   <div className="section-bottom"><span>读取时间</span><Time at={health.as_of}/></div>
  </>}</ReadState>
  <p className="health-note"><Info/>环境状态不等于事件通过安全验证；超过两分钟的心跳视为过期。</p>
 </section>;
}

export function EventTable({items,selected=null,onSelect,compact=false}){
 return <div className="table-scroll" tabIndex={0} aria-label="事件表格，可横向滚动"><table className={compact?'compact-table':''}>
  <thead><tr><th>优先级</th><th>安全事件</th>{!compact?<th>资源</th>:null}<th>当前状态</th><th>最近更新</th></tr></thead>
  <tbody>{items.map(r=><tr key={r.id} className={selected===r.id?'selected':''} onClick={()=>onSelect(r)}>
   <td><span className={`priority ${r.priority.toLowerCase()}`}>{r.priority}</span></td>
   <td><div className="event-cell"><button className="event-button" aria-label={`查看 ${r.id} ${r.name}`} aria-pressed={selected===r.id} onClick={event=>{event.stopPropagation();onSelect(r);}}><span>{r.name}</span></button><RecordReference value={r.id} label="事件 ID"/></div></td>
   {!compact?<td className="subtle">{r.asset}</td>:null}<td><Status status={r.status}/></td><td><Time at={r.at}/></td>
  </tr>)}</tbody>
 </table></div>;
}

export default function Overview({items,overview,health,listState,onOpen,onNavigate,onReload,contextOpen,onToggleContext}){
 const narrow=useMedia('(max-width: 1279px)'),queue=ordered(items.filter(isTodo)).slice(0,5),data=overview.data;
 /** @type {Array<[string,string|null,import('lucide-react').LucideIcon,string]>} */
 const metrics=[['关联事件记录','associated_events',Database,'当前事件的去重关联记录'],['安全事件','incidents',ScanLine,'当前创建窗口'],['需要处理','needs_attention',Clock,'待研判、审批、复核、重开'],['验证中',null,ShieldCheck,'事件处于验证中']];
 const focusQueue=()=>{const section=document.getElementById('attention-queue');section?.scrollIntoView({block:'start',behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'});section?.querySelector('h2')?.focus({preventScroll:true});};
 return <>
  <ReadState state={overview} onRetry={onReload}>{summary=><section className="kpi-strip enter" aria-label="概览指标">
   {metrics.map(([label,key,Icon,context])=>{
    const number=<><Count value={key?summary.metrics[key]:summary.status_counts.VERIFYING||0}/>{key==='incidents'&&summary.daily_incidents.length>1?<Spark values={summary.daily_incidents.map(item=>item.count)}/>:null}</>;
    return <div className="kpi" key={label}>
     <div className="kpi-top"><span>{label}</span><Icon/></div>
     {key==='associated_events'?<div className="kpi-value">{number}</div>:<button className="kpi-link" onClick={()=>key==='needs_attention'?focusQueue():onNavigate('incidents',{filter:key===null?'VERIFYING':null,q:null,priority:null,cursor:null,incident:null,snapshot:null})} aria-label={key==='needs_attention'?'查看当前页待处理队列':`查看${label}`}>{number}</button>}
     <div className="kpi-meta"><span title={summary.formulas[key]||'COUNT(status=VERIFYING)'}>{context}</span>{key==='incidents'&&summary.metrics.incident_delta_percent!==null?<span className="kpi-delta">{summary.metrics.incident_delta_percent===0?'较上一窗口持平':`较上一窗口${summary.metrics.incident_delta_percent>0?'上升':'下降'} ${Math.abs(summary.metrics.incident_delta_percent)}%`}</span>:null}</div>
    </div>;
   })}
  </section>}</ReadState>
  <div className={`overview-grid ${contextOpen?'context-open':''}`}>
   <div className="overview-main">
    <section className="section attention-section enter" id="attention-queue">
     <div className="section-heading"><div><div className="heading-line"><h2 tabIndex={-1}>需要你关注</h2><span className="count-badge">{data?.metrics.needs_attention??'—'}</span></div><p>当前页待处理记录 · 按优先级与更新时间排序</p></div><button className="text-button" onClick={onToggleContext}>{narrow?'环境摘要':contextOpen?'收起环境摘要':'环境摘要'}<ChevronRight/></button></div>
     <div className="queue-summary"><span><i className="status-dot warn"/>{data?(data.status_counts.NEW||0):'—'} 待研判</span><span>{data?(data.status_counts.HUMAN_REVIEW||0):'—'} 待复核</span><span>{data?(data.status_counts.WAITING_APPROVAL||0):'—'} 等待审批</span></div>
     <ReadState state={listState} onRetry={onReload}>{()=>queue.length?<EventTable items={queue} compact onSelect={onOpen}/>:<Empty title="当前页没有待处理事件" description="其他状态的事件仍可在列表中查看；本队列仅覆盖当前页。" action="查看全部事件" onAction={()=>onNavigate('incidents',{filter:null,q:null,priority:null,cursor:null})}/>}</ReadState>
     <div className="section-bottom"><span>最多展示当前页 5 条记录</span><LinkButton onClick={()=>onNavigate('incidents',{filter:null,q:null,priority:null,cursor:null})}>查看全部事件</LinkButton></div>
    </section>
    <div className="enter"><ActivityChart data={data?.daily_incidents||[]} loading={overview.status==='loading'}/></div>
   </div>
   <aside className="overview-context" aria-label="环境与验证背景">
    <Health state={health} onReload={onReload}/>
    <section className="section assurance-section enter"><div className="section-heading"><div><h2>独立验证</h2><p>安全、业务与观测三维检查</p></div><ShieldCheck/></div><dl className="coverage-rows"><div><dt>正在验证</dt><dd>{data?(data.status_counts.VERIFYING||0):'—'}</dd></div></dl><p className="health-note"><Info/>逐事件查看验证结论与有效期。综合分数未定义、验证通过率未计算，不推算展示。</p></section>
    <div className="scope-note"><ShieldCheck/><div><strong>受控范围内读取</strong><p>{data?.scope_id||data?.environment_id||'等待授权上下文'}<br/>结论仅适用于指定目标与时间窗。</p></div></div>
   </aside>
  </div>
 </>;
}
