import React from 'react';
import {describe,it,expect,vi} from 'vitest';
import {render,screen,fireEvent,within,waitFor} from '@testing-library/react';
import {ReportDocument} from './ReportsPage';
import {SnapshotNote} from './ProductUI';
import {ReportIndex} from './ReportElements';

const at='2026-10-05T07:43:31Z',hash='a'.repeat(64);
const fact=(kind,id,fields)=>({ref:`${kind}:lab:${id}`,id,kind,basis:'OBSERVED',freshness:'UNKNOWN',fields});
const snapshot={snapshot_id:'snapshot-id',incident_id:'incident-id',environment_id:'lab',scope_id:'scope-a',as_of:at,expires_at:'2026-10-05T07:48:31Z',run_mode:'LIVE',content_sha256:hash,history_completeness:'PARTIAL',facts:[
 fact('incident','incident-id',{title:'真实事件',status:'VERIFYING',priority:'P2',updated_at:at}),
 fact('verification','verification-id',{status:'PASS',security_status:'PASS',business_status:'PASS',observation_status:'PASS',valid_until:'2026-10-05T07:32:41Z'}),
 fact('resource','resource-id',{name:'原始资源',custom_field:'不得遗漏的原始值'}),
 fact('analysis','analysis-id',{status:'REFERENCE_GROUNDED',uncertainty:'未证实的假设',confidence_semantics:'MODEL_SELF_REPORTED'})
]};
const report={snapshot,report_id:'report-id',report_sha256:hash,timeline:[],limitations:['受控 Lab；不代表生产验收。']};

describe('formal report presentation',()=>{
 it('keeps expired three-dimensional PASS historical and separates execution from verification',()=>{
  const {container}=render(<ReportDocument report={report} params={{}} contextPicker={null}/>);
  expect(screen.getAllByText('历史结果已过期').length).toBeGreaterThan(0);
  const matrix=screen.getAllByRole('definition').filter(el=>el.closest('.report-verification-matrix'));
  expect(matrix.length).toBe(6);
  expect(container.querySelectorAll('.report-verification-matrix .ok').length).toBe(0);
  expect(screen.getByText(/AI 提案不构成授权；执行成功不等于独立验证通过/)).toBeTruthy();
  expect(screen.getByRole('heading',{name:/^06\s*执行回执$/})).toBeTruthy();
 });
 it('prints every source fact without changing the screen disclosures',()=>{
  const {container}=render(<ReportDocument report={report} params={{}} contextPicker={null}/>);
  expect(container.querySelector('.report-source-appendix')).toBeNull();
  fireEvent(window,new Event('beforeprint'));
  const appendix=screen.getByRole('region',{name:'完整来源记录打印附录'});
  expect(appendix.querySelectorAll('.fact-card').length).toBe(snapshot.facts.length);
  expect(within(appendix).getAllByText('不得遗漏的原始值').length).toBeGreaterThan(0);
  fireEvent(window,new Event('afterprint'));
  expect(container.querySelector('.report-source-appendix')).toBeNull();
  expect(container.querySelectorAll('.document-records[open]').length).toBe(0);
 });
 it('shows progress on the requested export format and restores it on failure',async()=>{
  let reject;
  vi.stubGlobal('fetch',vi.fn(()=>new Promise((_,fail)=>{reject=fail;})));
  render(<ReportDocument report={report} params={{}} contextPicker={null}/>);
  fireEvent.click(screen.getByRole('button',{name:'下载 JSON'}));
  const busy=screen.getByRole('button',{name:'校验与下载中…'}),markdown=screen.getByRole('button',{name:'下载 Markdown'});
  expect(busy.getAttribute('aria-busy')).toBe('true');
  expect(markdown.getAttribute('aria-busy')).toBe('false');expect(markdown.disabled).toBe(true);
  await waitFor(()=>expect(fetch).toHaveBeenCalledOnce());
  reject(new Error('test service unavailable'));
  await waitFor(()=>expect(screen.getByRole('button',{name:'下载 JSON'}).disabled).toBe(false));
 });
 it('discloses partial, complete and unknown history without a constant fallback',()=>{
  const {rerender}=render(<SnapshotNote snapshot={snapshot}/>);
  expect(screen.getByText(/历史记录不完整/)).toBeTruthy();
  rerender(<SnapshotNote snapshot={{...snapshot,history_completeness:'COMPLETE'}}/>);
  expect(screen.getByText(/历史记录完整/)).toBeTruthy();
  rerender(<SnapshotNote snapshot={{...snapshot,history_completeness:undefined}}/>);
  expect(screen.getByText(/历史完整性未知/)).toBeTruthy();
 });
 it('preserves unknown assertion shapes instead of crashing or inventing results',()=>{
  const assertions=[null,{legacy:'<img src=x>'},'raw'];
  const {container}=render(<ReportIndex facts={[fact('observation','unstructured',{assertions})]} fields={['assertions']}/>);
  expect(container.querySelector('.report-object-value').textContent).toBe(JSON.stringify(assertions,null,2));
  expect(container.querySelector('img')).toBeNull();
 });
});
