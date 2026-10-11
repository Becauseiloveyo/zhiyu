import React from 'react';
import {describe,it,expect,vi} from 'vitest';
import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import {ReadState,FactCard} from './ProductUI';
import {api,useRemote,validateEnvelope,validatePage,validateOverview,validateHealth,validateGraph,validateSnapshot,ApiError} from './api';
import {contextHref,readContext} from './routing';
import {verificationState,incidentView} from './data';
import {Health,EventTable} from './Overview';

const envelope={projection_version:'0.9.0',environment_id:'lab',as_of:'2026-10-01T00:00:00Z',run_mode:'LIVE'};
describe('product response contract',()=>{
 it('rejects shape changes, corrupt timestamps, fabricated graph causality and oversized graphs',()=>{
  for(const value of [null,{}, {...envelope,as_of:'invalid'}, {...envelope,run_mode:'SIMULATED_AS_LIVE'}])expect(()=>validateEnvelope(value)).toThrow(ApiError);
  expect(()=>validatePage({...envelope,items:[{incident_id:'x',title:'x',updated_at:envelope.as_of}]})).toThrow();
  expect(()=>validateOverview({...envelope,metrics:{incidents:'9'}})).toThrow();
  expect(()=>validateHealth({...envelope,sensors:{}})).toThrow();
  expect(()=>validateGraph({...envelope,nodes:[],edges:[{source:'a',target:'b',causal:true}]})).toThrow();
  expect(()=>validateGraph({...envelope,nodes:Array(201).fill({}),edges:[]})).toThrow();
  expect(()=>validateSnapshot({...envelope,snapshot_id:'x',content_sha256:'fake',facts:[]})).toThrow();
 });
 it('preserves empty data as zero records and never substitutes preview fixtures',()=>{
  expect(validatePage({...envelope,items:[],next_cursor:null}).items).toEqual([]);
  expect(incidentView({incident_id:'i',title:'real',status:'NEW',priority:'P2',updated_at:envelope.as_of}).riskScore).toBeNull();
 });
 it('scope changes discard the snapshot; page changes preserve a shared snapshot',()=>{
  const params=new URLSearchParams('environment=lab&scope=a&incident=i&snapshot=s&hours=24&cursor=c');
  const link=contextHref('graph',params,{});expect(link).toContain('snapshot=s');expect(link).not.toContain('cursor=');
  expect(contextHref('graph',params,{scope:'b'})).not.toContain('snapshot=');
  expect(contextHref('graph',params,{incident:'j'})).not.toContain('snapshot=');
  expect(readContext(new URLSearchParams('hours=999')).hours).toBe(24);
 });
});
describe('visible safety and uncertainty',()=>{
 it('cannot promote expired or incomplete PASS to current success',()=>{
  const base={checks:['PASS','PASS','PASS'],verificationStatus:'PASS'};
  expect(verificationState(base).complete).toBe(false);
  expect(verificationState({...base,validUntil:'2000-01-01T00:00:00Z'}).verdict).toBe('历史结果已过期');
  expect(verificationState({...base,checks:['PASS','FAIL','PASS']}).complete).toBe(false);
  expect(verificationState({...base,checks:['PASS','PASS','INCONCLUSIVE']}).complete).toBe(false);
 });
 it('renders loading, permission and service failures explicitly',()=>{
  const retry=vi.fn(),{rerender}=render(<ReadState state={{status:'loading'}} onRetry={retry}>{()=>null}</ReadState>);
  expect(screen.getByRole('status').getAttribute('aria-label')).toContain('正在加载');
  rerender(<ReadState state={{status:'error',error:new ApiError(403,'denied')}} onRetry={retry}>{()=>null}</ReadState>);
  expect(screen.getByText('当前身份无权读取这个环境或范围。')).toBeTruthy();
  fireEvent.click(screen.getByRole('button',{name:'重新读取'}));expect(retry).toHaveBeenCalledOnce();
  rerender(<Health state={{status:'error',error:new ApiError(503,'down')}} onReload={retry}/>);
  expect(screen.queryByText('HEALTHY')).toBeNull();expect(screen.getByText('数据服务不可用，无法确认当前状态。')).toBeTruthy();
 });
 it('escapes untrusted evidence and retains inference labels',()=>{
  const fact={ref:'a',id:'record',kind:'analysis',basis:'MODEL_INFERENCE',freshness:'UNKNOWN',fields:{incident_summary:'<img src=x onerror=alert(1)>',hypotheses:[{claim:'guess'}]}};
  const {container}=render(<FactCard fact={fact}/>);expect(container.querySelector('img')).toBeNull();expect(screen.getByText('<img src=x onerror=alert(1)>')).toBeTruthy();expect(screen.getByText('模型推断 · 未知')).toBeTruthy();expect(container.querySelector('.raw-record pre').textContent).toContain('MODEL_INFERENCE');
 });
 it('incident rows are keyboard accessible and retain real identifiers',()=>{
  const choose=vi.fn(),row=incidentView({incident_id:'canonical-id',title:'实际记录',status:'NEW',priority:'P1',updated_at:envelope.as_of});
  render(<EventTable items={[row]} onSelect={choose}/>);fireEvent.click(screen.getByRole('button',{name:'查看 canonical-id 实际记录'}));expect(choose).toHaveBeenCalledWith(row);
 });
 it('collapses model identifiers without hiding validity, model semantics or authorization',()=>{
  const fact={ref:'analysis:a',id:'analysis-a',kind:'analysis',basis:'MODEL_INFERENCE',freshness:'UNKNOWN',fields:{model_run_id:'model-run-'+ 'a'.repeat(64),status:'REFERENCE_GROUNDED',confidence_semantics:'MODEL_SELF_REPORTED',valid_until:'2026-10-01T01:00:00Z',outcome:'DENY'}};
  render(<FactCard fact={fact} compact/>);
  const metadata=screen.getAllByText(fact.fields.model_run_id).map(node=>node.closest('details')).find(Boolean);
  expect(metadata).toBeTruthy();expect(metadata.open).toBe(false);
  for(const value of ['引用已核对，内容尚未核实','模型自报，未校准','拒绝'])expect(screen.getByText(value).closest('details')).toBeNull();
  const original=screen.getAllByText(/"REFERENCE_GROUNDED"/).map(node=>node.closest('details')).find(Boolean);expect(original).toBeTruthy();expect(original.open).toBe(false);
  expect(screen.getByText('2026/10/01 09:00:00 +08:00').closest('details')).toBeNull();
 });
});
describe('transport and stale context',()=>{
 it('rejects HTML failure pages instead of displaying fallback data',async()=>{
  vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:true,headers:new Headers({'content-type':'text/html'})}));
  await expect(api('/v1/product/overview')).rejects.toMatchObject({code:'malformed_response'});
 });
 it('ignores a delayed response after switching the authorized query',async()=>{
  const responses=new Map();vi.stubGlobal('fetch',vi.fn(path=>new Promise(resolve=>responses.set(path,resolve))));
  function Probe({path}){const state=useRemote(path);return <span>{state.status==='ready'?state.data.value:state.status}</span>;}
  const {rerender}=render(<Probe path="/v1/product/a"/>);await waitFor(()=>expect(responses.has('/v1/product/a')).toBe(true));
  rerender(<Probe path="/v1/product/b"/>);await waitFor(()=>expect(responses.has('/v1/product/b')).toBe(true));
  const response=value=>({ok:true,headers:new Headers({'content-type':'application/json'}),json:async()=>({value})});
  responses.get('/v1/product/b')(response('scope-b'));await screen.findByText('scope-b');
  responses.get('/v1/product/a')(response('scope-a'));await waitFor(()=>expect(screen.queryByText('scope-a')).toBeNull());
 });
});
