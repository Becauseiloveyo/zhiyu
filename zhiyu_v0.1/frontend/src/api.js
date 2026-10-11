import {useEffect, useRef, useState} from 'react';

export class ApiError extends Error {
 constructor(status, code){super(code);this.status=status;this.code=code;}
}
const messages={401:'会话已过期，请重新登录。',403:'当前身份无权读取这个环境或范围。',404:'记录不存在，或不在当前授权范围内。',409:'运行状态已变化，或仍有未清理资源。请刷新记录后重试。',410:'这份快照已过期，请明确刷新后重新查看。',413:'数据超过展示预算，请缩小时间窗口。',422:'查询条件无效，请重置筛选。',429:'读取较繁忙，请稍后重试。',500:'服务暂时无法完成请求。',503:'数据服务不可用，无法确认当前状态。'};
export const errorMessage=error=>messages[error?.status]||(error?.code==='timeout'?'请求超时，请检查服务后重试。':'无法读取有效数据，请重试。');
let csrf='';let active=0;const waiting=[];
async function acquire(){if(active<2){active++;return;}await new Promise(resolve=>waiting.push(resolve));}
function release(){const next=waiting.shift();if(next)next();else active--;}
export function setCsrf(value){csrf=value||'';}
/** @param {string} path @param {{method?:string, body?:unknown, signal?:AbortSignal}} options */
export async function api(path,{method='GET',body,signal}={}){
 if(!path.startsWith('/v1/product/'))throw new ApiError(0,'invalid_endpoint');
 await acquire();const controller=new AbortController();let timeout=false;
 const cancel=()=>controller.abort();signal?.addEventListener('abort',cancel,{once:true});
 if(signal?.aborted)controller.abort();
 const timer=setTimeout(()=>{timeout=true;controller.abort();},8000);
 try{
  const response=await fetch(path,{method,credentials:'same-origin',signal:controller.signal,headers:{Accept:'application/json',...(body?{'Content-Type':'application/json'}:{}),...(method!=='GET'?{'X-Zhiyu-CSRF':csrf}:{})},body:body?JSON.stringify(body):undefined});
  if(!response.ok){if(response.status===401&&!path.startsWith('/v1/product/session')){setCsrf('');dispatchEvent(new Event('zhiyu:session-expired'));}throw new ApiError(response.status,'request_failed');}
  if(!response.headers.get('content-type')?.includes('application/json'))throw new ApiError(0,'malformed_response');
  let data;try{data=await response.json();}catch{throw new ApiError(0,'malformed_response');}
  if(!data||typeof data!=='object'||Array.isArray(data))throw new ApiError(0,'malformed_response');
  if(data.csrf)setCsrf(data.csrf);return data;
 }catch(error){if(timeout)throw new ApiError(0,'timeout');throw error;}
 finally{clearTimeout(timer);signal?.removeEventListener('abort',cancel);release();}
}
export function queryPath(endpoint,params){const values=new URLSearchParams();Object.entries(params).forEach(([key,value])=>{if(value!==null&&value!==undefined&&value!=='')values.set(key,String(value));});return `/v1/product/${endpoint}?${values}`;}
export function validateEnvelope(data){
 if(!data||data.projection_version!=='0.9.0'||typeof data.environment_id!=='string'||!Number.isFinite(Date.parse(data.as_of))||!['LIVE','RECORDED_REPLAY'].includes(data.run_mode))throw new ApiError(0,'malformed_response');return data;
}
export function validatePage(data){validateEnvelope(data);if(!Array.isArray(data.items)||data.items.some(row=>!row||typeof row.incident_id!=='string'||typeof row.title!=='string'||typeof row.status!=='string'||typeof row.priority!=='string'||!Number.isFinite(Date.parse(row.updated_at))))throw new ApiError(0,'malformed_response');return data;}
export function validateSnapshot(data){validateEnvelope(data);if(typeof data.snapshot_id!=='string'||!/^[a-f0-9]{64}$/.test(data.content_sha256)||!Array.isArray(data.facts)||data.facts.some(f=>!f||typeof f.ref!=='string'||typeof f.kind!=='string'||typeof f.id!=='string'||!f.fields||typeof f.fields!=='object'||Array.isArray(f.fields)))throw new ApiError(0,'malformed_response');return data;}
export function validateOverview(data){validateEnvelope(data);if(!data.metrics||!data.status_counts||!data.formulas||!Array.isArray(data.daily_incidents)||['incidents','associated_events','needs_attention'].some(key=>!Number.isFinite(data.metrics[key]))||Object.values(data.status_counts).some(value=>!Number.isFinite(value))||data.daily_incidents.some(row=>!Number.isFinite(row.count)||!Number.isFinite(Date.parse(row.day))))throw new ApiError(0,'malformed_response');return data;}
export function validateHealth(data){validateEnvelope(data);if(!Array.isArray(data.sensors)||!Array.isArray(data.capabilities)||typeof data.runtime_status!=='string'||data.sensors.some(row=>!row||typeof row.sensor_id!=='string'||typeof row.effective_status!=='string'))throw new ApiError(0,'malformed_response');return data;}
export function validateTimeline(data){validateEnvelope(data);if(!Array.isArray(data.items)||data.items.some(row=>!row||typeof row.source_ref!=='string'||typeof row.kind!=='string'||!Number.isFinite(Date.parse(row.at))))throw new ApiError(0,'malformed_response');return data;}
export function validateGraph(data){validateEnvelope(data);if(!Array.isArray(data.nodes)||!Array.isArray(data.edges)||data.nodes.length>200||data.edges.length>400||data.nodes.some(row=>!row||typeof row.id!=='string'||typeof row.label!=='string'||!row.fields)||data.edges.some(row=>!row||typeof row.source!=='string'||typeof row.target!=='string'||row.causal!==false))throw new ApiError(0,'malformed_response');return data;}
export function useRemote(path,validate=value=>value,revision=0){
 const validator=useRef(validate);validator.current=validate;
 const [state,setState]=useState({key:null,status:'loading',data:null,error:null});
 useEffect(()=>{if(!path)return;const controller=new AbortController();setState({key:path,status:'loading',data:null,error:null});api(path,{signal:controller.signal}).then(data=>validator.current(data)).then(data=>{if(!controller.signal.aborted)setState({key:path,status:'ready',data,error:null});}).catch(error=>{if(!controller.signal.aborted)setState({key:path,status:'error',data:null,error});});return()=>controller.abort();},[path,revision]);
 return state.key===path?state:{key:path,status:path?'loading':'idle',data:null,error:null};
}
