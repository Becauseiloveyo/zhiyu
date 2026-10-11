import React,{useEffect,useRef,useState} from 'react';
import {Play,Archive} from 'lucide-react';
import {api,queryPath,useRemote,validateEnvelope,validateSnapshot,errorMessage} from './api';
import {ReadState} from './ProductUI';
import {Empty} from './ui';
export default function Recordings({params,onOpen,onReload}){
 const [busy,setBusy]=useState(null),[error,setError]=useState(null),[revision,setRevision]=useState(0),pending=useRef(null);
 const retry=()=>setRevision(value=>value+1);
 useEffect(()=>()=>pending.current?.abort(),[]);
 const state=useRemote(queryPath('recordings',params),value=>{validateEnvelope(value);if(!Array.isArray(value.items))throw Error('malformed recordings');return value;},revision);
 const open=async item=>{setBusy(item.recording_id);setError(null);const controller=new AbortController();pending.current=controller;try{const snapshot=validateSnapshot(await api(queryPath(`recordings/${encodeURIComponent(item.recording_id)}/snapshot`,params),{signal:controller.signal}));if(snapshot.run_mode!=='RECORDED_REPLAY'||snapshot.recording_id!==item.recording_id)throw Error('replay mode mismatch');if(!controller.signal.aborted)onOpen(snapshot);}catch(reason){if(!controller.signal.aborted)setError(reason);}finally{if(!controller.signal.aborted)setBusy(null);}};
 return <section className="section"><div className="section-heading"><h2><Archive/>封存记录回放</h2><span className="subtle">RECORDED REPLAY · 只读</span></div><p className="health-note">保留原始观测时间与结果，不调用模型，不创建事件、Action 或验证结果。失败的现场运行不会被替换。</p>{error?<p role="alert" className="health-note warn">{errorMessage(error)}</p>:null}<ReadState state={state} onRetry={retry}>{data=><>{data.items.length?<div className="demo-cards">{data.items.map(item=><article key={item.recording_id}><span className="eyebrow">RECORDED REPLAY</span><h3>{item.title}</h3><p>{item.model_source}</p><p className="mono">{item.source_run_id}</p><button className="button secondary" disabled={!!busy} onClick={()=>open(item)}><Play/>{busy===item.recording_id?'校验封存快照…':'打开历史回放'}</button></article>)}</div>:<Empty title="当前范围尚无封存记录" description="仅展示管理员登记且哈希校验通过的产品快照。" action="重新读取" onAction={retry}/>}</>}</ReadState></section>;
}
