import React, {useState} from 'react';
import {ArrowUpRight, Activity, Clock, Database, FileText, GitBranch, Inbox, Layers, Search, ShieldCheck, ShieldQuestion, Radio, BrainCircuit, ChevronRight, SlidersHorizontal, TriangleAlert, Check} from 'lucide-react';
import {ResponsiveContainer, LineChart, Line, CartesianGrid, XAxis, YAxis, Tooltip} from 'recharts';
import {useRemote, queryPath, validateSnapshot, ApiError} from './api';
import {incidentView, verificationState, factsOf, statusMap, ordered, absoluteTime} from './data';
import {healthLabel, shortId, displayValue} from './presentation';
import {ReadState} from './ProductUI';
import {Count, Empty, Status, Time} from './ui';

/** @param {{title:string,description?:string,children:React.ReactNode,action?:React.ReactNode,className?:string}} props */
export function SentinelCard({title,description,children,action,className=''}) {
 return <section className={`sn-card ${className}`}><header className="sn-card-head"><div><h2>{title}</h2>{description?<p>{description}</p>:null}</div>{action}</header>{children}</section>;
}

function TrendTooltip({active=false,payload=[]}) {
 if(!active||!payload.length)return null;
 const row=payload[0].payload;
 return <div className="sn-chart-tip"><strong>{row.day.slice(0,10)} · UTC</strong><div><span><i/>创建的安全事件</span><b>{row.count} 条</b></div></div>;
}

function IncidentTrend({state,onReload}) {
 const [visible,setVisible]=useState(true),[table,setTable]=useState(false);
 return <SentinelCard title="安全事件趋势" description="近 7 日（UTC）· 独立于列表筛选" className="sn-trend" action={<button className="sn-button sn-subtle" onClick={()=>setTable(v=>!v)}><FileText/>{table?'查看图表':'查看数据'}</button>}><ReadState state={state} onRetry={onReload}>{data=><>
  <div className="sn-chart-tools"><button className="sn-legend" aria-pressed={visible} onClick={()=>setVisible(v=>!v)}><i className={visible?'':'is-hidden'}/>安全事件</button></div>
  <div className="sn-chart-frame">{!data.daily_incidents.length?<Empty title="近 7 日没有趋势记录" description="可重新读取，确认是否有新增记录。" action="重新读取" onAction={onReload}/>:!visible?<Empty title="趋势序列已隐藏" description="恢复序列后查看实际事件数量。" action="显示序列" onAction={()=>setVisible(true)}/>:table?<div className="sn-chart-data" tabIndex={0} role="region" aria-label="安全事件趋势数据"><table><thead><tr><th>日期（UTC）</th><th>创建事件</th></tr></thead><tbody>{data.daily_incidents.map(row=><tr key={row.day}><td>{row.day.slice(0,10)}</td><td>{row.count}</td></tr>)}</tbody></table></div>:<ResponsiveContainer width="100%" height="100%"><LineChart data={data.daily_incidents} margin={{top:18,right:18,left:0,bottom:4}} accessibilityLayer><CartesianGrid vertical={false} stroke="var(--sn-divider)" strokeDasharray="3 5"/><XAxis dataKey="day" tickFormatter={value=>value.slice(5,10)} axisLine={false} tickLine={false} minTickGap={28} tick={{fill:'var(--sn-secondary)',fontSize:12}}/><YAxis allowDecimals={false} domain={[0,dataMax=>Math.max(1,dataMax)]} tickCount={3} axisLine={false} tickLine={false} width={36} tick={{fill:'var(--sn-secondary)',fontSize:12}}/><Tooltip content={<TrendTooltip/>} cursor={{stroke:'var(--sn-muted)',strokeWidth:1,strokeDasharray:'3 4'}} isAnimationActive={false}/><Line type="linear" dataKey="count" stroke="var(--sn-chart)" strokeWidth={2} dot={{r:3,fill:'var(--sn-surface)',strokeWidth:1.5}} activeDot={{r:5}} isAnimationActive={false}/></LineChart></ResponsiveContainer>}</div><p className="sn-chart-note">{data.daily_incidents.length===1?'仅 1 日有记录；未返回的日期不补零。':'未返回的日期不补零。'}</p>
 </>}</ReadState></SentinelCard>;
}

function Metrics({state,onReload,onNavigate,onAttention}) {
 /** @type {Array<{key:string,title:string,description:string,icon:import('lucide-react').LucideIcon}>} */
 const entries=[{key:'incidents',title:'安全事件',description:'当前时间窗口内创建的事件',icon:Inbox},{key:'needs_attention',title:'需要处理',description:'待研判、审批、复核及重新打开',icon:TriangleAlert},{key:'associated_events',title:'关联记录',description:'当前事件去重后的来源记录',icon:Layers},{key:'VERIFYING',title:'验证中',description:'正在独立验证的安全事件',icon:ShieldCheck}];
 return <ReadState state={state} onRetry={onReload}>{data=><section className="sn-metrics" aria-label="概览指标">{entries.map(({key,title,description,icon:Icon})=>{
  const value=key==='VERIFYING'?(data.status_counts.VERIFYING||0):data.metrics[key],delta=data.metrics.incident_delta_percent;
  return <article className="sn-metric" key={key}><div className="sn-metric-head"><h2>{title}</h2><Icon aria-hidden="true"/></div><p>{description}</p><div className="sn-metric-bottom">{key==='associated_events'?<div className="sn-number"><Count value={value}/></div>:<button className="sn-number" aria-label={key==='needs_attention'?'查看待处理状态分布':`查看${title}`} onClick={()=>key==='needs_attention'?onAttention():onNavigate('incidents',{filter:key==='VERIFYING'?'VERIFYING':null,q:null,priority:null,cursor:null,incident:null,snapshot:null})}><Count value={value}/><ArrowUpRight/></button>}<span className="sn-metric-unit">条</span></div><div className="sn-metric-foot">{key==='incidents'&&Number.isFinite(delta)?<span>较上一窗口{delta===0?'持平':`${delta>0?'增加':'减少'} ${Math.abs(delta)}%`}</span>:key==='VERIFYING'?<span>验证中不等于验证通过</span>:null}</div></article>;
 })}</section>}</ReadState>;
}

function VerificationCard({snapshotState,record,onReload,onView}) {
 const verdict=record?verificationState(record):null;
 return <SentinelCard title="独立验证" description={record?`所选事件 ${shortId(record.id,8,5)}`:"安全、业务与观测"} className="sn-verification" action={<button className="sn-text-button" disabled={!record} onClick={()=>onView('verification')}>查看依据<ArrowUpRight/></button>}>{snapshotState.status==='idle'?<Empty title="选择事件查看验证" description="验证结论仅适用于具体目标与有效期。"/>:<ReadState state={snapshotState} onRetry={onReload}>{snapshot=><>
  <div className={`sn-verdict ${verdict.expired?'expired':verdict.complete?'passed':verdict.rows.some(r=>r.tone==='danger')?'failed':'unknown'}`}><span className="sn-verdict-icon">{verdict.complete?<ShieldCheck/>:verdict.expired?<Clock/>:<ShieldQuestion/>}</span><strong>{verdict.verdict}</strong></div>
  <p className="sn-verification-description">{verdict.expired?'历史结果不能证明当前安全状态。':verdict.complete?'结论受当前目标与有效期约束。':'缺失或不确定的证据不能视为通过。'}</p><dl className="sn-checks">{verdict.rows.map(row=><div key={row.label}><dt>{row.label}</dt><dd className={row.tone} title={row.effective}>{verdict.expired?<Clock/>:row.tone==='ok'?<Check/>:<ShieldQuestion/>}{verdict.expired?'历史 · ':''}{displayValue(row.value)}</dd></div>)}</dl>
  <div className="sn-verification-time"><Clock/><div><span>验证有效截止</span><strong>{record.validUntil?absoluteTime(record.validUntil):'尚未提供'}</strong></div></div><p className="sn-source-time">快照读取于 <Time at={snapshot.as_of} focusable={false}/></p>
 </>}</ReadState>}</SentinelCard>;
}

function SystemCard({state,onReload,onContext}) {
 return <SentinelCard title="系统状态" className="sn-system" action={<button className="sn-icon-button" aria-label="查看完整环境状态" onClick={onContext}><ArrowUpRight/></button>}><ReadState state={state} onRetry={onReload}>{data=><>
  <div className="sn-system-list">{data.sensors.map(sensor=><div className="sn-system-row" key={sensor.sensor_id}><span className="sn-icon-tile"><Radio/></span><div><strong title={sensor.sensor_id}>{sensor.sensor_id.replace(/^sensor-/, '')}</strong><small>心跳 <Time at={sensor.last_heartbeat_at} focusable={false}/></small></div><span className={`sn-service-state ${sensor.effective_status==='HEALTHY'?'ok':sensor.effective_status==='UNKNOWN'?'neutral':'warn'}`}><i/>{healthLabel(sensor.effective_status)}</span></div>)}{!data.sensors.length?<p className="sn-no-sensor"><Radio/>当前范围未读取到采集器心跳</p>:null}
  {[[Database,'数据库',data.database,'仅表示数据可达'],[BrainCircuit,'模型服务',data.model_runtime_status||'UNKNOWN',`影响模式：${healthLabel(data.ai_mode)}`],[Activity,'后台进程',data.worker_status||'UNKNOWN','']].map(([Icon,label,status,note])=>{const Symbol=/** @type {import('lucide-react').LucideIcon} */(Icon);return <div className="sn-system-row" key={String(label)}><span className="sn-icon-tile"><Symbol/></span><div><strong>{String(label)}</strong>{note?<small>{String(note)}</small>:null}</div><span className={`sn-service-state ${['AVAILABLE','HEALTHY'].includes(String(status))?'ok':status==='UNKNOWN'?'neutral':'warn'}`}><i/>{healthLabel(status)}</span></div>})}</div>
  <div className="sn-card-foot"><span>更新于 <Time at={data.as_of} focusable={false}/></span></div>
 </>}</ReadState></SentinelCard>;
}

/** The index counts real snapshot facts. Its stage order is not an inferred edge. */
export function stageIndex(snapshot) {
 return [{name:'检测记录',kinds:['event'],icon:Radio,tab:'evidence'},{name:'安全事件',kinds:['incident'],icon:Inbox,tab:'summary'},{name:'AI 研判',kinds:['analysis','proposal'],icon:BrainCircuit,tab:'decision'},{name:'处置计划',kinds:['plan'],icon:FileText,tab:'decision'},{name:'授权决定',kinds:['authorization'],icon:ShieldCheck,tab:'decision'},{name:'动作与回执',kinds:['action','result'],icon:Activity,tab:'decision'},{name:'独立验证',kinds:['verification'],icon:ShieldCheck,tab:'verification'},{name:'状态更新',kinds:['state_update'],icon:GitBranch,tab:'verification'}].map(stage=>({...stage,count:factsOf(snapshot,...stage.kinds).length}));
}

function DecisionRecords({snapshotState,record,onReload,onView,onGraph}) {
 return <SentinelCard title="处置记录关联" description="同一事件快照 · 按业务阶段索引" className="sn-decision" action={<button className="sn-text-button" disabled={!record} onClick={onGraph}>证据图谱<ArrowUpRight/></button>}>{snapshotState.status==='idle'?<Empty title="选择事件查看处置记录" description="沿来源、计划、动作与验证逐项核对。"/>:<ReadState state={snapshotState} onRetry={onReload}>{snapshot=><><div className="sn-decision-context"><span>{record.name}</span><span title={record.id}>{shortId(record.id)}</span></div><div className="sn-stages">{stageIndex(snapshot).map(({name,count,icon:Icon,tab},i)=><React.Fragment key={name}><button className={`sn-stage ${count?'has-record':'no-record'} ${name==='独立验证'&&verificationState(record).expired?'expired':''}`} disabled={!count} aria-label={`${name} ${count?`${count} 条记录`:'未读取到记录'}`} onClick={()=>onView(tab)}><span className="sn-stage-icon"><Icon/></span><strong>{name}</strong><small>{count?`${count} 条记录`:'未读取到记录'}</small></button>{i<7?<span className="sn-stage-link" aria-hidden="true"/>:null}</React.Fragment>)}</div><div className="sn-decision-note"><ShieldCheck/><span>记录数量不代表执行成功；明确引用关系见证据图谱。AI 提案不构成授权。</span></div></>}</ReadState>}</SentinelCard>;
}

export default function SentinelOverview({items,overview,health,listState,onOpen,onNavigate,onReload,contextOpen,onToggleContext,params,query,filter,priority,onSearch,onFilter,onFirst,onNext,hasCursor,onHealth,revision=0}) {
 const [focus,setFocus]=useState(null),[sort,setSort]=useState(false),[attention,setAttention]=useState(false);
 const focusId=items.find(row=>row.id===focus)?.id||items[0]?.id;
 const snapshotState=useRemote(focusId?queryPath(`incidents/${encodeURIComponent(focusId)}/snapshot`,params):null,value=>{validateSnapshot(value);if(value.incident_id!==focusId||!value.facts.some(fact=>fact.kind==='incident'&&fact.id===focusId))throw new ApiError(0,'snapshot_incident_mismatch');return value;},revision);
 const root=snapshotState.data?.facts.find(fact=>fact.kind==='incident'),record=root?incidentView({incident_id:root.id,...root.fields},snapshotState.data):null;
 const inspect=tab=>record&&onNavigate('incident',{incident:record.id,snapshot:record.snapshot.snapshot_id,tab});
 const attentionStates=['NEW','WAITING_APPROVAL','HUMAN_REVIEW','REOPENED'];
 const rows=sort?ordered(items):items;
 return <div className="sentinel-overview"><Metrics state={overview} onReload={onReload} onNavigate={onNavigate} onAttention={()=>{setAttention(v=>!v);document.getElementById('sn-event-heading')?.focus();document.getElementById('sn-event-heading')?.scrollIntoView({block:'center'})}}/>
  <div className={`sn-grid ${contextOpen?'':'sn-context-hidden'}`}><IncidentTrend state={overview} onReload={onReload}/>{contextOpen?<VerificationCard snapshotState={snapshotState} record={record} onReload={onReload} onView={inspect}/>:null}
  <SentinelCard title="最近事件" description="点选事件查看验证与处置记录" className="sn-recent" action={<button className="sn-text-button" onClick={()=>onNavigate('incidents')}>全部事件<ArrowUpRight/></button>}>
   <h3 className="sr-only" id="sn-event-heading" tabIndex={-1}>事件筛选与列表</h3>
   <div className="sn-table-tools"><label className="sn-search"><Search/><input name="overview-search" type="search" aria-label="搜索概览事件" placeholder="搜索事件 ID、名称…" autoComplete="off" spellCheck={false} value={query} onChange={e=>onSearch(e.target.value)}/></label><select aria-label="概览事件状态" value={filter} onChange={e=>onFilter({filter:e.target.value})}><option value="all">全部状态</option>{Object.entries(statusMap).map(([key,value])=><option key={key} value={key}>{value.label}</option>)}</select><select aria-label="概览事件优先级" value={priority} onChange={e=>onFilter({priority:e.target.value})}><option value="all">全部优先级</option>{['P0','P1','P2','P3','P4'].map(value=><option key={value}>{value}</option>)}</select><button className="sn-icon-button" aria-label={contextOpen?'收起验证与系统面板':'展开验证与系统面板'} onClick={onToggleContext}><SlidersHorizontal/></button></div>
   {attention?<div className="sn-attention" aria-label="待处理状态分布"><span>选择一个待处理状态</span>{attentionStates.map(key=><button className="sn-chip" key={key} onClick={()=>onFilter({filter:key})}>{statusMap[key].label}<b>{overview.data?.status_counts[key]??'—'}</b></button>)}</div>:null}
   <ReadState state={listState} onRetry={onReload}>{()=>rows.length?<div className="sn-table-scroll" tabIndex={0} role="region" aria-label="最近事件表格，可横向滚动"><table className="sn-table"><thead><tr><th aria-sort={sort?'ascending':'none'}><button onClick={()=>setSort(v=>!v)}>优先级<span className="sr-only">（仅排序本页）</span><ChevronRight className={sort?'sn-sort-active':'sn-sort'}/></button></th><th>事件 / 受影响资源</th><th>当前状态</th><th>更新于</th><th><span className="sr-only">打开详情</span></th></tr></thead><tbody>{rows.map(row=><tr key={row.id} className={focusId===row.id?'is-selected':''}><td><span className={`sn-severity ${row.priority.toLowerCase()}`}><i/>{row.priority}</span></td><td><button className="sn-event-title" aria-pressed={focusId===row.id} onClick={()=>setFocus(row.id)}>{row.name}</button><small title={`${row.id} · ${row.asset}`}>{shortId(row.id,10,5)} · {row.asset}</small></td><td><Status status={row.status}/></td><td><Time at={row.at}/></td><td><button className="sn-icon-button" aria-label={`打开事件 ${row.id}`} onClick={()=>onOpen(row)}><ArrowUpRight/></button></td></tr>)}</tbody></table></div>:<Empty title="当前条件下没有事件" description="调整时间窗口，或重置状态、优先级与搜索条件。" action="重置筛选" onAction={()=>onFilter({filter:null,priority:null,q:null})}/>}</ReadState>
   <div className="sn-table-pagination"><span>本页 {items.length} 条{sort?' · 本页按优先级排序':''}{listState.data?.next_cursor?' · 还有更多记录':''}</span>{hasCursor||listState.data?.next_cursor?<div><button className="sn-text-button" disabled={!hasCursor} onClick={onFirst}>返回首页</button><button className="sn-button" disabled={!listState.data?.next_cursor} onClick={onNext}>下一页<ChevronRight/></button></div>:null}</div>
  </SentinelCard>{contextOpen?<SystemCard state={health} onReload={onReload} onContext={onHealth}/>:null}<DecisionRecords snapshotState={snapshotState} record={record} onReload={onReload} onView={inspect} onGraph={()=>record&&onNavigate('graph',{incident:record.id,snapshot:record.snapshot.snapshot_id})}/></div>
 </div>;
}
