import React from 'react';
import {RefreshCw} from 'lucide-react';
import {Status,Tabs,Time} from './ui';
import {SnapshotNote} from './ProductUI';
import {historyLabel,modeLabel} from './presentation';
import {absoluteTime} from './data';
import RecordReference from './RecordReference';

const views=[['summary','概况'],['timeline','时间线'],['graph','证据图谱'],['decision','研判与处置'],['verification','独立验证'],['reports','报告']];
export default function EventWorkspace({record,page,tab,onNavigate,onReload,children}){
 const snapshot=record.snapshot,active=['timeline','graph','reports'].includes(page)?page:['decision','verification'].includes(tab)?tab:'summary';
 const expired=Number.isFinite(Date.parse(snapshot.expires_at))&&Date.parse(snapshot.expires_at)<=Date.now();
 const change=value=>onNavigate(['timeline','graph','reports'].includes(value)?value:'incident',{tab:['summary','decision','verification'].includes(value)?value:null});
 return <section className="event-workspace">
  <header className="event-context"><div className="event-context-title"><h1 tabIndex={-1}>{record.name}</h1><Status status={record.status}/><button className="icon-button" aria-label="重新读取事件快照" onClick={onReload}><RefreshCw/></button></div><div className="event-context-meta"><span>快照读取于 <Time at={snapshot.as_of}/></span><span className={expired?'warn':'subtle'}>{expired?'快照有效期已结束':modeLabel(snapshot.run_mode)}</span><span>{historyLabel(snapshot.history_completeness)}</span><details className="event-data-info"><summary>数据说明</summary><div className="event-data-body"><SnapshotNote snapshot={snapshot}/><dl className="facts"><div><dt>快照时间</dt><dd>{absoluteTime(snapshot.as_of)}</dd></div><div><dt>快照有效截止</dt><dd>{absoluteTime(snapshot.expires_at)}</dd></div><div><dt>已读取记录</dt><dd>{snapshot.facts.length} 条{snapshot.truncated?'，数据已截断':''}</dd></div></dl><RecordReference value={record.id} label="事件编号"/><RecordReference value={snapshot.snapshot_id} label="快照编号"/><RecordReference value={snapshot.content_sha256} label="内容校验值"/><p>快照有效期与独立验证有效期分别计算；历史快照不能代表当前在线状态。</p></div></details></div></header>
  <Tabs id="event-workspace" label="事件页面" items={views} value={active} onChange={change}/>
  <div id="event-workspace-panel" className="event-panel" role="tabpanel" aria-labelledby={`event-workspace-tab-${active}`}>{children}</div>
 </section>;
}
