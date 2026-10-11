import React from 'react';

export default function ScopePicker({access,environment,scope,grant,onChange}){
 return <div className="scope-picker">
  <label className="field-label">工作环境<select aria-label="工作环境" value={environment} onChange={event=>onChange({environment:event.target.value,scope:null,incident:null,snapshot:null,cursor:null})}>{access.environments.map(item=><option key={item.environment_id} value={item.environment_id}>{item.environment_id}</option>)}</select></label>
  <label className="field-label">读取范围<select aria-label="读取范围" value={scope||''} onChange={event=>onChange({scope:event.target.value||null,incident:null,snapshot:null,cursor:null})}>{grant?.whole_environment?<option value="">获准整环境</option>:null}{grant?.scope_ids.map(id=><option key={id} value={id}>{id}</option>)}</select></label>
  <p className="caption">仅显示已授权范围。</p>
 </div>;
}
