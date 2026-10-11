import React from 'react';

// The supplied project artwork is copied byte-for-byte; functional icons remain Lucide.
export default function BrandMark({small=false}){
 return <img className={`brand-mark${small?' brand-mark-small':''}`} src="/brand/zhiyu-logo.png" width="40" height="40" alt="智御项目标志" decoding="async"/>;
}
