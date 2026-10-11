"""生成 ai.5 派生 JSON Schema、单文件阅读版和哈希清单；不运行任何靶场/网络动作。"""
from pathlib import Path
import hashlib, json, sys, yaml
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from contracts.models import CONTRACTS

def build():
    state=yaml.safe_load((ROOT/'PROJECT_STATE.yaml').read_text())
    defs={}
    for name,cls in CONTRACTS.items():
        schema=cls.model_json_schema()
        for key,value in schema.pop('$defs',{}).items():
            if key in defs and defs[key]!=value: raise ValueError(f'conflicting schema definition: {key}')
            defs[key]=value
        defs[name]=schema
    schema={'$schema':'https://json-schema.org/draft/2020-12/schema','title':'Zhiyu ai.5 Engineering Freeze contracts',
            'description':'结构校验；跨对象/运行语义另见 models.py 和 docs。','$defs':defs,
            'oneOf':[{'$ref':f'#/$defs/{name}'} for name in CONTRACTS]}
    (ROOT/'contracts/zhiyu.schema.json').write_text(json.dumps(schema,ensure_ascii=False,indent=2)+'\n')
    parts=[f"# 智御｜完整 AI 上下文与工程冻结基线\n\n版本：{state['meta']['version']}\n\n本文件自动生成。全部示例为合成数据；平台功能、性能与 A01–A15 尚未因本资料包而得到验证。\n"]
    parts.append('\n## 导航\n\n'+(ROOT/'START_HERE.md').read_text())
    parts.append('\n## 机器可读状态\n\n```yaml\n'+(ROOT/'PROJECT_STATE.yaml').read_text()+'```\n')
    for doc in sorted((ROOT/'docs').glob('*.md')):
        parts.append(f'\n---\n\n模块来源：`docs/{doc.name}`\n\n'+doc.read_text())
    parts.append('\n---\n\n# 权威数据契约\n\n```python\n'+(ROOT/'contracts/models.py').read_text()+'```\n')
    parts.append('\n# 状态迁移\n\n```json\n'+(ROOT/'contracts/state_machines.json').read_text()+'```\n')
    for name in ['golden_chain.json','scenario.json','verification_cases.json']:
        parts.append(f'\n# 合成示例：{name}\n\n```json\n'+(ROOT/'examples'/name).read_text()+'```\n')
    parts.append('\n---\n\n'+(ROOT/'CHANGELOG.md').read_text())
    out=ROOT/state['authority']['generated_reading_copy']; out.write_text('\n'.join(parts))
    records=[]
    for path in sorted(ROOT.rglob('*')):
        if not path.is_file() or path.name in {'MANIFEST.json','VALIDATION_REPORT.json'} or '__pycache__' in path.parts: continue
        raw=path.read_bytes(); records.append({'path':path.relative_to(ROOT).as_posix(),'size_bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
    manifest={'package_version':state['meta']['version'],'source_package':'2026.09.12-ai.4','files':records,
              'excluded_generated_files':['MANIFEST.json','VALIDATION_REPORT.json'],'hash_is_authenticity_signature':False}
    (ROOT/'MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'built':True,'files_in_manifest':len(records),'contracts':len(CONTRACTS),'single_file_bytes':out.stat().st_size},ensure_ascii=False))
if __name__=='__main__': build()
