import React,{useEffect,useState} from 'react';
import {ArrowRight,ChevronDown} from 'lucide-react';
import {Empty,Time} from './ui';
import {FactCard,ReadState} from './ProductUI';
import {kindLabel,basisLabel,displayValue,timeLabel} from './presentation';
import {queryPath,useRemote,validateTimeline} from './api';
export {default as GraphPage} from './EvidenceGraph';

export function TimelinePage({snapshot,params,onReload,initialPicked=null,initialCursor=null,onSelectionChange=undefined}){
 const [cursor,setCursor]=useState(initialCursor),[picked,setPicked]=useState(initialPicked);
 useEffect(()=>{setCursor(initialCursor);setPicked(initialPicked);},[initialCursor,initialPicked]);
 const state=useRemote(queryPath(`snapshots/${encodeURIComponent(snapshot.snapshot_id)}/timeline`,{...params,limit:50,cursor}),validateTimeline);
 const choose=ref=>{const next=picked===ref?null:ref;setPicked(next);onSelectionChange?.({time_ref:next});};
 const next=cursor=>{setCursor(cursor);setPicked(null);onSelectionChange?.({time_cursor:cursor,time_ref:null});};
 return <ReadState state={state} onRetry={onReload}>{result=><section className="section investigation-timeline"><div className="section-heading"><div><h2>事件时间线</h2><p>按来源时间排列；相邻记录不代表攻击因果。</p></div><span className="caption">本页 {result.items.length} 个时间点{result.truncated?' · 数据已截断':''}</span></div>
  {result.items.length?<ol className="investigation-time-list">{result.items.map(entry=>{const fact=snapshot.facts.find(f=>f.ref===entry.source_ref);return <li key={entry.id}><button className="investigation-time-row" aria-pressed={picked===entry.id} aria-expanded={picked===entry.id} onClick={()=>choose(entry.id)}><Time at={entry.at} focusable={false}/><span><strong>{kindLabel(entry.kind)}</strong><small>{timeLabel(entry.time_semantics)} · {basisLabel(entry.basis)}</small></span><span>{displayValue(entry.status)||'未记录结果'}</span><ChevronDown aria-hidden="true"/></button>{picked===entry.id?<div className="time-inline-detail">{fact?<FactCard fact={fact} compact/>:<p className="caption">这份快照没有读取到该时间点的来源记录；不会补齐缺失字段。</p>}</div>:null}</li>;})}</ol>:<Empty title="没有可用时间记录" description="缺失的时间不会由前端补齐。" action="重新读取" onAction={onReload}/>}
  <div className="section-bottom"><button className="text-button" disabled={!cursor} onClick={()=>next(null)}>返回首页</button><span className="caption">每页最多 50 个真实时间点</span><button className="text-button" disabled={!result.next_cursor} onClick={()=>next(result.next_cursor)}>下一页<ArrowRight/></button></div>
 </section>}</ReadState>;
}
