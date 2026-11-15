"""Model-agnostic Hermes managed-preset selection and explicit GGUF companions.

No name heuristics, no filesystem-wide scans, no foreign process management.
A compatible engine and model are required: the plugin cannot make arbitrary
GGUF files support MTP merely by passing --spec-type=draft-mtp.
"""
from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
import re


def atomic_write(path: Path, blob: bytes) -> None:
    import tempfile
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.mtp-lab-', delete=False) as f:
        temp=Path(f.name)
        f.write(blob)
        f.flush()
        os.fsync(f.fileno())
    try: os.replace(temp,path)
    finally:
        if temp.exists(): temp.unlink()


def ini_sections(content:str)->dict[str,dict[str,str]]:
    result={}; active=None
    for line in content.splitlines():
        stripped=line.strip()
        if stripped.startswith('[') and stripped.endswith(']'):
            active=stripped[1:-1]
            if active in result: raise ValueError('Duplicate preset model ID: '+active)
            result[active]={}
        elif active is not None and not stripped.startswith(('#',';')) and '=' in line:
            k,v=line.split('=',1)
            result[active][k.strip().lower()]=v.strip()
    return result


def models_from_presets(preset_path:Path)->list[dict]:
    if not preset_path.is_file(): return []
    entries=ini_sections(preset_path.read_text(encoding='utf-8-sig'))
    out=[]
    for model_id,p in entries.items():
        raw=p.get('model','')
        if not raw.lower().endswith('.gguf'): continue
        # The preset is authored by Hermes. No untrusted model search here.
        out.append({'id':model_id,'model_path':raw,'mmproj':p.get('mmproj',''),
                    'native_mtp': 'draft-mtp' in [x.strip() for x in p.get('spec-type','').split(',')],
                    'native_draft':p.get('model-draft',''),
                    'context':p.get('ctx-size',''),'native_draft_n':p.get('spec-draft-n-max','')})
    return out


def companions(path:Path)->dict:
    try: obj=json.loads(path.read_text(encoding='utf-8-sig'))
    except FileNotFoundError: return {'version':1,'models':{}}
    if not isinstance(obj,dict) or obj.get('version')!=1 or not isinstance(obj.get('models'),dict):
        raise RuntimeError('Unsupported model-companions.json schema; no files changed')
    return obj


def resolve_file(raw:str, asset_dir:Path)->Path|None:
    if not raw or not isinstance(raw,str): return None
    path=Path(raw).expanduser()
    if not path.is_absolute(): path=asset_dir/path
    return path


def assert_gguf(path:Path|None, field:str)->None:
    if path is None: return
    if path.suffix.lower()!='.gguf' or not path.is_file():
        raise RuntimeError(f'{field} requires an existing GGUF file: {path}')
    with path.open('rb') as f:
        if f.read(4)!=b'GGUF': raise RuntimeError(f'{field} is not a GGUF file: {path}')


@lru_cache(maxsize=128)
def _embedded_metadata(gguf:str,mtime_ns:int,size:int)->bool:
    try:
        from hermes_cli.local_runtime.gguf import read_gguf_header
        header=read_gguf_header(gguf)
        architecture=str(header.metadata.get('general.architecture',''))
        return int(header.metadata.get(architecture+'.nextn_predict_layers',0))>0
    except (ImportError,ValueError,OSError,TypeError): return False

def detect_embedded_mtp(gguf:str)->bool:
    """Use native GGUF metadata, cached by file identity; never infer from names."""
    path=Path(gguf)
    try:
        info=path.stat()
        if not path.is_file(): return False
        return _embedded_metadata(str(path.resolve()),info.st_mtime_ns,info.st_size)
    except (ValueError,OSError):return False


def model_specs(preset_path:Path, companion_path:Path)->list[dict]:
    models=models_from_presets(preset_path)
    obj=companions(companion_path)
    for model in models:
        entry=obj['models'].get(model['id'],{})
        if not isinstance(entry,dict): entry={}
        head=resolve_file(entry.get('mtp_head') or (model['native_draft'] if model['native_mtp'] else ''),companion_path.parent)
        projector=resolve_file(entry.get('mmproj') or model['mmproj'],companion_path.parent)
        embedded=model['native_mtp'] and not model['native_draft']
        # Header detection extends native presets to community integrated-MTP models.
        embedded=embedded or (not head and detect_embedded_mtp(model['model_path']))
        draft_raw=entry.get('mtp_draft_depth') or entry.get('draft_n') or model.get('native_draft_n') or 3
        try: draft_n=max(1,min(16,int(draft_raw)))
        except (TypeError,ValueError): draft_n=3
        model.update({'mtp_head':str(head) if head else '', 'mmproj':str(projector) if projector else '',
                     'draft_n':draft_n,
                     'has_mmproj':bool(projector and projector.is_file()),
                     'embedded_mtp':embedded,
                     'mtp_kind':'external' if head else 'embedded' if embedded else 'unsupported',
                     'mtp_supported':bool((head and head.is_file()) or embedded),
                     'persistent_flag':entry.get('enable_mtp') if type(entry.get('enable_mtp')) is bool else None})
    return models


def choose_model(models:list[dict],selected:str|None,primary:str|None=None)->str|None:
    ids={m['id'] for m in models}
    for name in (selected,primary):
        if name in ids: return name
    return models[0]['id'] if len(models)==1 else None


def section_override(text:str,model_id:str,changes:dict[str,str|None])->str:
    """Change only one model section, preserve every other section byte-for-byte."""
    lines=text.splitlines(keepends=True)
    newline='\r\n' if '\r\n' in text else '\n'
    def is_heading(x):
        s=x.strip()
        return s.startswith('[') and s.endswith(']')
    sections=[(i,x.strip()[1:-1]) for i,x in enumerate(lines) if is_heading(x)]
    matches=[i for i,(_,name) in enumerate(sections) if name==model_id]
    if len(matches)!=1: raise RuntimeError(f'Model preset section not unique: {model_id}')
    k=matches[0];start=sections[k][0]+1;end=sections[k+1][0] if k+1<len(sections) else len(lines)
    block=lines[start:end]
    pending={key.lower():value for key,value in changes.items()}
    seen=set();new=[]
    for line in block:
        m=re.match(r'^\s*([a-z0-9-]+)\s*=',line,re.I)
        key=m.group(1).lower() if m else None
        if key not in pending:
            new.append(line);continue
        if key in seen: raise RuntimeError('Duplicate preset key: '+key)
        seen.add(key)
        value=pending[key]
        if value is not None:new.append(f'{key} = {value}'+newline)
    # Separate keys newly inserted after model path, never append after a next heading.
    for key,value in pending.items():
        if key not in seen and value is not None:
            if new and not new[-1].endswith(('\r','\n')):new[-1]+=newline
            new.append(f'{key} = {value}'+newline)
    return ''.join(lines[:start]+new+lines[end:])


def benchmark_presets(text:str,model:dict,enabled:bool,ctx:int)->str:
    if not model.get('mtp_supported'): raise RuntimeError('Selected model has no supported MTP configuration')
    changes={'ctx-size':str(ctx),'spec-type':'draft-mtp' if enabled else 'none',
             'model-draft':model['mtp_head'] if enabled and model['mtp_kind']=='external' else None,
             'spec-draft-n-max':str(model.get('draft_n',3)) if enabled else None,
             'spec-draft-backend-sampling':None if not enabled else 'on'}
    # Keep mmproj exactly as in native preset unless an explicitly configured link is present.
    if model['has_mmproj']:
        changes['mmproj']=model['mmproj']
    return section_override(text,model['id'],changes)


def set_companion(path:Path,model_id:str,model_ids:set[str],mtp_head:str,mmproj:str)->dict:
    """Explicit binding: no automatic guessed pairing of unrelated model weights."""
    if model_id not in model_ids: raise RuntimeError('Model ID is not a Hermes managed preset')
    head=resolve_file(mtp_head,path.parent)
    proj=resolve_file(mmproj,path.parent)
    assert_gguf(head,'MTP head')
    assert_gguf(proj,'Vision projector')
    if head is not None and proj is not None and head.resolve()==proj.resolve():
        raise RuntimeError('MTP head and mmproj must not be the same GGUF')
    obj=companions(path)
    spec=obj['models'].setdefault(model_id,{})
    if not isinstance(spec,dict):raise RuntimeError('Invalid model companion entry')
    if head: spec['mtp_head']=str(head.resolve());spec['enable_mtp']=True
    else: spec.pop('mtp_head',None);spec.pop('enable_mtp',None)
    if proj: spec['mmproj']=str(proj.resolve())
    else: spec.pop('mmproj',None)
    # Safety: preserve unrelated entries, back up existing file before changing.
    if path.exists():
        import datetime
        backup=path.with_name(path.name+'.mtp-lab-config-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
        backup.write_bytes(path.read_bytes())
    atomic_write(path,(json.dumps(obj,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    return spec
