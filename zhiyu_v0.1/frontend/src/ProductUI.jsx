import React,{useState} from 'react';
import {Info,LogIn,ShieldCheck,ChevronDown} from 'lucide-react';
import BrandMark from './BrandMark';
import {api,errorMessage} from './api';
import {absoluteTime} from './data';
import {Empty,Loading} from './ui';
import RecordReference from './RecordReference';
import {kindLabel,displayValue,basisLabel,modeLabel,historyLabel,modelText,eventTitle} from './presentation';

export function ReadState({state,onRetry,children}){
 if(state.status==='loading')return <Loading rows={6}/>;
 if(state.status==='error')return <Empty error title="无法读取当前数据" description={errorMessage(state.error)} action="重新读取" onAction={onRetry}/>;
 if(state.status!=='ready')return <Empty title="选择工作范围" description="先选择获准的环境和读取范围，再查看记录。"/>;
 return children(state.data);
}
export function Login({onLogin,connectionError}){
 const [busy,setBusy]=useState(false),[error,setError]=useState(null);
 const submit=async event=>{event.preventDefault();if(busy)return;setBusy(true);setError(null);const form=event.currentTarget,values=new FormData(form);try{await api('/v1/product/session',{method:'POST',body:{username:values.get('username'),access_key:values.get('access_key')}});form.reset();onLogin();}catch(reason){setError(reason);}finally{setBusy(false);}};
 return <main className="login-screen"><section className="section login-card"><div className="brand"><BrandMark/><span><strong>智御</strong><small>安全决策与持续验证</small></span></div><h1>进入工作空间</h1><p className="body-copy">使用为当前受控实验室配置的工作台身份。</p><form onSubmit={submit}><label className="field-label">用户名<input name="username" autoComplete="username" required maxLength={64}/></label><label className="field-label">工作台访问密钥<input name="access_key" type="password" autoComplete="current-password" required minLength={32} maxLength={128}/></label>{error||connectionError?<p role="alert" className="warn">{errorMessage(error||connectionError)}</p>:null}<button className="button primary" type="submit" disabled={busy}><LogIn/>{busy?'正在验证身份…':'登录工作台'}</button>{busy?<Loading rows={1}/>:null}</form><p className="caption"><ShieldCheck/>访问权限由服务端配置；密钥不会保存在浏览器本地存储。</p></section></main>;
}
const labels={clock_status:'时钟状态',scope_version:'授权范围版本',execution_status:'检查执行',schema_valid:'结构校验通过',safety_status:'安全校验',sensor_health_status:'采集器健康',autonomy_mode:'自主决策模式',load_mode:'负载模式',requested_risk:'请求风险等级',approval_id:'审批记录',expires_at:'到期时间',claim:'验证声明',recommended_next_step:'原记录建议',status:'状态',claim_kind:'声明类型',data_origin:'数据来源',provenance_group:'来源组',trust_status:'来源信任',valid_until:'有效至',observed_at:'观测时间',collected_at:'采集时间',created_at:'创建时间',started_at:'开始时间',finished_at:'结束时间',source_timestamp:'来源时间',ingested_at:'入库时间',security_status:'安全目标',business_status:'业务健康',observation_status:'观测有效性',outcome:'决定',assessed_risk:'风险等级',human_approval_required:'需要人工审批',policy_version:'策略版本',integrity_hash:'完整性哈希',evidence_ids:'证据引用',source_event_ids:'来源事件',confidence_semantics:'置信度语义',semantic_correctness:'语义正确性',incident_summary:'模型摘要',reasoning_summary:'模型理由',hypotheses:'模型假设',uncertainty:'不确定性',scope_id:'授权范围',execution_outcome:'执行结果',replan_count:'重规划次数',reason:'原因',reasons:'原因',assertions:'断言',assertion_status:'断言结果',mode:'提案模式'};
const textValue=value=>value===null||value===undefined?'未记录':typeof value==='object'?JSON.stringify(value,null,2):String(value);
const criticalField=key=>/(^|_)(status|valid|expires|outcome|risk|approval|scope|policy|mode|semantics?|confidence|trust|claim|assertions?|uncertainty|reasons?)(_|$)/.test(key);
export function FieldValue({field,value}){
 if(typeof value==='string'&&(/_at$|_until$/.test(field)||['source_timestamp','timestamp'].includes(field))&&Number.isFinite(Date.parse(value)))return <time dateTime={value} title={value}>{absoluteTime(value)}</time>;
 if(value&&typeof value==='object')return <details className="structured-value"><summary>查看结构化内容{Array.isArray(value)?`（${value.length} 项）`:''}</summary><pre className="field-json">{textValue(value)}</pre></details>;
 if(value===null||value===undefined)return '未记录';
 if(field==='incident_summary'||field==='title')return eventTitle(value);
 if(['uncertainty','reasoning_summary','claim','recommended_next_step'].includes(field)&&typeof value==='string'&&/[a-z]{3}/i.test(value)){const translated=modelText(value);return translated!==value?<>{translated}<details className="structured-value"><summary>查看原文</summary><p>{value}</p></details></>:<details className="structured-value"><summary>查看记录原文</summary><p>{value}</p></details>;}
 const translated=displayValue(value);
 return translated===value&&typeof value==='string'&&/^[A-Z][A-Z_]{3,}$/.test(value)?'未识别值，请核对原始记录':String(translated);
}
export function FactCard({fact,compact=false}){
 const fields=Object.entries(fact.fields);
 let count=0;
 const primary=fields.filter(([key,value])=>criticalField(key)||((labels[key]||key==='title')&&typeof value!=='object'&&(!compact||count++<6)));
 const primaryKeys=new Set(primary.map(([key])=>key)),remaining=fields.filter(([key])=>!primaryKeys.has(key));
 const rows=entries=><dl className="facts">{entries.map(([key,value])=><div key={key}><dt title={key}>{labels[key]||(key==='title'?'名称':key)}</dt><dd><FieldValue field={key} value={value}/></dd></div>)}</dl>;
 return <article className="evidence-card fact-card"><header><strong title={fact.kind}>{kindLabel(fact.kind)}</strong><span className={`small-badge ${fact.freshness==='EXPIRED'?'warn':''}`}>{basisLabel(fact.basis)} · {displayValue(fact.freshness)||'有效性未知'}</span></header><div className="identity-meta"><RecordReference value={fact.id} label="记录 ID"/></div>{rows(primary)}{remaining.length?<details className="record-fields"><summary><ChevronDown/>更多记录信息 <span>{remaining.length}</span></summary>{rows(remaining)}</details>:null}<details className="record-fields raw-record"><summary><ChevronDown/>查看原始记录</summary><pre className="field-json" translate="no">{JSON.stringify(fact,null,2)}</pre></details><div className="print-only">{rows(remaining)}<pre className="field-json" translate="no">{JSON.stringify(fact,null,2)}</pre></div></article>;
}
export function FactList({facts,title='来源记录',description='这份快照中没有读取到对应记录。'}){return facts.length?<div className="evidence-cards">{facts.map(fact=><FactCard key={fact.ref} fact={fact}/>)}</div>:<Empty title={`尚无${title}`} description={description}/>;}
export function SnapshotNote({snapshot}){return <p className="health-note snapshot-note"><Info/><span>{modeLabel(snapshot.run_mode)}{snapshot.run_mode==='RECORDED_REPLAY'?' · 历史封存，非当前观测':''} · {absoluteTime(snapshot.as_of)}{snapshot.truncated?' · 数据已截断，请缩小窗口':''} · {historyLabel(snapshot.history_completeness)}</span></p>;}
