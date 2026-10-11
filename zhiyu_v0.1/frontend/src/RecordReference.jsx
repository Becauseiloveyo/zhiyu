import React from 'react';
import {ChevronDown,Copy} from 'lucide-react';
import {toast} from 'sonner';
import {shortId} from './presentation';

export default function RecordReference({value,label='记录 ID',copy=true}){
 const text=String(value??'未记录');
 const copyValue=async()=>{
  try{await navigator.clipboard.writeText(text);toast.success(`${label}已复制`);}
  catch{toast.error('复制不可用，请展开后手动选择完整值');}
 };
 return <div className="record-reference" onClick={event=>event.stopPropagation()}>
  <details className="reference-details">
   <summary aria-label={`查看完整${label}`} title={text}><code>{shortId(text)}</code><ChevronDown aria-hidden="true"/></summary>
   <div className="reference-full"><span className="caption">完整{label}</span><code>{text}</code></div>
  </details>
  {copy?<button className="icon-button reference-copy" aria-label={`复制${label}`} title={`复制完整${label}`} onClick={copyValue}><Copy/></button>:null}
  <code className="reference-print print-only">{text}</code>
 </div>;
}
