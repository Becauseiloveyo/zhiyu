import {describe,it,expect,vi} from 'vitest';
import {webcrypto,createHash} from 'node:crypto';
import {reportExport,validateReport} from './report';
import {latest,incidentView,verificationState} from './data';

const hash='a'.repeat(64),report={snapshot_id:'s',content_sha256:hash,report_sha256:hash};
const exported={...report,content:'{"number": 1.0, "title": "智御"}',media_type:'application/json',filename:'report.json'};
const response=body=>({ok:true,headers:new Headers({'content-type':'application/json'}),json:async()=>body});
function mock(body){vi.stubGlobal('crypto',webcrypto);vi.stubGlobal('fetch',vi.fn().mockResolvedValue(response(body)));}
describe('report integrity',()=>{
 it('downloads exact server bytes and preserves numeric representation',async()=>{
  const value={...exported,export_sha256:createHash('sha256').update(exported.content).digest('hex')};mock(value);
  expect((await reportExport(report,{},'json')).content).toBe(exported.content);
 });
 it('rejects changed bytes and mismatched snapshots without saving a fallback',async()=>{
  mock({...exported,export_sha256:hash});await expect(reportExport(report,{},'json')).rejects.toMatchObject({code:'report_integrity_failed'});
  mock({...exported,snapshot_id:'other',export_sha256:hash});await expect(reportExport(report,{},'markdown')).rejects.toMatchObject({code:'report_snapshot_mismatch'});
  await expect(reportExport(report,{},'html')).rejects.toMatchObject({code:'invalid_format'});
  expect(()=>validateReport({...report})).toThrow();
 });
 it('compares actual instants including completed_at; missing or tied times cannot establish latest',()=>{
  const fact=(id,fields)=>({id,kind:'result',fields});
  const a=fact('z',{completed_at:'2026-10-01T08:00:00+08:00',execution_outcome:'EXECUTION_SUCCESS'}),b=fact('a',{completed_at:'2026-10-01T01:00:00Z',execution_outcome:'FAILED'});
  expect(latest({facts:[a,b]},'result')).toBe(b);
  expect(latest({facts:[a,fact('other',{})]},'result')).toBeUndefined();
  expect(latest({facts:[a,fact('tied',{completed_at:'2026-10-01T00:00:00Z'})]},'result')).toBeUndefined();
  expect(incidentView({}, {facts:[a,fact('other',{})]}).execution).toContain('顺序未确定');
 });
 it('report verdict is bound to snapshot time rather than time of reopening',()=>{
  const value={checks:['PASS','PASS','PASS'],verificationStatus:'PASS',validUntil:'2026-10-01T01:00:00Z'};
  expect(verificationState(value,Date.parse('2026-10-01T00:00:00Z')).complete).toBe(true);
  expect(verificationState(value,Date.parse('2026-10-02T00:00:00Z')).complete).toBe(false);
 });
});
