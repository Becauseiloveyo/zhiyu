import {it,expect} from 'vitest';
import {validateDemoRuns,runIncident,hasArchive} from './demo';

const id=`demo-${'a'.repeat(32)}`;
const run={run_id:id,source_environment_id:`m6-real-${id}`,scenario_id:'B',run_mode:'LIVE',version:1,step_index:4,updated_at:'2026-10-03T03:00:00Z',status:'COMPLETED',steps:[{operation:'ARCHIVE',status:'COMPLETED',output:{artifact_sha256:'b'.repeat(64),object_refs:['incident:inc-actual','recording:'+id]}}]};
const envelope={projection_version:'0.9.0',environment_id:'lab',as_of:run.updated_at,run_mode:'LIVE',items:[run]};
it('opens only the actual incident reference and completed pinned archive',()=>{expect(runIncident(run)).toBe('inc-actual');expect(hasArchive(run)).toBe(true);expect(hasArchive({...run,status:'NEEDS_RECONCILIATION'})).toBe(false);});
it('rejects malformed or cross-environment demo records',()=>{expect(validateDemoRuns(envelope)).toBe(envelope);for(const change of [{source_environment_id:'other'}, {steps:[{output:{object_refs:[null]}}]}, {step_index:8}])expect(()=>validateDemoRuns({...envelope,items:[{...run,...change}]})).toThrow();});
