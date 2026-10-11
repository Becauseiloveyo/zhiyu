export function contextHref(page,current,patch={},navigation=true){
 const params=new URLSearchParams(current);
 if(navigation){params.delete('detail');params.delete('report');params.delete('cursor');}
 if(['environment','scope','hours'].some(key=>key in patch&&String(patch[key])!==params.get(key))||('incident'in patch&&patch.incident!==params.get('incident'))){params.delete('snapshot');}
 if(['environment','scope','incident'].some(key=>key in patch&&String(patch[key])!==params.get(key))){for(const key of ['recording','node','time_ref','time_cursor','list_cursor'])params.delete(key);}
 for(const [key,value] of Object.entries(patch)){if(value===null||value===undefined||value===''||value==='all')params.delete(key);else params.set(key,String(value));}
 return `#/${page}${params.size?'?'+params:''}`;
}
export function readContext(params){return{hours:[6,24,72,168].includes(Number(params.get('hours')))?Number(params.get('hours')):24,query:params.get('q')||'',filter:params.get('filter')||'all',priority:params.get('priority')||'all',source:params.get('source')||'all',tab:['summary','decision','verification','evidence','records'].includes(params.get('tab'))?params.get('tab'):'summary'};}
