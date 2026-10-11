import React,{useState} from 'react';
import {ChevronDown} from 'lucide-react';
import {absoluteTime} from './data';
import {FactList,FieldValue} from './ProductUI';
import {Empty} from './ui';
import {kindLabel,displayValue,basisLabel} from './presentation';
import RecordReference from './RecordReference';

export function ReportFacts({rows,className=''}){
 return <dl className={`report-facts ${className}`}>{rows.map(([label,value])=><div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>;
}
export function ReportSection({id,number,title,description='',children}){
 return <section id={`report-${id}`} className="report-section"><h3 tabIndex={-1}><span>{number}</span>{title}</h3>{description?<p className="report-section-intro">{description}</p>:null}{children}</section>;
}
export function VerificationMatrix({verdict}){
 return <dl className="report-verification-matrix" aria-label="三维独立验证">{verdict.rows.map(row=><div key={row.label}><dt>{row.label}</dt><dd><span className={`report-check ${row.tone}`}><i/>{displayValue(row.value)}</span><small>{row.effective}</small></dd></div>)}</dl>;
}
export function ReportRecords({facts,title='完整来源记录'}){
 const [open,setOpen]=useState(false);
 if(!facts.length)return null;
 return <details className="document-records" onToggle={event=>setOpen(event.currentTarget.open)}><summary><ChevronDown/>{title}<span>{facts.length} 条</span></summary>{open?<FactList facts={facts} title={title}/>:null}</details>;
}
const labels={status:'状态',outcome:'决定',execution_outcome:'执行结果',assessed_risk:'风险等级',human_approval_required:'需要人工审批',policy_version:'策略版本',scope_id:'授权范围',action_id:'动作引用',security_status:'安全目标',business_status:'业务健康',observation_status:'观测有效性',assertion_status:'断言结果',assertions:'独立断言',execution_status:'检查执行',confidence_semantics:'置信度语义',semantic_correctness:'语义正确性',incident_summary:'模型摘要',uncertainty:'不确定性',mode:'提案模式',reason:'原因',reasons:'原因',denied_dimensions:'拒绝维度',business_impact:'业务影响',claim:'验证声明',claim_kind:'声明类型',trust_status:'来源信任',data_origin:'数据来源',source_type:'来源类型',replan_count:'重规划次数',recommended_next_step:'原记录建议'};
const timeFields=[['finished_at','完成时间'],['completed_at','完成时间'],['observed_at','观测时间'],['source_timestamp','来源时间'],['created_at','创建时间'],['started_at','开始时间'],['checked_at','检查时间'],['collected_at','采集时间'],['ingested_at','入库时间']];
function Value({field,value}){
 if(typeof value==='string'&&/_id$|_ref$/.test(field))return <RecordReference value={value} label={labels[field]||field}/>;
 if(field==='assertions'&&Array.isArray(value)&&value.every(item=>item&&typeof item==='object'&&!Array.isArray(item)&&Object.hasOwn(item,'field')))return <dl className="report-assertions">{value.map((item,i)=><div key={i}><dt>{String(item.field??'未提供字段')} · {String(item.operator??'未提供比较方式')}</dt><dd>预期：{JSON.stringify(item.expected)??'未提供'}<br/>观测：{JSON.stringify(item.observed)??'未提供'}</dd></div>)}</dl>;
 return value===null||value===undefined?'未记录':typeof value==='object'?<span className="report-object-value">{JSON.stringify(value,null,2)}</span>:<FieldValue field={field} value={value}/>;
}
export function ReportIndex({facts,fields=[],title='记录索引'}){
 if(!facts.length)return <Empty title={`尚无${title}`} description="这份快照未读取到对应记录，不能据此确认安全或处置效果。"/>;
 return <div className="report-index-scroll" tabIndex={0} role="region" aria-label={title}><table className="report-index document-table"><thead><tr><th>记录与来源</th><th>原记录状态与说明</th><th>记录时间与有效期</th></tr></thead><tbody>{facts.map(fact=>{
  const entries=fields.filter(key=>Object.hasOwn(fact.fields,key)),moment=timeFields.find(([key])=>fact.fields[key]),until=fact.fields.valid_until||fact.fields.expires_at;
  return <tr key={fact.ref}><td><strong>{kindLabel(fact.kind)}</strong><RecordReference value={fact.id} label="来源记录 ID"/><small>{basisLabel(fact.basis)} · {displayValue(fact.freshness)}</small></td><td>{entries.length?<dl className="report-index-values">{entries.map(key=><div key={key}><dt>{labels[key]||key}</dt><dd><Value field={key} value={fact.fields[key]}/></dd></div>)}</dl>:<span className="subtle">未提供对应状态字段</span>}</td><td>{moment?<><small>{moment[1]}</small><time dateTime={fact.fields[moment[0]]}>{absoluteTime(fact.fields[moment[0]])}</time></>:<span className="subtle">时间未提供</span>}{until?<><small>{fact.fields.valid_until?'有效至':'到期时间'}</small><time dateTime={until}>{absoluteTime(until)}</time></>:<small>有效期未提供</small>}</td></tr>;
 })}</tbody></table></div>;
}
