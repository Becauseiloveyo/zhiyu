import React,{useEffect,useId,useMemo,useRef,useState} from 'react';
import {ArrowLeft,ArrowRight,ChevronRight,Search} from 'lucide-react';
import {queryPath,useRemote,validateGraph,ApiError} from './api';
import {FactCard,ReadState} from './ProductUI';
import {Empty,Time} from './ui';
import {kindLabel,resourceName,relationLabel,basisLabel,displayValue} from './presentation';

export function graphNeighbors(nodes,edges,id){
 const index=new Map(nodes.map(n=>[n.id,n])),linked=new Map();
 for(const edge of edges){if(edge.source!==id&&edge.target!==id)continue;const other=edge.source===id?edge.target:edge.source;if(other===id||!index.has(other))continue;if(!linked.has(other))linked.set(other,{node:index.get(other),edges:[]});linked.get(other).edges.push(edge);}
 const rank={resource:0,analysis:1,action:2,verification:3,event:4,evidence:5,proposal:6};
 return [...linked.values()].sort((a,b)=>(rank[a.node.kind]??20)-(rank[b.node.kind]??20)||a.node.label.localeCompare(b.node.label));
}
function graphTitle(node,facts){
 if(!node)return '安全事件';if(node.kind==='resource')return resourceName(node);
 const peers=facts.filter(f=>f.kind===node.kind),index=peers.findIndex(f=>f.ref===(node.source_ref||node.ref||node.id));
 return kindLabel(node.kind)+(peers.length>1?` ${index>=0?index+1:'（编号未提供）'}`:'');
}
function readSelection(snapshot,initialNode){
 try{const saved=JSON.parse(window.sessionStorage.getItem(`zhiyu:graph:v2:${snapshot.environment_id}:${snapshot.scope_id}:${snapshot.snapshot_id}`)||'null');if(saved&&saved.node===initialNode&&Array.isArray(saved.path)&&saved.path.length<=12&&saved.path.every(id=>typeof id==='string')&&Number.isInteger(saved.page)&&saved.page>=0)return saved;}catch{}
 return{path:initialNode?[initialNode]:[],page:0};
}
export default function EvidenceGraph({snapshot,params,onReload,initialNode=null,onNodeChange=undefined}){
 const [rootRef,setRootRef]=useState(initialNode),[restored]=useState(()=>readSelection(snapshot,initialNode)),[path,setPath]=useState(restored.path),[page,setPage]=useState(restored.page),pendingFocus=useRef(false);
 const [searching,setSearching]=useState(false),[query,setQuery]=useState('');
 const field=useRef(null),focus=useRef(null),paths=useRef(null),title=useRef(null),marker='relation-'+useId().replace(/:/g,'');
 const state=useRemote(queryPath(`snapshots/${encodeURIComponent(snapshot.snapshot_id)}/graph`,{...params,root_ref:rootRef,depth:2}),value=>{validateGraph(value);if(value.snapshot_id!==snapshot.snapshot_id||value.content_sha256!==snapshot.content_sha256)throw new ApiError(0,'graph_snapshot_mismatch');return value;});
 const nodes=state.data?.nodes||[],edges=state.data?.edges||[],selectedId=rootRef||state.data?.root_ref||nodes.find(n=>n.kind==='incident')?.id;
 const selected=nodes.find(n=>n.id===selectedId),neighbors=useMemo(()=>graphNeighbors(state.data?.nodes||[],state.data?.edges||[],selectedId),[state.data,selectedId]);
 const pages=Math.max(1,Math.ceil(neighbors.length/4)),currentPage=Math.min(page,pages-1),shown=neighbors.slice(currentPage*4,currentPage*4+4);
 const lookup=id=>nodes.find(n=>n.id===id)||snapshot.facts.find(f=>f.ref===id),trail=path.length?path:selectedId?[selectedId]:[];
 const matches=query.trim()?snapshot.facts.filter(f=>`${f.id} ${kindLabel(f.kind)}`.toLowerCase().includes(query.trim().toLowerCase())):[];
 useEffect(()=>{try{window.sessionStorage.setItem(`zhiyu:graph:v2:${snapshot.environment_id}:${snapshot.scope_id}:${snapshot.snapshot_id}`,JSON.stringify({node:rootRef,path,page}));}catch{}},[rootRef,path,page,snapshot.snapshot_id,snapshot.environment_id,snapshot.scope_id]);
 useEffect(()=>{if(initialNode!==rootRef){setRootRef(initialNode);setPath(initialNode?[initialNode]:[]);setPage(0);}},[initialNode]);
 useEffect(()=>{
  if(state.status!=='ready'||!field.current)return;
  const draw=()=>{if(!field.current||!focus.current||!paths.current)return;const box=field.current.getBoundingClientRect(),a=focus.current.getBoundingClientRect(),sx=a.right-box.left,sy=a.top+a.height/2-box.top;
   paths.current.querySelectorAll('path').forEach((edge,i)=>{const button=field.current.querySelectorAll('.relation-neighbor')[i];if(!button)return;const b=button.getBoundingClientRect(),x=b.left-box.left,y=b.top+b.height/2-box.top,m=(sx+x)/2;edge.setAttribute('d',`M${sx} ${sy} C${m} ${sy},${m} ${y},${x} ${y}`);});};
  const frame=requestAnimationFrame(draw),observer=new window.ResizeObserver(draw);observer.observe(field.current);
  if(pendingFocus.current){title.current?.focus({preventScroll:true});pendingFocus.current=false;}
  return()=>{cancelAnimationFrame(frame);observer.disconnect();};
 },[state.status,state.data,selectedId,currentPage]);
 const choose=(id,back=false,direct=false)=>{setRootRef(id);setPage(0);setSearching(false);setQuery('');pendingFocus.current=true;setPath(old=>direct?[id]:back?old.slice(0,Math.max(0,old.lastIndexOf(id))+1):[...(old.length?old:selectedId?[selectedId]:[]),id].slice(-12));onNodeChange?.(id);};
 const reset=()=>{setRootRef(null);setPath([]);setPage(0);onNodeChange?.(null);};
 const atIncident=selectedId===snapshot.facts.find(f=>f.kind==='incident'&&f.id===snapshot.incident_id)?.ref;
 const fact=selected&&(snapshot.facts.find(f=>f.ref===selected.source_ref)||{...selected,ref:selected.id,id:selected.label});
 return <ReadState state={state} onRetry={onReload}>{result=>selected?<section className="section relation-explorer" aria-label="证据关联调查">
  <div className="relation-toolbar">{trail.length>1?<nav aria-label="已查看的关联路径">{trail.slice(-4).map((id,i,a)=><React.Fragment key={`${i}-${id}`}>{i?<ChevronRight aria-hidden="true"/>:null}{i===a.length-1?<strong>{graphTitle(lookup(id),snapshot.facts)}</strong>:<button className="text-button" onClick={()=>choose(id,true)}>{graphTitle(lookup(id),snapshot.facts)}</button>}</React.Fragment>)}</nav>:null}<div className="relation-actions"><button className="text-button" aria-expanded={searching} onClick={()=>setSearching(value=>!value)}><Search/>查找记录</button>{!atIncident?<button className="text-button" onClick={reset}>回到事件</button>:null}</div></div>
  {searching?<div className="relation-search"><label className="search-input"><Search/><input name="graph-search" type="search" autoComplete="off" spellCheck={false} aria-label="搜索图谱记录" autoFocus placeholder="搜索记录编号或类型…" value={query} onChange={event=>setQuery(event.target.value)}/></label>{query.trim()?matches.length?<><p className="caption">显示 {Math.min(10,matches.length)} / {matches.length} 条匹配记录</p><ul>{matches.slice(0,10).map(f=><li key={f.ref}><button className="text-button" onClick={()=>choose(f.ref,false,true)}>{graphTitle(f,snapshot.facts)}</button></li>)}</ul></>:<Empty title="没有匹配的记录" description="试试记录编号或类型，例如“证据”。" action="清除搜索" onAction={()=>setQuery('')}/>:<p className="caption">只搜索本快照已读取的记录，每次显示前 10 个匹配项。</p>}</div>:null}
  <div className="relation-reading"><h2 ref={title} tabIndex={-1}>{graphTitle(selected,snapshot.facts)}</h2><div className="relation-record-meta"><span>{basisLabel(selected.basis)}</span>{selected.fields.collector_id?<span>采集器：{selected.fields.collector_id}</span>:null}{selected.fields.observed_at||selected.fields.created_at?<Time at={selected.fields.observed_at||selected.fields.created_at}/>:null}{selected.fields.status?<span>{displayValue(selected.fields.status)}</span>:null}</div><details className="record-fields"><summary>查看来源、时间与原始记录</summary><FactCard fact={fact} compact/></details></div>
  <p className="caption" aria-live="polite">当前记录直接关联 {neighbors.length} 条记录、{neighbors.reduce((sum,x)=>sum+x.edges.length,0)} 条关系。{result.truncated?'已读取关系不完整。':''}</p>
  <div ref={field} className="relation-map" aria-label="当前记录及其直接关联"><svg className="relation-lines" aria-hidden="true"><defs><marker id={marker} markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto-start-reverse"><path d="M0 0 L7 3.5 L0 7 Z"/></marker></defs><g ref={paths}>{shown.map(({node,edges:links})=><path key={node.id} {...(links[0].source===selected.id?{markerEnd:`url(#${marker})`}:{markerStart:`url(#${marker})`})}/>)}</g></svg><div className="relation-focus" ref={focus}><strong>{graphTitle(selected,snapshot.facts)}</strong><span>{basisLabel(selected.basis)}</span></div><div className="relation-neighbors">{shown.map(({node,edges:links})=>{const outgoing=links[0].source===selected.id;return <div key={node.id} className="relation-row"><span className="relation-label">{outgoing?'':'← '}{relationLabel(links[0].relation)}{outgoing?' →':''}{links.length>1?`等 ${links.length} 项`:''}</span><button className="relation-neighbor" onClick={()=>choose(node.id)} aria-label={`查看${graphTitle(node,snapshot.facts)}的关联`}><strong>{graphTitle(node,snapshot.facts)}</strong><span>{node.fields.outcome?displayValue(node.fields.outcome):basisLabel(node.basis)}</span></button></div>;})}</div></div>
  <div className="section-bottom relation-paging"><span>{neighbors.length?`显示 ${currentPage*4+1}–${Math.min(currentPage*4+4,neighbors.length)} / ${neighbors.length} 条`:'没有更多直接关联记录'}</span>{pages>1?<div><button className="button secondary" disabled={currentPage===0} onClick={()=>setPage(value=>value-1)}><ArrowLeft/>上一组</button><button className="button secondary" disabled={currentPage===pages-1} onClick={()=>setPage(value=>value+1)}>下一组<ArrowRight/></button></div>:null}</div>
  <p className="caption">连线表示记录引用，不代表攻击因果。当前载入 {nodes.length} 个节点、{edges.length} 条关系{result.unresolved_count?`，${result.unresolved_count} 条引用未解析`:''}。</p>
 </section>:<Empty title="这条记录没有可显示的图谱" description="返回事件查看已有关系，或重新读取快照。" action="回到事件" onAction={reset}/>}</ReadState>;
}
