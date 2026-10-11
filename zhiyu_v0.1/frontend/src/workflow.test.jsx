import React from 'react';
import {describe,it,expect,vi} from 'vitest';
import {render,screen,fireEvent} from '@testing-library/react';
import Details,{summarizeSnapshot} from './Details';
import EventWorkspace from './EventWorkspace';
import {graphNeighbors} from './EvidenceGraph';
import {contextHref} from './routing';
import {incidentView} from './data';
import {eventTitle,eventSearchQuery} from './presentation';

const make=(kind,id,fields={},basis='DERIVED')=>({kind,id,fields,basis,freshness:'UNKNOWN',ref:`${kind}:lab:${id}`});
const snapshot={incident_id:'i',snapshot_id:'s',as_of:'2026-10-05T07:43:31Z',expires_at:'2026-10-05T07:48:31Z',history_completeness:'PARTIAL',facts:[make('incident','i',{title:'authentication: ["10.0.0.1"]',status:'VERIFYING',priority:'P2',affected_asset_ids:['r'],updated_at:'2026-10-05T07:43:31Z'}),make('event','denied',{outcome:'DENIED'}),make('event','unknown',{}),make('analysis','a',{uncertainty:'The evidence for the affected resources is not provided.'},'MODEL_INFERENCE')]};
describe('event investigation contract',()=>{
 it('keeps missing outcomes and resource records uncertain',()=>{
  const summary=summarizeSnapshot(snapshot);expect(summary.events).toHaveLength(2);expect(summary.denied).toBe(1);expect(summary.resources).toEqual([{id:'r'}]);
  const record=incidentView({incident_id:'i',...snapshot.facts[0].fields},snapshot);
  render(<Details record={record} full onNavigate={vi.fn()} onTabChange={vi.fn()}/>);
  expect(screen.getByText(/其中 1 条记录结果为拒绝/)).toBeTruthy();expect(screen.queryByText(/结果均为拒绝/)).toBeNull();
  expect(screen.getByText(/模型指出受影响资源的证据不足/)).toBeTruthy();
 });
 it('links every event view without confusing snapshot expiry and verification expiry',()=>{
  const navigate=vi.fn(),record=incidentView({incident_id:'i',...snapshot.facts[0].fields},snapshot);
  render(<EventWorkspace record={record} page="graph" tab="summary" onNavigate={navigate} onReload={vi.fn()}><p>真实来源</p></EventWorkspace>);
  expect(screen.getByRole('tab',{name:'证据图谱'}).getAttribute('aria-selected')).toBe('true');
  fireEvent.click(screen.getByRole('tab',{name:'独立验证'}));expect(navigate).toHaveBeenCalledWith('incident',{tab:'verification'});
  expect(screen.getByText('快照有效期已结束')).toBeTruthy();expect(screen.queryByText('验证已过期')).toBeNull();
 });
 it('never invents graph relationships and preserves distinct canonical node identities',()=>{
  const nodes=[{id:'incident:i',kind:'incident',label:'i'},{id:'attempt:same',kind:'attempt',label:'same'},{id:'result:same',kind:'result',label:'same'},{id:'evidence:unlinked',kind:'evidence',label:'unlinked'}];
  const edges=[{source:'incident:i',target:'attempt:same'},{source:'result:same',target:'incident:i'},{source:'incident:i',target:'missing'}];
  const result=graphNeighbors(nodes,edges,'incident:i');expect(new Set(result.map(x=>x.node.id))).toEqual(new Set(['attempt:same','result:same']));expect(result.flatMap(x=>x.edges)).toHaveLength(2);
 });
 it('drops investigation selection on scope changes while keeping shared snapshot on view changes',()=>{
  const params=new URLSearchParams('environment=lab&scope=a&incident=i&snapshot=s&node=evidence%3Ae&time_ref=event%3Ae&time_cursor=c&list_cursor=l');
  expect(contextHref('timeline',params)).toContain('snapshot=s');expect(contextHref('timeline',params)).toContain('node=');
  const changed=new URLSearchParams(contextHref('graph',params,{scope:'b'}).split('?')[1]);
  for(const key of ['snapshot','node','time_ref','time_cursor','list_cursor'])expect(changed.has(key)).toBe(false);
 });
 it('searches the displayed Chinese event category through its canonical title',()=>{expect(eventSearchQuery('认证')).toBe('authentication');expect(eventSearchQuery('认证活动')).toBe('authentication');expect(eventSearchQuery('10.0.0.1')).toBe('10.0.0.1');expect(eventSearchQuery('任意事件')).toBe('任意事件');});
 it('translates the known machine title without replacing arbitrary incident text',()=>{
  expect(eventTitle('authentication: ["10.0.0.1"]')).toBe('认证活动 · 10.0.0.1');expect(eventTitle('custom: ["value"]')).toBe('custom: ["value"]');expect(snapshot.facts[0].fields.title).toBe('authentication: ["10.0.0.1"]');
 });
});
