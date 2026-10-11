import {validateEnvelope,ApiError} from './api';

export function validateDemoRuns(value){
 validateEnvelope(value);
 const invalid=()=>{throw new ApiError(0,'malformed_response');};
 if(!Array.isArray(value.items)||value.items.length>50)invalid();
 for(const run of value.items){
  if(!run||!/^demo-[a-f0-9]{32}$/.test(run.run_id)||run.source_environment_id!==`m6-real-${run.run_id}`||!['A','B','C','D','E'].includes(run.scenario_id)||run.run_mode!=='LIVE'||!Number.isInteger(run.version)||!Number.isInteger(run.step_index)||run.step_index<0||run.step_index>4||!Array.isArray(run.steps)||run.steps.length>5||!Number.isFinite(Date.parse(run.updated_at)))invalid();
  for(const step of run.steps){if(!step||typeof step.operation!=='string'||typeof step.status!=='string'||!step.output||typeof step.output!=='object'||(step.output.object_refs&&(!Array.isArray(step.output.object_refs)||step.output.object_refs.some(ref=>typeof ref!=='string'))))invalid();}
 }
 return value;
}
export function runIncident(run){return run.steps.flatMap(step=>step.output.object_refs||[]).find(ref=>ref.startsWith('incident:'))?.slice(9);}
export function hasArchive(run){return run.status==='COMPLETED'&&run.steps.some(step=>step.operation==='ARCHIVE'&&step.status==='COMPLETED'&&/^[a-f0-9]{64}$/.test(step.output.artifact_sha256));}
