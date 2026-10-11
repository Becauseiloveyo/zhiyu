"""ai.5 工程冻结资料包一致性检查。只读合成 fixtures；不执行任何网络/设备/模型动作。"""
from pathlib import Path
import copy, hashlib, json, platform, re, sys
import pydantic, yaml
from pydantic import ValidationError
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from contracts.models import (
    CONTRACTS, ActionRequest, AIPlan, AuthorizationDecision, EnvironmentProfile,
    ResourceRef, SecurityIncident, VerificationResult, action_digest,
    IncidentStatus, TaskStatus, ActionStatus,
)

def main():
    checks=[]
    def check(label, cond):
        if not cond: raise AssertionError(label)
        checks.append(label)
    def rejects(label, cls, payload):
        try: cls.model_validate(payload)
        except ValidationError: checks.append(label); return
        raise AssertionError(label)

    state=yaml.safe_load((ROOT/'PROJECT_STATE.yaml').read_text())
    check('version_is_ai5',state['meta']['version']=='2026.09.12-ai.5')
    check('engineering_freeze',state['engineering_freeze']['status']=='FROZEN_FOR_IMPLEMENTATION')
    check('platform_results_not_claimed',state['meta']['platform_test_status']=='not_run')

    manifest=json.loads((ROOT/'MANIFEST.json').read_text())
    check('manifest_version_matches',manifest['package_version']==state['meta']['version'])
    listed={r['path'] for r in manifest['files']}
    actual={p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name not in ('MANIFEST.json','VALIDATION_REPORT.json')}
    check('manifest_has_every_deliverable',listed==actual)
    for r in manifest['files']:
        raw=(ROOT/r['path']).read_bytes()
        check('hash:'+r['path'],len(raw)==r['size_bytes'] and hashlib.sha256(raw).hexdigest()==r['sha256'])

    for p in ROOT.rglob('*.md'):
        text=p.read_text()
        for link in re.findall(r'\]\(([^)]+)\)',text):
            if '://' in link or link.startswith('#'): continue
            target=(p.parent/link.split('#',1)[0]).resolve()
            check('link:'+str(p.relative_to(ROOT))+':'+link,target.exists())

    schema=json.loads((ROOT/'contracts/zhiyu.schema.json').read_text())
    def visit(node):
        if isinstance(node,dict):
            if '$ref' in node:
                ref=node['$ref']; check('schema_ref:'+ref,ref.startswith('#/$defs/') and ref.split('/')[-1] in schema['$defs'])
            for v in node.values(): visit(v)
        elif isinstance(node,list):
            for v in node: visit(v)
    visit(schema)

    objects=[]
    for p in sorted((ROOT/'examples').glob('*.json')):
        data=json.loads(p.read_text())
        if 'objects' not in data: continue
        check('synthetic:'+p.name,data.get('data_origin')=='SYNTHETIC')
        for o in data['objects']:
            cls=CONTRACTS[o['object_type']]
            cls.model_validate(o)
            objects.append(o)
    covered={o['object_type'] for o in objects}
    check('examples_cover_all_contracts',set(CONTRACTS)==covered)
    typed=lambda n:[o for o in objects if o['object_type']==n]

    resources={o['resource_id']:o for o in typed('ResourceRef')}
    events={o['event_id']:o for o in typed('NormalizedEvent')}
    groups={o['group_id']:o for o in typed('EventGroup')}
    evidence={o['evidence_id']:o for o in typed('Evidence')}
    scopes={o['scope_id']:o for o in typed('ScopeDefinition')}
    caps={o['capability_id']:o for o in typed('CapabilityManifest')}
    caphealth={(o['capability_id'],o['capability_version']):o for o in typed('CapabilityHealth')}
    actions={o['action_id']:ActionRequest.model_validate(o) for o in typed('ActionRequest')}
    authctx={o['authorization_context_id']:o for o in typed('AuthorizationContext')}
    vspecs={o['verification_spec_id']:o for o in typed('VerificationSpec')}
    modelruns={o['run_id']:o for o in typed('ModelRun')}
    tasks={o['task_id']:o for o in typed('Task')}
    for p in typed('AIPlan'):
        for t in p['tasks']: tasks.setdefault(t['task_id'],t)

    # Event -> correlation -> incident references
    for g in groups.values():
        for eid in g['member_event_ids']+g['outlier_event_ids']: check('event_group_ref:'+eid,eid in events)
    for d in typed('CorrelationDecision'):
        check('correlation_output_group',d['output_group_id'] in groups)
        for eid in d['input_event_ids']+d['excluded_event_ids']: check('correlation_input:'+eid,eid in events)
    for inc in typed('SecurityIncident'):
        for gid in inc.get('event_group_ids',[]): check('incident_group:'+gid,gid in groups)
        for eid in inc['related_event_ids']: check('incident_event:'+eid,eid in events)

    # Evidence payload integrity
    payloads=json.loads((ROOT/'examples/evidence_payloads.json').read_text())['payloads']
    for eid,e in evidence.items():
        payload=payloads[eid]
        digest=hashlib.sha256(json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        check('evidence_hash:'+eid,digest==e['integrity_hash'])
        check('evidence_content_ref:'+eid,e['content_ref']=='examples/evidence_payloads.json#/payloads/'+eid)
        for event_id in e['source_event_ids']: check('evidence_event:'+event_id,event_id in events)

    # Capability definition/health separation
    for c in caps.values():
        check('capability_health_exists:'+c['capability_id'],(c['capability_id'],c['version']) in caphealth)
        check('capability_no_dynamic_health_field','health' not in c)

    # Action -> Resource -> Scope -> Capability
    for a in actions.values():
        check('action_task',a.task_id in tasks)
        check('action_capability',a.capability_id in caps and a.capability_version==caps[a.capability_id]['version'])
        scope=scopes[a.scope_id]
        check('action_target_scope',a.target.resource_id in scope['target_resource_ids'])
        if a.source:
            check('action_source_scope',a.source.resource_id in scope['source_resource_ids'])
            check('action_capability_source',a.source.resource_id in scope['capability_source_ids'].get(a.capability_id,[]))
        check('action_capability_scope',a.capability_id in scope['allowed_capabilities'])
        if a.target.resource_type=='NETWORK_ENDPOINT' and a.source:
            port=a.target.locator['port']; proto=a.target.locator['protocol']
            check('action_network_constraint',any(a.source.resource_id in n['source_resource_ids'] and a.target.resource_id in n['target_resource_ids'] and port in n['destination_ports'] and proto in n['protocols'] for n in scope['network_constraints']))
        check('action_owned',a.ownership_tag==a.action_id and a.ttl_seconds>0)

    # Exact digest binding and authorization context snapshot
    for c in authctx.values():
        a=actions[c['action_id']]
        check('authctx_digest',c['action_digest']==action_digest(a))
        check('authctx_action_match',c['capability_id']==a.capability_id and c['target_resource_id']==a.target.resource_id)
    for d in typed('AuthorizationDecision'):
        a=actions[d['action_id']]
        check('authz_digest',d['action_digest']==action_digest(a))
        check('authz_context',d['authorization_context_id'] in authctx)
    for ap in typed('ApprovalRecord'):
        check('approval_digest',ap['action_digest']==action_digest(actions[ap['action_id']]))

    # Model run and plan linkage
    for p in typed('AIPlan'):
        if p['model_run_id']:
            check('plan_model_run',p['model_run_id'] in modelruns and modelruns[p['model_run_id']]['context_id']==p['context_id'])

    # Verification executable spec and results
    for s in typed('ValidationScenario'): check('scenario_vspec',s['verification_spec_id'] in vspecs)
    for v in typed('VerificationResult'):
        check('verification_vspec',v['verification_spec_id'] in vspecs)
        VerificationResult.model_validate(v)
    for s in vspecs.values():
        dims={x['dimension'] for x in s['checks']}; check('vspec_three_dimensions',dims=={'SECURITY','BUSINESS','OBSERVATION'})
        for c in s['checks']: check('vspec_capability:'+c['check_id'],c['capability_id'] in caps)

    # Lease and task lifecycle
    for l in typed('WorkerLease'): check('lease_task',l['task_id'] in tasks)
    for t in tasks.values():
        check('task_attempt_bound:'+t['task_id'],t['attempt_count']<=t['max_attempts'])
    for a in typed('ActionAttempt'):
        check('attempt_finished_after_start',not a['finished_at'] or a['finished_at']>=a['started_at'])

    # Forwarded duplicate vs independent app observation
    net=events['evt-net']; forwarded=events['evt-net-forwarded']; app=events['evt-app']
    check('forwarded_same_origin',net['origin_event_id']==forwarded['origin_event_id'] and net['provenance_group']==forwarded['provenance_group'])
    check('application_distinct_origin',app['provenance_group']!=net['provenance_group'])
    dec=typed('CorrelationDecision')[0]
    check('duplicate_excluded_from_group','evt-net-forwarded' in dec['excluded_event_ids'] and 'evt-net-forwarded' not in groups[dec['output_group_id']]['member_event_ids'])

    # State machine still matches enums
    machines=json.loads((ROOT/'contracts/state_machines.json').read_text())['machines']
    for name,enum in [('Incident',IncidentStatus),('Task',TaskStatus),('Action',ActionStatus)]:
        m=machines[name]; check('state_enum:'+name,set(m['states'])=={e.value for e in enum})
        for tr in m['transitions']: check('transition:'+name+':'+tr['event'],tr['from'] in m['states'] and tr['to'] in m['states'] and bool(tr['guard']))

    # Negative contract checks
    profile=copy.deepcopy(typed('EnvironmentProfile')[0]); profile['max_auto_risk']='R5'; rejects('reject_auto_r5_profile',EnvironmentProfile,profile)
    rr=copy.deepcopy(typed('ResourceRef')[0]); rr['locator'].pop('port',None); rejects('reject_bad_network_resource',ResourceRef,rr)
    inc=copy.deepcopy(typed('SecurityIncident')[0]); inc['status']='CLOSED'; inc['closure_type']=None; inc['closed_at']=None; rejects('reject_closed_without_disposition',SecurityIncident,inc)
    bad=copy.deepcopy(typed('VerificationResult')[1]); bad['status']='PASS'; rejects('reject_false_pass_with_missing_observation',VerificationResult,bad)
    auth=copy.deepcopy(typed('AuthorizationDecision')[0]); auth['business_impact']='HIGH'; rejects('reject_high_impact_without_human',AuthorizationDecision,auth)
    plan=copy.deepcopy(typed('AIPlan')[0]); plan['tasks'][0]['dependencies']=[plan['tasks'][-1]['task_id']]; rejects('reject_cyclic_plan',AIPlan,plan)
    a=next(iter(actions.values())); modified=a.model_copy(deep=True); modified.target.locator['port']=8081
    check('action_change_invalidates_digest',action_digest(a)!=action_digest(modified))

    report={
      'status':'PASS','package_version':state['meta']['version'],'validated_object_count':len(objects),
      'contract_type_count':len(CONTRACTS),'check_count':len(checks),'checks':checks,
      'runtime':{'python':platform.python_version(),'pydantic':pydantic.__version__,'pyyaml':yaml.__version__},
      'scope':'ai.5 package integrity, contract consistency, synthetic references and selected negative contract cases only',
      'not_performed':['platform implementation tests','real sensor integration','actual firewall actions','live authorization or attack validation','model quality evaluation','throughput/recovery benchmarks'],
      'platform_acceptance_A01_A15':'NOT_RUN'
    }
    (ROOT/'VALIDATION_REPORT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['status','package_version','validated_object_count','contract_type_count','check_count','platform_acceptance_A01_A15']},ensure_ascii=False))

if __name__=='__main__': main()
