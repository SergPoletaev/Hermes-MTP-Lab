"""Hermes MTP Lab: model-agnostic, managed-runtime-only OFF/ON benchmark.

Only a selected Hermes managed preset is changed temporarily. Original preset
bytes are restored after completion or interruption. No cloud or chat UI calls.
Unsupported models fail explicitly: MTP requires compatible GGUF/engine support.
"""
from __future__ import annotations
import base64
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import re
import statistics
import threading
import time
from datetime import datetime
from urllib.request import Request, urlopen

try:
    from . import model_support as ms
except ImportError:
    import importlib.util
    spec=importlib.util.spec_from_file_location('mtp_lab_model_support',Path(__file__).with_name('model_support.py'))
    ms=importlib.util.module_from_spec(spec);spec.loader.exec_module(ms)

BENCH_CTX = 32768  # Upper bound, never grow a smaller native context
METRICS = {'llamacpp:tokens_predicted_total':'tokens',
           'llamacpp:tokens_predicted_seconds_total':'decode_seconds',
           'llamacpp:prompt_tokens_total':'prompt_tokens',
           'llamacpp:prompt_seconds_total':'prompt_seconds',
           'llamacpp:spec_decode_num_draft_tokens_total':'drafted',
           'llamacpp:spec_decode_num_accepted_tokens_total':'accepted'}
METRIC_LINE=re.compile(r'^(llamacpp:[a-z_]+)(?:\{[^}]*\})?\s+([0-9.eE+\-]+)(?:\s|$)')
TASKS=[
    {'id':'network','group':'Текст','title':'Technical explanation','image':False,
     'prompt':'Explain how a TCP connection starts, how sequence numbers and acknowledgements work, and how retransmission and congestion control differ. Use an example with lost packets and write at least six paragraphs.'},
    {'id':'code','group':'Код и данные','title':'Python code generation','image':False,
     'prompt':'Write a Python 3 function that merges overlapping date intervals, retaining time zones. Explain handling of empty intervals, equal boundaries and invalid inputs. Include three realistic unit tests, and discuss the complexity.'},
    {'id':'structured','group':'Код и данные','title':'Data extraction and reasoning','image':False,
     'prompt':'A warehouse received 18 red crates at 24 units each, 13 blue crates at 17 units each and 7 green crates at 31 units each. Then 12% of red units, 8% of blue units and 5% of green units were damaged (round each damaged count up). Calculate accepted units by color and total, show every intermediate calculation, and output a JSON object with the final results.'},
    {'id':'narrative','group':'Текст','title':'Creative reasoning','image':False,
     'prompt':'Write a grounded scene about an engineer restoring power to an alpine observatory during a snowstorm. Explain the practical reasoning behind every decision, preserve continuity of tools and locations, and end with a short inspection checklist.'},
    {'id':'scene','group':'Описание изображения','title':'Detailed image description','image':True,
     'prompt':'Describe the attached photograph in detail. Identify important objects and their colors, explain their positions relative to one another and the window, and describe lighting, materials and atmosphere. Do not invent people.'},
    {'id':'grounding','group':'Распознавание деталей','title':'Visual grounding and text','image':True,
     'prompt':'Analyze this picture methodically. What short printed label is legible on the tent card? Which objects lie to the right of the clock and which are left of it? What colors are the three stacked notebooks? Describe the clock face, the map and the mouse pad, carefully distinguishing observed facts from uncertain details.'},
]

def cmd_flag(argv:list[str],flag:str)->str:
    for i,x in enumerate(argv):
        if x==flag and i+1<len(argv):return argv[i+1]
        if x.startswith(flag+'='):return x[len(flag)+1:]
    return ''

def metrics_from_text(s:str)->dict[str,float]:
    out={}
    for line in s.splitlines():
        m=METRIC_LINE.match(line)
        if m and m.group(1) in METRICS:
            value=float(m.group(2))
            if math.isfinite(value):
                k=METRICS[m.group(1)];out[k]=out.get(k,0)+value
    return out

def diff_metrics(before:dict,after:dict)->dict:
    return {k:after[k]-before[k] for k in (before.keys() & after.keys())}

def http_json(url:str,key:str,body:dict|None=None,timeout:int=480)->dict:
    headers={'Authorization':'Bearer '+key} if key else {}
    if body is not None:headers['Content-Type']='application/json'
    req=Request(url,headers=headers,data=json.dumps(body).encode('utf-8') if body is not None else None)
    with urlopen(req,timeout=timeout) as resp:out=json.loads(resp.read())
    if not isinstance(out,dict):raise RuntimeError('Non-object llama.cpp response')
    return out

def ensure_owned_idle():
    from hermes_cli.local_runtime.bootstrap import get_supervisor
    sup=get_supervisor()
    if sup is None or getattr(sup,'proc',None) is None or sup.proc.poll() is not None:
        raise RuntimeError('Managed llama.cpp router is not owned by the current Hermes backend')
    if not sup.is_idle():raise RuntimeError('Managed llama.cpp is busy or idle status is unknown. Finish other chats first.')
    return sup

def get_model_environment():
    from hermes_cli.local_runtime.bootstrap import get_supervisor, assets_dir
    sup=get_supervisor()
    if sup is None or getattr(sup,'preset_path',None) is None:raise RuntimeError('No managed Hermes preset available')
    path=Path(sup.preset_path)
    companion_path=Path(assets_dir())/'model-companions.json'
    models=ms.model_specs(path,companion_path)
    return sup,path,companion_path,models

def get_selection_file(companion_path:Path)->Path:
    return companion_path.with_name('.mtp-lab-selection.json')

def selected_id(companion_path:Path,models:list[dict],sup)->str|None:
    stored=None
    try:stored=json.loads(get_selection_file(companion_path).read_text(encoding='utf-8')).get('model_id')
    except (FileNotFoundError,ValueError,OSError,AttributeError):pass
    return ms.choose_model(models,stored,getattr(sup,'primary_model',None))

def set_selection(companion_path:Path,models:list[dict],model_id:str)->None:
    if model_id not in {m['id'] for m in models}:
        raise RuntimeError('Model is not registered in the managed Hermes presets')
    ms.atomic_write(get_selection_file(companion_path),json.dumps({'model_id':model_id}).encode('utf-8'))

def select_spec(models:list[dict],model_id:str|None)->dict:
    matches=[m for m in models if m['id']==model_id]
    if len(matches)!=1:raise RuntimeError('Select exactly one installed Hermes model')
    model=matches[0]
    if not model['mtp_supported']:
        raise RuntimeError('No compatible MTP configuration for selected model. Link its separate MTP GGUF, or use a model with confirmed embedded MTP metadata.')
    return model

def _same_path(a:str,b:str)->bool:
    # Confirm the exact file, not just a matching filename.
    if not a or not b:return False
    return os.path.normcase(str(Path(a).resolve()))==os.path.normcase(str(Path(b).resolve()))

def child_info(sup,model:dict)->dict:
    import psutil
    parent_pid=getattr(getattr(sup,'proc',None),'pid',None)
    if not parent_pid:raise RuntimeError('Missing owned Hermes router process')
    parent=psutil.Process(parent_pid)
    hits=[]
    for proc in parent.children(recursive=False):
        try:
            argv=proc.cmdline()
            path=cmd_flag(argv,'--model') or cmd_flag(argv,'-m')
            if path and not _same_path(path,model['model_path']): continue
            if not path and model['id'].casefold() not in ' '.join(argv).casefold():continue
            port=cmd_flag(argv,'--port')
            if port.isdigit():hits.append((proc,argv,int(port)))
        except (psutil.NoSuchProcess,psutil.AccessDenied):pass
    if len(hits)!=1:raise RuntimeError(f'Expected exactly one owned child for {model["id"]}, got {len(hits)}')
    proc,argv,port=hits[0]
    draft=cmd_flag(argv,'--model-draft') or cmd_flag(argv,'--spec-draft-model')
    spec_type=cmd_flag(argv,'--spec-type')
    enabled='draft-mtp' in [x.strip() for x in spec_type.split(',')]
    head_good=(not draft) if model['mtp_kind']=='embedded' else _same_path(draft,model['mtp_head'])
    return {'pid':proc.pid,'port':port,'ctx':cmd_flag(argv,'--ctx-size'),
            'kv_k':cmd_flag(argv,'--cache-type-k'),'kv_v':cmd_flag(argv,'--cache-type-v'),
            'flash':cmd_flag(argv,'--flash-attn'),'batch':cmd_flag(argv,'--batch-size'),
            'ubatch':cmd_flag(argv,'--ubatch-size'),'mmproj':bool(cmd_flag(argv,'--mmproj')),
            'mtp':enabled and head_good,'spec_type':spec_type,'draft':draft,
            'draft_n':cmd_flag(argv,'--spec-draft-n-max')}

def child_metrics(child:dict,timeout:float=12)->dict:
    req=Request(f'http://127.0.0.1:{child["port"]}/metrics')
    with urlopen(req,timeout=timeout) as resp:
        return metrics_from_text(resp.read().decode('utf-8',errors='replace'))

def apply_phase(sup,preset:Path,original:bytes,model:dict,enabled:bool,ctx:int)->None:
    if not sup.is_idle():raise RuntimeError('A Hermes model request is still running')
    text=original.decode('utf-8-sig')
    updated=ms.benchmark_presets(text,model,enabled,ctx).encode('utf-8')
    ms.atomic_write(preset,updated)
    try:sup.reload_presets()
    except Exception:
        ms.atomic_write(preset,original)
        try:sup.reload_presets()
        except Exception:pass
        raise

def restore_presets(sup,preset:Path,original:bytes)->None:
    if not sup.is_idle():raise RuntimeError('Cannot safely restore presets during active requests')
    ms.atomic_write(preset,original)
    sup.reload_presets()
    if preset.read_bytes()!=original:raise RuntimeError('Preset bytes differ after restoration')

def route_request(sup,model_id:str,task:dict,image_b64:str|None,max_tokens:int=260)->dict:
    content=task['prompt']
    if task['image']:
        if not image_b64:raise RuntimeError('Benchmark image missing')
        content=[{'type':'text','text':content},
                 {'type':'image_url','image_url':{'url':'data:image/jpeg;base64,'+image_b64}}]
    body={'model':model_id,'messages':[{'role':'user','content':content}],
          'max_tokens':max_tokens,'temperature':0.0,'top_p':1.0,'seed':12345,'stream':False}
    tick=time.perf_counter()
    response=http_json(sup.base_url+'/chat/completions',sup.api_key,body)
    elapsed=time.perf_counter()-tick
    usage=response.get('usage') or {}
    msg=((response.get('choices') or [{}])[0].get('message') or {})
    output=(msg.get('content') or '')+' '+(msg.get('reasoning_content') or '')
    return {'elapsed':elapsed,'usage':usage,'timings':response.get('timings') or {},
            'chars':len(output.strip()),'output_sha256':hashlib.sha256(output.encode('utf-8')).hexdigest()}

def summarize(rows:list[dict])->list[dict]:
    result=[]
    for group in sorted(set(r['group'] for r in rows)):
        rec={'group':group}
        for phase in ('OFF','ON'):
            eligible=[r for r in rows if r['group']==group and r['phase']==phase and r['valid']]
            rec[phase.lower()+'_n']=len(eligible)
            rec[phase.lower()+'_tps']=round(statistics.median([r['decode_tps'] for r in eligible]),2) if eligible else None
            rec[phase.lower()+'_elapsed']=round(statistics.median([r['elapsed'] for r in eligible]),2) if eligible else None
            rec[phase.lower()+'_accepted']=sum(r['accepted'] for r in eligible)
            rec[phase.lower()+'_drafted']=sum(r['drafted'] for r in eligible)
        a,b=rec['off_tps'],rec['on_tps']
        rec['speedup']=round(b/a,3) if a and b else None
        rec['acceptance']=round(rec['on_accepted']/rec['on_drafted'],3) if rec['on_drafted'] else None
        result.append(rec)
    return result

def write_report(root:Path,rows:list[dict],notes:list[str],model:dict,restored:bool,configs:dict,ctx:int)->dict:
    root.mkdir(parents=True,exist_ok=True)
    (root/'results.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    fields=['model_id','phase','task','group','trial','valid','output_sha256','tokens','decode_seconds','decode_tps','elapsed','prompt_tokens','prompt_seconds','drafted','accepted','ctx','kv_k','kv_v','flash','mmproj','pid','detail']
    with (root/'results.csv').open('w',encoding='utf-8-sig',newline='') as file:
        writer=csv.DictWriter(file,fieldnames=fields,extrasaction='ignore');writer.writeheader();writer.writerows(rows)
    summary=summarize(rows)
    # Remove loaded PIDs, ports and draft filesystem paths from shareable report.
    safe={p:{k:v for k,v in conf.items() if k not in ('pid','port','draft')} for p,conf in configs.items()}
    comparable=bool(safe.get('OFF') and safe.get('ON'))
    if comparable:
        comparable=all(safe['OFF'].get(k)==safe['ON'].get(k) for k in ('ctx','kv_k','kv_v','flash','batch','ubatch','mmproj'))
    lines=['# Hermes MTP Lab — model-agnostic A/B benchmark','',
           f'Model ID: `{model["id"]}`',f'MTP configuration: {model["mtp_kind"]}',
           f'Has vision projector: {model["has_mmproj"]}',f'Preset restored byte-for-byte: {restored}',
           'Direct llama.cpp workloads; NOT Hermes Auto/Native/Text UI-mode timings.',
           f'OFF/ON effective flags confirmed comparable: {comparable}; context {ctx}',
           '','| Workload | OFF tok/s | ON tok/s | Speedup | Accepted/drafted |',
           '|---|---:|---:|---:|---:|']
    for s in summary:
        value=lambda x:'n/a' if x is None else str(x)
        lines.append(f'| {s["group"]} | {value(s["off_tps"])} | {value(s["on_tps"])} | {value(s["speedup"])}× | {s["on_accepted"]}/{s["on_drafted"]} |')
    lines+=['','## Actual flags (excluding private paths)','```json',json.dumps(safe,ensure_ascii=False,indent=2),'```','','## Notes']+['- '+str(n) for n in notes]
    lines+=['','Not all GGUFs support MTP. A tested model, engine and companion combination is required.',
            'Speedup is descriptive if batch/ubatch or other effective flags are unknown.']
    (root/'summary.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return {'summary':summary,'comparable':comparable,'path':str(root),'configs':safe}

class BenchmarkState:
    def __init__(self):
        self.lock=threading.RLock();self.cancel=threading.Event()
        self.data={'state':'idle','stage':'Готов к тестированию','done':0,'total':0,
                   'rows':[],'summary':[],'error':None,'report_path':None,'selected_model':None,
                   'run_started_at':None,'stage_started_at':None,'step_kind':'idle',
                   'phase':None,'current_task':None,'trial':None,'trials':None,
                   'live_port':None,'live_baseline':None,'live_token_limit':None}
    def read(self):
        with self.lock:return json.loads(json.dumps(self.data))
    def update(self,**kwargs):
        with self.lock:self.data.update(kwargs)
    def add_row(self,row):
        with self.lock:self.data['rows'].append(row);self.data['done']+=1
    def stage(self,kind:str,label:str,**extra):
        with self.lock:
            self.data.update(step_kind=kind,stage=label,stage_started_at=time.time(),
                             live_port=None,live_baseline=None,live_token_limit=None)
            self.data.update(extra)
STATE=BenchmarkState()

def execute_benchmark(model_id:str,trials:int=1):
    trials=max(1,min(3,int(trials)))
    sup,preset,comp,models=get_model_environment()
    model=select_spec(models,model_id)
    tasks=[t for t in TASKS if model['has_mmproj'] or not t['image']]
    total=2*trials*len(tasks)
    # Reserve a single benchmark slot atomically. Two near-simultaneous /start
    # calls must never run competing workers that both modify Hermes presets.
    with STATE.lock:
        if STATE.data['state']=='running':
            raise RuntimeError('Benchmark already running')
        STATE.cancel.clear()
        STATE.data.update(state='running',stage='Checking model',model_spec=model,done=0,total=total,
                          rows=[],summary=[],error=None,report_path=None,
                          selected_model=model_id,run_started_at=time.time(),stage_started_at=time.time(),
                          step_kind='checking',phase=None,current_task=None,trial=None,trials=trials,
                          live_port=None,live_baseline=None,live_token_limit=None)
    thread=threading.Thread(target=_run,args=(model_id,trials),daemon=True,name='hermes-mtp-lab-benchmark')
    try:
        thread.start()
    except Exception:
        STATE.update(state='error',stage='Worker start failed')
        raise
    return total

def _run(model_id:str,trials:int):
    original=None;backup=None;marker=None;preset=None;sup=None
    rows=[];notes=[];configs={};restored=False;ctx=0;model=None
    output=Path.home()/'Desktop'/'Hermes-MTP-Reports'
    if not (Path.home()/'Desktop').exists():output=Path.home()/'Hermes-MTP-Reports'
    folder=output/('run-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
    try:
        sup=ensure_owned_idle()
        _,preset,comp,models=get_model_environment()
        model=select_spec(models,model_id)
        original=preset.read_bytes()
        section=ms.ini_sections(original.decode('utf-8-sig'))[model_id]
        native=int(section.get('ctx-size','0'))
        if native<=0:raise RuntimeError('Native context not specified; cannot benchmark safely')
        ctx=min(native,BENCH_CTX)
        if ctx<512:raise RuntimeError('Context too small for benchmark')
        from hermes_cli.local_runtime.bootstrap import assets_dir
        marker=Path(assets_dir())/'.mtp-lab-pending.json'
        if marker.exists():raise RuntimeError('Unresolved prior benchmark marker; restore before starting another test')
        backup=preset.with_name(preset.name+'.mtp-lab-backup-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
        backup.write_bytes(original)
        ms.atomic_write(marker,json.dumps({'schema':2,'model':model_id,
                                           'original':'draft-mtp' in [x.strip() for x in section.get('spec-type','').split(',')],
                                           'backup':str(backup),
                                           'sha256':hashlib.sha256(original).hexdigest()}).encode('utf-8'))
        tasks=[t for t in TASKS if model['has_mmproj'] or not t['image']]
        img64=None
        if model['has_mmproj']:
            img=Path(__file__).resolve().parent.parent/'data'/'benchmark_scene.jpg'
            img64=base64.b64encode(img.read_bytes()).decode('ascii')
        notes.append('Saved original preset bytes. Benchmark does not edit the model companion manifest.')
        for phase,enabled in (('OFF',False),('ON',True)):
            if STATE.cancel.is_set():break
            STATE.stage('switch',f'{phase}: preparing selected model preset',phase=phase,current_task=None,trial=None)
            apply_phase(sup,preset,original,model,enabled,ctx)
            STATE.stage('loading',f'{phase}: loading {model_id}',phase=phase)
            ready=sup.ensure_model_ready(model_id)
            if not ready:raise RuntimeError('Model did not become ready: '+model_id)
            STATE.stage('warmup',f'{phase}: warm-up (not measured)',phase=phase)
            route_request(sup,model_id,{'prompt':'Explain in detail why repeatable software tests matter.','image':False},None,max_tokens=150)
            child=child_info(sup,model)
            if child['mtp']!=enabled:
                raise RuntimeError(f'MTP not confirmed for {model_id} during {phase}: observed {child["mtp"]}')
            configs[phase]=child
            for trial in range(trials):
                for task in tasks:
                    if STATE.cancel.is_set():break
                    STATE.stage('preparing',f'{phase}: {task["title"]}, trial {trial+1}/{trials}',phase=phase,current_task=task['title'],current_group=task['group'],trial=trial+1)
                    child=child_info(sup,model)
                    before=child_metrics(child)
                    STATE.stage('request',f'{phase}: generating {task["title"]}',phase=phase,current_task=task['title'],current_group=task['group'],trial=trial+1,
                                live_port=child['port'],live_baseline=before.get('tokens'),live_token_limit=260)
                    res=route_request(sup,model_id,task,img64,max_tokens=260)
                    delta=diff_metrics(before,child_metrics(child))
                    n=int(delta.get('tokens',res['usage'].get('completion_tokens',0)) or 0)
                    sec=float(delta.get('decode_seconds',0) or 0)
                    if sec<=0:sec=float(res['timings'].get('predicted_ms',0) or 0)/1000
                    tps=n/sec if sec>0 else None
                    drafted=max(0,int(delta.get('drafted',0)));accepted=max(0,int(delta.get('accepted',0)))
                    valid=bool(n>=48 and tps and math.isfinite(tps) and res['chars']>0)
                    detail=[]
                    if not valid:detail.append('Insufficient tokens or timing')
                    if enabled and (drafted==0 or accepted==0):valid=False;detail.append('MTP draft acceptance not confirmed')
                    if not enabled and drafted>0:valid=False;detail.append('Unexpected drafts in OFF')
                    usage_n=int(res['usage'].get('completion_tokens',0) or 0)
                    if usage_n and abs(n-usage_n)>max(15,usage_n*.10):
                        valid=False;detail.append('Concurrent request contamination')
                    record={'model_id':model_id,'phase':phase,'task':task['id'],'group':task['group'],
                            'trial':trial+1,'valid':valid,'output_sha256':res['output_sha256'],
                            'tokens':n,'decode_seconds':round(sec,4),'decode_tps':round(tps,3) if tps else None,
                            'elapsed':round(res['elapsed'],3),'prompt_tokens':round(delta.get('prompt_tokens',0)),
                            'prompt_seconds':round(delta.get('prompt_seconds',0),3),'drafted':drafted,'accepted':accepted,
                            'ctx':child['ctx'],'kv_k':child['kv_k'],'kv_v':child['kv_v'],'flash':child['flash'],
                            'mmproj':child['mmproj'],'pid':child['pid'],'detail':'; '.join(detail)}
                    rows.append(record);STATE.add_row(record)
                if STATE.cancel.is_set():break
            notes.append(f'{phase}: model {model_id}; ctx {ctx}; MTP confirmed {child["mtp"]}')
        if STATE.cancel.is_set():notes.append('User cancelled; partial data retained')
    except Exception as exc:
        notes.append('FAILED: '+str(exc));STATE.update(error=str(exc))
    finally:
        if original is not None and preset is not None and sup is not None:
            try:
                STATE.stage('restore','Restoring original Hermes model preset')
                restore_presets(sup,preset,original)
                restored=preset.read_bytes()==original
                if restored and marker and marker.exists():marker.unlink()
                notes.append('Restored exact original preset: '+str(restored))
            except Exception as exc:
                notes.append('RESTORE FAILED: '+str(exc))
                STATE.update(error=(STATE.read().get('error') or '')+'; RESTORE FAILED: '+str(exc))
        else:restored=True
        if model is None:model={'id':model_id,'mtp_kind':'unknown','has_mmproj':False}
        try:
            STATE.stage('report','Writing benchmark reports')
            summary=write_report(folder,rows,notes,model,restored,configs,ctx)
        except Exception as exc:
            STATE.update(state='error',stage='Report failed',error=str(exc),restored=restored)
            return
        STATE.update(state='cancelled' if STATE.cancel.is_set() else ('error' if STATE.read().get('error') else 'done'),
                     stage='Done' if restored else 'Recovery required',summary=summary['summary'],
                     comparable=summary['comparable'],report_path=summary['path'],configs=summary['configs'],
                     restored=restored,notes=notes,step_kind='finished',stage_started_at=time.time(),
                     live_port=None,live_baseline=None,live_token_limit=None)
