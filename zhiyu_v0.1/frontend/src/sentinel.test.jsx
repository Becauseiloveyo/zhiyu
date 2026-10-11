import React from 'react';
import {describe,it,expect,vi} from 'vitest';
import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import SentinelOverview from './SentinelOverview';
import {incidentView} from './data';

const envelope={projection_version:'0.9.0',environment_id:'lab',as_of:'2026-10-01T00:00:00Z',run_mode:'LIVE'};
const row=id=>({incident_id:id,title:`事件 ${id}`,status:'VERIFYING',priority:'P2',updated_at:envelope.as_of});
const fact=(kind,id,fields={})=>({ref:`${kind}:${id}`,kind,id,fields});
const snapshot=id=>({...envelope,incident_id:id,snapshot_id:`snapshot-${id}`,content_sha256:'a'.repeat(64),facts:[fact('incident',id,row(id)),fact('verification','v',{security_status:'PASS',business_status:'PASS',observation_status:'PASS',status:'PASS',valid_until:'2000-01-01T00:00:00Z'})]});
const response=data=>({ok:true,headers:new Headers({'content-type':'application/json'}),json:async()=>data});
function props(overrides={}){return {items:[incidentView(row('first')),incidentView(row('second'))],overview:{status:'ready',data:{...envelope,metrics:{incidents:2,needs_attention:0,associated_events:0,incident_delta_percent:null},status_counts:{VERIFYING:2},daily_incidents:[]}},health:{status:'ready',data:{...envelope,sensors:[],database:'AVAILABLE',ai_mode:'OFF',runtime_status:'UNKNOWN'}},listState:{status:'ready',data:{next_cursor:null}},onOpen:vi.fn(),onNavigate:vi.fn(),onReload:vi.fn(),contextOpen:true,onToggleContext:vi.fn(),params:{environment_id:'lab',scope_id:'permitted',hours:168},query:'',filter:'all',priority:'all',onSearch:vi.fn(),onFilter:vi.fn(),onFirst:vi.fn(),onNext:vi.fn(),hasCursor:false,onHealth:vi.fn(),...overrides};}
describe('Overview snapshot and control integration',()=>{
 it('shares the selected snapshot across verification and graph, never treating an expired PASS as success',async()=>{
  vi.stubGlobal('fetch',vi.fn(path=>Promise.resolve(response(snapshot(path.includes('/second/')?'second':'first')))));
  const p=props();render(<SentinelOverview {...p}/>);
  await screen.findByText('历史结果已过期');
  expect(screen.queryByText('独立验证通过')).toBeNull();
  expect(screen.getAllByText('历史 · 通过')).toHaveLength(3);
  fireEvent.click(screen.getByRole('button',{name:'查看依据'}));
  expect(p.onNavigate).toHaveBeenLastCalledWith('incident',{incident:'first',snapshot:'snapshot-first',tab:'verification'});
  fireEvent.click(screen.getByRole('button',{name:'事件 second',exact:true}));
  await waitFor(()=>expect(screen.getByText('所选事件 second')).toBeTruthy());
  fireEvent.click(screen.getByRole('button',{name:'证据图谱'}));
  expect(p.onNavigate).toHaveBeenLastCalledWith('graph',{incident:'second',snapshot:'snapshot-second'});
  expect(fetch).toHaveBeenCalledWith(expect.stringContaining('scope_id=permitted'),expect.any(Object));
 });
 it('fails closed when the snapshot envelope or root belongs to another event',async()=>{
  vi.stubGlobal('fetch',vi.fn(()=>Promise.resolve(response({...snapshot('first'),facts:[fact('incident','other',row('other'))]}))));
  render(<SentinelOverview {...props()}/>);
  await waitFor(()=>expect(screen.getAllByRole('alert')).toHaveLength(2));
  expect(screen.getByRole('button',{name:'查看依据'}).disabled).toBe(true);
  expect(screen.queryByText('历史结果已过期')).toBeNull();
 });
 it('keeps missing AI, authorization and execution records unavailable instead of claiming a completed chain',async()=>{
  vi.stubGlobal('fetch',vi.fn(()=>Promise.resolve(response(snapshot('first')))));
  render(<SentinelOverview {...props()}/>);
  await screen.findByText('历史结果已过期');
  for(const name of ['AI 研判','授权决定','动作与回执'])expect(screen.getByRole('button',{name:`${name} 未读取到记录`}).disabled).toBe(true);
  expect(screen.getByText('记录数量不代表执行成功；明确引用关系见证据图谱。AI 提案不构成授权。')).toBeTruthy();
 });
 it('exposes real pagination, filters and an explicit empty reset without manufacturing rows',()=>{
  const p=props({items:[],hasCursor:true,listState:{status:'ready',data:{next_cursor:'server-cursor'}}});
  render(<SentinelOverview {...p}/>);
  fireEvent.change(screen.getByRole('combobox',{name:'概览事件状态'}),{target:{value:'VERIFYING'}});
  expect(p.onFilter).toHaveBeenLastCalledWith({filter:'VERIFYING'});
  fireEvent.click(screen.getByRole('button',{name:'重置筛选'}));
  expect(p.onFilter).toHaveBeenLastCalledWith({filter:null,priority:null,q:null});
  fireEvent.click(screen.getByRole('button',{name:'下一页'}));expect(p.onNext).toHaveBeenCalledOnce();
  fireEvent.click(screen.getByRole('button',{name:'返回首页'}));expect(p.onFirst).toHaveBeenCalledOnce();
  expect(screen.queryByRole('table')).toBeNull();
 });
 it('offers a reload for the fixed seven-day empty trend and hides unavailable pagination',()=>{
  const p=props({items:[]});render(<SentinelOverview {...p}/>);
  expect(screen.getByText('近 7 日没有趋势记录')).toBeTruthy();
  expect(screen.queryByText('可调整全局时间窗口或查询条件。')).toBeNull();
  fireEvent.click(screen.getByRole('button',{name:'重新读取',exact:true}));
  expect(p.onReload).toHaveBeenCalledOnce();
  expect(screen.queryByRole('button',{name:'下一页'})).toBeNull();
  expect(screen.queryByRole('button',{name:'返回首页'})).toBeNull();
 });
});
