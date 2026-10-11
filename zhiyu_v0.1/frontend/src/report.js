import {api,ApiError,queryPath,validateEnvelope,validateSnapshot} from './api';
export function validateReport(value){
 validateEnvelope(value);validateSnapshot(value.snapshot);
 if(value.schema_version!=='zhiyu-incident-report/0.9.0'||value.report_status!=='UNREVIEWED_DRAFT'||typeof value.report_id!=='string'||!/^[a-f0-9]{64}$/.test(value.report_sha256)||!Array.isArray(value.timeline)||!Array.isArray(value.sections)||!Array.isArray(value.limitations)||value.snapshot_id!==value.snapshot.snapshot_id||value.content_sha256!==value.snapshot.content_sha256)throw new ApiError(0,'malformed_report');return value;
}
export async function reportExport(report,params,format,signal=undefined){
 if(!['json','markdown'].includes(format))throw new ApiError(0,'invalid_format');
 const result=await api(queryPath(`snapshots/${encodeURIComponent(report.snapshot_id)}/report-${format}`,params),{signal});
 if(result.snapshot_id!==report.snapshot_id||result.content_sha256!==report.content_sha256||result.report_sha256!==report.report_sha256||typeof result.content!=='string'||!/^[a-f0-9]{64}$/.test(result.export_sha256))throw new ApiError(0,'report_snapshot_mismatch');
 const actual=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(result.content))),byte=>byte.toString(16).padStart(2,'0')).join('');
 if(actual!==result.export_sha256)throw new ApiError(0,'report_integrity_failed');
 return result;
}
export function saveExport(result){
 const url=URL.createObjectURL(new Blob([result.content],{type:result.media_type}));
 const link=document.createElement('a');link.href=url;link.download=result.filename.replace(/[^a-zA-Z0-9._-]/g,'_');document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
