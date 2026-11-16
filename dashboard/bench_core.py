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
    from . import quality_eval as qe, hardware_diag as hd
except ImportError:
    import importlib.util
    spec=importlib.util.spec_from_file_location('mtp_lab_model_support',Path(__file__).with_name('model_support.py'))
    ms=importlib.util.module_from_spec(spec);spec.loader.exec_module(ms)
    spec_q=importlib.util.spec_from_file_location('mtp_lab_quality_eval',Path(__file__).with_name('quality_eval.py'))
    qe=importlib.util.module_from_spec(spec_q);spec_q.loader.exec_module(qe)
    spec_h=importlib.util.spec_from_file_location('mtp_lab_hardware_diag',Path(__file__).with_name('hardware_diag.py'))
    hd=importlib.util.module_from_spec(spec_h);spec_h.loader.exec_module(hd)

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
     'prompt':'In at most 120 words, explain TCP three-way handshake, sequence/ACK numbers, retransmission after one lost packet, and why congestion control is different from retransmission. Give one concrete example.'},
    {'id':'code','group':'Код и данные','title':'Python code generation','image':False,
     'prompt':'Write only one Python 3 fenced code block defining merge_intervals(intervals). Each input is a pair of timezone-aware datetime objects; return UTC-aware intervals sorted and merged when overlapping or touching. Preserve zero-length intervals. Empty input returns []. Reject naive datetime, reversed intervals, and malformed pairs with ValueError or TypeError. No commentary.'},
    {'id':'structured','group':'Код и данные','title':'Data extraction and reasoning','image':False,
     'prompt':'Warehouse: red 18 crates x 24 units; blue 13 x 17; green 7 x 31. Damaged: red 12%, blue 8%, green 5%; round damaged units UP separately for each color. Respond with ONLY one JSON object with integer keys red, blue, green, total representing accepted (undamaged) units. No explanation.'},
    {'id':'narrative','group':'Текст','title':'Creative reasoning','image':False,
     'prompt':'Write a coherent 90-130 word scene: an engineer restores power to an alpine observatory during a snowstorm. Preserve locations and tools. End with a 3-item inspection checklist. Output the scene, not your planning notes.'},
    {'id':'scene','group':'Описание изображения','title':'Detailed image description','image':True,
     'prompt':'Describe the attached photograph in 5-7 short sentences: main objects, colors, relative positions, window, lighting and materials. Describe only visible details. Do not invent people. No analysis preamble.'},
    {'id':'grounding','group':'Распознавание деталей','title':'Visual grounding and text','image':True,
     'prompt':'Answer briefly from this image: (1) exact text on the white tent card; (2) colors of the three stacked notebooks from top to bottom; (3) what is immediately left and right of the clock. If unclear, say so. Keep under 100 words.'},
]
REASONING_MODES=('off','native')
REQUEST_CONTRACT={'temperature':0.0,'top_k':1,'top_p':1.0,'min_p':0.0,
                  'repeat_penalty':1.0,'cache_prompt':False,'seed':12345,'stream':False}


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


def request_timeout(max_tokens:int,probe:dict|None=None)->int:
    """Per-request HTTP timeout, tolerant of heavily CPU-offloaded models.

    The warm-up probe provides a conservative per-token latency estimate that
    already includes first-load effects. Without it the previous fixed policy
    (max(480, 0.9*max_tokens) seconds) is used. The derived value is bounded to
    [base, 7200] so a single request can never hang the whole benchmark for good.
    """
    base=max(480,int(max_tokens*.9))
    if not isinstance(probe,dict):return base
    elapsed=probe.get('elapsed');usage=probe.get('usage') or {}
    try:tokens=int(usage.get('completion_tokens') or 0)
    except (TypeError,ValueError):tokens=0
    try:elapsed=float(elapsed or 0)
    except (TypeError,ValueError):elapsed=0.0
    if elapsed<=0 or tokens<=0:return base
    per_token=elapsed/tokens
    derived=per_token*max_tokens*2+180
    return int(max(base,min(7200,derived)))

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
    try:
        executable=proc.exe()
    except (psutil.Error,OSError):
        executable=None
    try:
        resident=round(proc.memory_info().rss/1048576,1)
    except (psutil.Error,OSError):
        resident=None
    draft=cmd_flag(argv,'--model-draft') or cmd_flag(argv,'--spec-draft-model')
    spec_type=cmd_flag(argv,'--spec-type')
    enabled='draft-mtp' in [x.strip() for x in spec_type.split(',')]
    head_good=(not draft) if model['mtp_kind']=='embedded' else _same_path(draft,model['mtp_head'])
    return {'pid':proc.pid,'port':port,'ctx':cmd_flag(argv,'--ctx-size'),
            'kv_k':cmd_flag(argv,'--cache-type-k'),'kv_v':cmd_flag(argv,'--cache-type-v'),
            'flash':cmd_flag(argv,'--flash-attn'),'batch':cmd_flag(argv,'--batch-size'),
            'ubatch':cmd_flag(argv,'--ubatch-size'),'mmproj':bool(cmd_flag(argv,'--mmproj')),
            'gpu_layers':cmd_flag(argv,'--n-gpu-layers') or cmd_flag(argv,'-ngl') or cmd_flag(argv,'--gpu-layers') or None,
            'actual_gpu_layers':None, # engine does not expose trustworthy count via metrics
            'draft_gpu_layers':cmd_flag(argv,'--spec-draft-ngl') or cmd_flag(argv,'-ngld') or None,
            'threads':cmd_flag(argv,'--threads') or None,
            'parallel':cmd_flag(argv,'--parallel') or cmd_flag(argv,'-np') or None,
            'engine_version':hd.engine_version(executable),
            'rss_mib':resident,
            'mtp':enabled and head_good,'spec_type':spec_type,'draft':draft,
            'draft_n':cmd_flag(argv,'--spec-draft-n-max')}

def child_metrics(child:dict,timeout:float=12)->dict:
    req=Request(f'http://127.0.0.1:{child["port"]}/metrics')
    with urlopen(req,timeout=timeout) as resp:
        return metrics_from_text(resp.read().decode('utf-8',errors='replace'))

def apply_phase(sup,preset:Path,original:bytes,model:dict,enabled:bool,ctx:int)->None:
    if not sup.is_idle():raise RuntimeError('A Hermes model request is still running')
    text=original.decode('utf-8-sig')
    # Preserve a native UTF-8 BOM while the phase preset is active so the
    # temporary file keeps Hermes' own encoding convention byte-for-byte.
    encoding='utf-8-sig' if original.startswith(b'\xef\xbb\xbf') else 'utf-8'
    updated=ms.benchmark_presets(text,model,enabled,ctx).encode(encoding)
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

def route_request(sup,model_id:str,task:dict,image_b64:str|None,max_tokens:int=768,
                  reasoning_mode:str='off',timeout:int|None=None)->dict:
    content=task['prompt']
    if task['image']:
        if not image_b64:raise RuntimeError('Benchmark image missing')
        content=[{'type':'text','text':content},
                 {'type':'image_url','image_url':{'url':'data:image/jpeg;base64,'+image_b64}}]
    if reasoning_mode not in REASONING_MODES:
        raise ValueError('Unknown reasoning policy')
    # One request contract, unchanged between OFF/ON. The model's template may
    # still ignore the no-think hint; audit actual reasoning_content separately.
    body={'model':model_id,'messages':[{'role':'user','content':content}],
          'max_tokens':max_tokens,**REQUEST_CONTRACT}
    if reasoning_mode=='off':
        body['chat_template_kwargs']={'enable_thinking':False}
        body['reasoning_effort']='none'
    if timeout is None:timeout=request_timeout(max_tokens)
    tick=time.perf_counter()
    response=http_json(sup.base_url+'/chat/completions',sup.api_key,body,
                       timeout=timeout)
    elapsed=time.perf_counter()-tick
    usage=response.get('usage') or {}
    choice=(response.get('choices') or [{}])[0]
    msg=choice.get('message') or {}
    visible=qe.normalize_response(msg.get('content'))
    reasoning=qe.normalize_response(msg.get('reasoning_content'))
    return {'elapsed':elapsed,'usage':usage,'timings':response.get('timings') or {},
            'chars':len(visible.strip())+len(reasoning.strip()),
            'visible':visible,'reasoning':reasoning,
            'visible_sha256':qe.sha(visible),'reasoning_sha256':qe.sha(reasoning),
            'output_sha256':qe.sha(visible+' '+reasoning),
            'finish_reason':choice.get('finish_reason'),
            'max_tokens':max_tokens,'reasoning_mode':reasoning_mode}


def token_budget(task:dict,ctx:int)->int:
    """Fixed per-task caps: OFF and ON use exactly the same generation budget.

    No adaptive resend: retries previously generated a SECOND, more expensive
    sample while corrupting the apparent end-to-end time and ruining parity.
    """
    choices={'network':768,'code':1536,'structured':768,'narrative':896,
             'scene':768,'grounding':768}
    if ctx<2048:raise RuntimeError('Benchmark requires native context >= 2048')
    return min(choices[task['id']],ctx-1536)


def is_truncated(res:dict,limit:int)->bool:
    try: used=int((res.get('usage') or {}).get('completion_tokens',0) or 0)
    except (ValueError,TypeError):used=0
    return res.get('finish_reason') in ('length','max_tokens') or (res.get('finish_reason') is None and used>=limit-2)


def compare_configuration(configs:dict,rows:list[dict])->dict:
    """Compare known common launch settings, explain missing values explicitly.

    MTP-specific flags are intentionally different. Unknown parameters are not
    evidence that OFF/ON actually differ and must not be reported as a mismatch.
    """
    expected=('ctx','kv_k','kv_v','flash','batch','ubatch','mmproj','gpu_layers',
              'threads','parallel','engine_version')
    off,on=configs.get('OFF'),configs.get('ON')
    differences={};unknown=[]
    if not off or not on:
        return {'status':'uncertain','differences':{},'unknown_fields':list(expected),
                'unequal_caps':0,'reason':'Both engine phases were not observed'}
    for k in expected:
        a,b=off.get(k),on.get(k)
        if a in ('',None) or b in ('',None):
            unknown.append(k)
        elif a!=b:
            differences[k]={'off':a,'on':b}
    limits={}
    for r in rows:
        limits.setdefault((r['trial'],r['task'],r['replica']),{})[r['phase']]=r['token_limit']
    mismatched_caps=sum('OFF' in p and 'ON' in p and p['OFF']!=p['ON'] for p in limits.values())
    if mismatched_caps:differences['token_limits']={'unequal_pairs':mismatched_caps}
    status='mismatch' if differences else 'uncertain' if unknown else 'matched'
    return {'status':status,'differences':differences,'unknown_fields':unknown,
            'unequal_caps':mismatched_caps,'reason':
            'Known common settings differ' if differences else
            'Known common settings match; some launch flags were not specified' if unknown else
            'All inspected common settings match'}


def summarize(rows:list[dict])->list[dict]:
    result=[]
    for group in sorted(set(r['group'] for r in rows)):
        rec={'group':group}
        for phase in ('OFF','ON'):
            eligible=[r for r in rows if r['group']==group and r['phase']==phase and r['valid']]
            speeds=[r['decode_tps'] for r in eligible if r.get('decode_tps') is not None]
            rec[phase.lower()+'_n']=len(speeds)
            rec[phase.lower()+'_tps']=round(statistics.median(speeds),2) if speeds else None
            rec[phase.lower()+'_tps_mad']=round(statistics.median(abs(x-statistics.median(speeds)) for x in speeds),3) if speeds else None
            rec[phase.lower()+'_tps_min']=round(min(speeds),3) if speeds else None
            rec[phase.lower()+'_tps_max']=round(max(speeds),3) if speeds else None
            rec[phase.lower()+'_elapsed']=round(statistics.median([r['elapsed'] for r in eligible]),2) if eligible else None
            rec[phase.lower()+'_accepted']=sum(r['accepted'] for r in eligible)
            rec[phase.lower()+'_drafted']=sum(r['drafted'] for r in eligible)
            rec[phase.lower()+'_quality_pass']=sum(r.get('quality',{}).get('status')=='pass' for r in eligible)
            rec[phase.lower()+'_quality_fail']=sum(r.get('quality',{}).get('status')=='fail' for r in eligible)
            rec[phase.lower()+'_incomplete']=sum(r.get('quality',{}).get('status')=='incomplete' for r in eligible)
        a,b=rec['off_tps'],rec['on_tps']
        rec['speedup']=round(b/a,3) if a and b else None
        rec['acceptance']=round(rec['on_accepted']/rec['on_drafted'],3) if rec['on_drafted'] else None
        result.append(rec)
    return result


def write_report(root:Path,rows:list[dict],notes:list[str],model:dict,restored:bool,
                 configs:dict,ctx:int,answers:list|None=None,hardware:list|None=None,reasoning_mode:str='off',tasks:list|None=None)->dict:
    root.mkdir(parents=True,exist_ok=True)
    (root/'results.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    fields=['model_id','phase','task','group','trial','replica','valid','finish_reason',
            'token_limit','attempts','truncated','reasoning_mode','reasoning_chars','visible_chars','visible_sha256','reasoning_sha256',
            'output_sha256','quality_status','tokens','decode_seconds','decode_tps','elapsed',
            'elapsed_total','prompt_tokens','prompt_seconds','drafted','accepted',
            'ctx','gpu_layers','draft_gpu_layers','kv_k','kv_v','flash','mmproj','detail']
    with (root/'results.csv').open('w',encoding='utf-8-sig',newline='') as file:
        writer=csv.DictWriter(file,fieldnames=fields,extrasaction='ignore');writer.writeheader();writer.writerows(rows)
    answers=answers or []
    with (root/'answers.jsonl').open('w',encoding='utf-8') as stream:
        for a in answers:
            stream.write(json.dumps(a,ensure_ascii=False)+'\n')
    parity=qe.comparisons(answers)
    parity_summary=qe.comparison_summary(parity)
    (root/'comparisons.json').write_text(json.dumps(parity,ensure_ascii=False,indent=2),encoding='utf-8')
    # These files contain only local benchmark text and optional NVIDIA telemetry;
    # never include full machine paths, auth headers or chat contents.
    hw={'environment':hd.environment(),'main_model':hd.file_identity(model.get('model_path')),
        'mtp_head':hd.file_identity(model.get('mtp_head')),
        'mmproj':hd.file_identity(model.get('mmproj')),
        'samples':hardware or []}
    (root/'hardware.json').write_text(json.dumps(hw,ensure_ascii=False,indent=2),encoding='utf-8')
    summary=summarize(rows)
    task_summary=[]
    for task_id in sorted({r['task'] for r in rows}):
        one={'task':task_id}
        for phase in ('OFF','ON'):
            values=[r['decode_tps'] for r in rows if r['task']==task_id and r['phase']==phase and r['valid'] and r.get('decode_tps') is not None]
            one[phase.lower()+'_n']=len(values)
            one[phase.lower()+'_median']=round(statistics.median(values),3) if values else None
            one[phase.lower()+'_min']=round(min(values),3) if values else None
            one[phase.lower()+'_max']=round(max(values),3) if values else None
        a,b=one['off_median'],one['on_median']
        one['speedup']=round(b/a,3) if a and b else None
        task_summary.append(one)
    (root/'task_summary.json').write_text(json.dumps(task_summary,ensure_ascii=False,indent=2),encoding='utf-8')
    safe={p:{k:v for k,v in conf.items() if k not in ('pid','port','draft','engine_exe')}
          for p,conf in configs.items()}
    comparison=compare_configuration(safe,rows)
    comparable=comparison['status']=='matched'
    (root/'comparability.json').write_text(json.dumps(comparison,ensure_ascii=False,indent=2),encoding='utf-8')
    # Every generated report is self-contained: include the exact benchmark
    # prompts and the actual reference image, when any vision task ran.
    tasks=tasks or [t for t in TASKS if any(r['task']==t['id'] for r in rows)]
    image_file=Path(__file__).resolve().parent.parent/'data'/'benchmark_scene.jpg'
    image_used=any(t.get('image') for t in tasks)
    reference=None;image_warning=None
    if image_used:
        if image_file.is_file():
            import shutil
            dest=root/'assets'/'benchmark_scene.jpg'
            dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(image_file,dest)
            reference={'path':'assets/benchmark_scene.jpg','sha256':hashlib.sha256(dest.read_bytes()).hexdigest()}
        else:
            # Degrade gracefully: a missing bundled image must not destroy an
            # otherwise complete report; the gap is recorded explicitly instead.
            image_warning=('Bundled benchmark image missing from the plugin data folder; '
                           'reference copy was NOT exported into this report.')
    protocol={'schema':'hermes-mtp-lab-protocol.v1','reasoning_mode':reasoning_mode,
              'request_contract':REQUEST_CONTRACT,'fixed_token_caps':True,
              'adaptive_retries':False,'context':ctx,'reference_image':reference,
              'reference_image_warning':image_warning,
              'request_timeout_policy':'warmup_derived_bounded_480_7200',
              'tasks':[{'id':t['id'],'group':t['group'],'title':t['title'],
                        'image':t['image'],'prompt':t['prompt'],
                        'max_tokens':token_budget(t,ctx)} for t in tasks]}
    (root/'protocol.json').write_text(json.dumps(protocol,ensure_ascii=False,indent=2),encoding='utf-8')
    quality_counts={s:sum(r.get('quality_status')==s for r in rows)
                    for s in ('pass','fail','unverified','manual_review','incomplete')}
    n_truncated=sum(r.get('truncated',False) for r in rows)
    lines=['# Hermes MTP Lab — controlled, paired benchmark','',
           f'Model ID: `{model["id"]}`',f'MTP configuration: {model.get("mtp_kind")}',
           f'Has vision projector: {model.get("has_mmproj")}',
           f'Preset restored byte-for-byte: {restored}',
           'Direct llama.cpp workloads; NOT Hermes Auto/Native/Text UI timings.',
           'No guarantee of identical greedy token streams: only visible/reasoning strings are compared, not token IDs or logits.',
           'Greedy: temperature=0; top_k=1; top_p=1; min_p=0; repeat_penalty=1; seed=12345; cache_prompt=false.',
           'Paired OFF/OFF, ON/ON and OFF/ON: separately compare visible/reasoning text; divergence is NOT by itself an incorrect answer.',
           f'Launch comparability: {comparison["status"]}; context {ctx}; unequal paired token caps: {comparison["unequal_caps"]}',
           f'Known mismatches: {comparison["differences"]}; unknown flags: {comparison["unknown_fields"]}',
           f'Reasoning policy requested: {reasoning_mode}; model template may ignore it.',
           f'Truncated at fixed token cap (no retry): {n_truncated}; quality outcomes: {quality_counts}',
           '', '| Workload | OFF median tok/s (MAD) | ON median tok/s (MAD) | Speedup | MTP accepted/drafted |',
           '|---|---:|---:|---:|---:|']
    for s in summary:
        value=lambda x:'n/a' if x is None else str(x)
        lines.append(f'| {s["group"]} | {value(s["off_tps"])} ({value(s["off_tps_mad"])}) | {value(s["on_tps"])} ({value(s["on_tps_mad"])}) | {value(s["speedup"])}× | {s["on_accepted"]}/{s["on_drafted"]} |')
    lines+=['','## Per-task speed dispersion',
            '| Task | OFF median [min, max] tok/s | ON median [min, max] tok/s | Speedup |',
            '|---|---:|---:|---:|']
    for t in task_summary:
        lines.append(f'| {t["task"]} | {t["off_median"]} [{t["off_min"]}, {t["off_max"]}] | {t["on_median"]} [{t["on_min"]}, {t["on_max"]}] | {t["speedup"]}× |')
    lines+=['','## Reproducibility','',
            '| Pair | Compared | Same visible | Same reasoning | Median visible similarity |',
            '|---|---:|---:|---:|---:|']
    for typ,s in parity_summary.items():
        lines.append(f'| {typ} | {s["pairs"]} | {s["same_visible"]} | {s["same_reasoning"]} | {s["median_visible_similarity"]} |')
    lines+=['','Visible-content differences indicate a change in decoding trajectory, not necessarily a regression.',
            'For code, execution occurs only in a local, pre-cached restricted Docker sandbox. If absent, quality is UNVERIFIED, never PASS.',
            'Reference JSON and image label/colour checks are narrow automated tests. Natural-language answers require manual review.',
            *( [image_warning] if image_warning else [] ),
            'A `valid` timing row is NOT a claim of correct content. `incomplete` means token cap prevented grading.',
            'Fixed caps, no adaptive resends. `reasoning_content` may still be produced if the model template ignores disable hints.',
            '', '## Files',
            '- `results.json`, `results.csv`: per-request speed, completion and quality.',
            '- `task_summary.json`: per-task OFF/ON speed medians, min/max and ratios.',
            '- `answers.jsonl`: full model-generated benchmark responses (review before sharing).',
            '- `comparisons.json`: visible/reasoning equality and similarity for three pair types.',
            '- `comparability.json`: known mismatches separated from unknown launch flags.',
            '- `protocol.json`: exact prompts, request contract, fixed budgets and image fingerprint.',
            '- `assets/benchmark_scene.jpg`: exact built-in vision reference, if vision tasks ran.',
            '- `hardware.json`: hardware and model/head fingerprints (first 64 KiB only), GPU-wide versus per-PID VRAM if available.',
            '', '## Actual flags (excluding private paths)','```json',
            json.dumps(safe,ensure_ascii=False,indent=2),'```','','## Notes']+['- '+str(n) for n in notes]
    lines+=['','The GPU layers field is the requested launcher setting; **actual loaded GPU layer count is unavailable** unless the engine reports it.',
            'The number of target GPU layers alone is not meaningful for MoE experts or dynamic offload.',
            'MTP requires a compatible head/engine/model combination; a GGUF header and an enabled flag alone do NOT establish compatibility.',
            'A missing GPU-offload flag or per-process VRAM metric is UNKNOWN, not an assumed value.']
    (root/'summary.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    last_gpu=next((x['gpu'] for x in reversed(hardware or []) if x.get('gpu')),None)
    version=next((x.get('engine_version') for x in hardware or [] if x.get('engine_version')),None)
    return {'summary':summary,'comparable':comparable,'path':str(root),'configs':safe,
            'parity':parity_summary,'quality_counts':quality_counts,'comparability':comparison,
            'hardware_info':{'gpu':last_gpu,'engine_version':version,
                             'gpu_layers_arg':(safe.get('ON') or safe.get('OFF') or {}).get('gpu_layers'),
                             'actual_gpu_layers':None}}


class BenchmarkState:
    def __init__(self):
        self.lock=threading.RLock();self.cancel=threading.Event()
        self.data={'state':'idle','stage':'Готов к тестированию','done':0,'total':0,
                   'rows':[],'summary':[],'error':None,'report_path':None,'selected_model':None,
                   'run_started_at':None,'stage_started_at':None,'step_kind':'idle',
                   'phase':None,'current_task':None,'trial':None,'trials':None,'replica':None,
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


def phase_order(trial:int)->list[str]:
    # A-B / B-A across cycles reduces systematic drift; two back-to-back
    # replicas in each phase permit OFF/OFF and ON/ON comparisons.
    return ['OFF','ON'] if trial%2==0 else ['ON','OFF']


def execute_benchmark(model_id:str,trials:int=1,reasoning_mode:str='off'):
    if trials not in (1,3):raise ValueError('trials must be 1 or 3')
    if reasoning_mode not in REASONING_MODES:raise ValueError('reasoning_mode must be off or native')
    sup,preset,comp,models=get_model_environment()
    model=select_spec(models,model_id)
    tasks=[t for t in TASKS if model['has_mmproj'] or not t['image']]
    total=4*trials*len(tasks)
    with STATE.lock:
        if STATE.data['state']=='running':raise RuntimeError('Benchmark already running')
        STATE.cancel.clear()
        STATE.data.update(state='running',stage='Checking model',model_spec=model,done=0,total=total,
                          rows=[],summary=[],error=None,report_path=None,parity=None,quality_counts=None,
                          selected_model=model_id,run_started_at=time.time(),stage_started_at=time.time(),
                          step_kind='checking',phase=None,current_task=None,trial=None,trials=trials,replica=None,
                          reasoning_mode=reasoning_mode,
                          live_port=None,live_baseline=None,live_token_limit=None)
    thread=threading.Thread(target=_run,args=(model_id,trials,reasoning_mode),daemon=True,name='hermes-mtp-lab-benchmark')
    try:thread.start()
    except Exception:
        STATE.update(state='error',stage='Worker start failed')
        raise
    return total


def _run(model_id:str,trials:int,reasoning_mode:str='off'):
    original=None;backup=None;marker=None;preset=None;sup=None
    rows=[];answers=[];notes=[];configs={};restored=False;ctx=0;model=None;hardware=[];tasks=[]
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
        if ctx<2048:raise RuntimeError('Context too small: minimum 2048 for controlled quality benchmark')
        from hermes_cli.local_runtime.bootstrap import assets_dir
        marker=Path(assets_dir())/'.mtp-lab-pending.json'
        if marker.exists():raise RuntimeError('Unresolved prior benchmark marker; restore before testing')
        backup=preset.with_name(preset.name+'.mtp-lab-backup-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
        ms.atomic_write(backup,original)
        ms.atomic_write(marker,json.dumps({'schema':2,'model':model_id,
                                           'original':'draft-mtp' in [x.strip() for x in section.get('spec-type','').split(',')],
                                           'backup':str(backup),
                                           'sha256':hashlib.sha256(original).hexdigest()}).encode('utf-8'))
        tasks=[t for t in TASKS if model['has_mmproj'] or not t['image']]
        img64=None
        if model['has_mmproj']:
            img=Path(__file__).resolve().parent.parent/'data'/'benchmark_scene.jpg'
            if not img.is_file():
                raise RuntimeError('Bundled benchmark image is missing from the plugin data folder: '
                                   +str(img)+'. Reinstall the plugin; vision tasks cannot run without it.')
            img64=base64.b64encode(img.read_bytes()).decode('ascii')
        notes.append('Original selected preset backed up; model companion manifest unchanged.')
        notes.append('Balanced cycle ordering; two replicas per phase. No third-party model, GPU or chat settings changed.')
        notes.append(f'Fixed request budgets; no retries; reasoning policy={reasoning_mode} (template support is model-dependent).')
        sandbox=qe.docker_ready()
        notes.append('Code sandbox: '+sandbox[1]+' (Docker image never pulled automatically).')
        for trial in range(trials):
            if STATE.cancel.is_set():break
            for phase in phase_order(trial):
                if STATE.cancel.is_set():break
                enabled=phase=='ON'
                STATE.stage('switch',f'Cycle {trial+1}/{trials} {phase}: preparing preset',
                            phase=phase,current_task=None,trial=trial+1,replica=None)
                apply_phase(sup,preset,original,model,enabled,ctx)
                STATE.stage('loading',f'{phase}: loading {model_id}',phase=phase)
                if not sup.ensure_model_ready(model_id):raise RuntimeError('Model did not become ready: '+model_id)
                STATE.stage('warmup',f'{phase}: warm-up (not measured)',phase=phase)
                probe=route_request(sup,model_id,{'prompt':'Reply with exactly: READY','image':False},
                                    None,max_tokens=192,reasoning_mode=reasoning_mode)
                # Catch broken no-thinking contracts before dozens of useless
                # token-capped outputs. Do not conflate a missing visible answer
                # with a failed MTP engine; this is a QA preflight failure.
                if (reasoning_mode=='off' and is_truncated(probe,192)
                        and not probe.get('visible','').strip()
                        and probe.get('reasoning','').strip()):
                    raise RuntimeError('No-thinking request was ignored by the model template: warm-up exhausted 192 tokens in reasoning without a visible answer. Benchmark stopped before costly repeated incomplete outputs. Try a compatible llama.cpp/chat template or select Native reasoning for timing-only.')
                child=child_info(sup,model)
                if child['mtp']!=enabled:
                    raise RuntimeError(f'MTP not confirmed for {model_id} during {phase}: observed {child["mtp"]}')
                if phase in configs:
                    compare_fields=('ctx','kv_k','kv_v','flash','batch','ubatch','gpu_layers','draft_gpu_layers','mmproj')
                    if any(configs[phase].get(k)!=child.get(k) for k in compare_fields):
                        notes.append('WARNING: effective flags changed between '+phase+' cycles')
                else:configs[phase]=child
                hardware.append({'stage':'phase_loaded','phase':phase,'trial':trial+1,
                                 'gpu':hd.snapshot(child.get('pid')),
                                 'rss_mib':child.get('rss_mib'),'engine_version':child.get('engine_version')})
                for replica in (1,2):
                    if STATE.cancel.is_set():break
                    for task in tasks:
                        if STATE.cancel.is_set():break
                        limit=token_budget(task,ctx)
                        STATE.stage('preparing',f'{phase}: {task["title"]}, cycle {trial+1}/{trials}, replica {replica}/2',
                                    phase=phase,current_task=task['title'],current_group=task['group'],
                                    trial=trial+1,replica=replica)
                        child=child_info(sup,model)
                        before=child_metrics(child)
                        STATE.stage('request',f'{phase}: {task["title"]} ({replica}/2)',
                                    phase=phase,current_task=task['title'],current_group=task['group'],
                                    trial=trial+1,replica=replica,live_port=child['port'],
                                    live_baseline=before.get('tokens'),live_token_limit=limit)
                        res=route_request(sup,model_id,task,img64,max_tokens=limit,
                                           reasoning_mode=reasoning_mode,
                                           timeout=request_timeout(limit,probe))
                        delta=diff_metrics(before,child_metrics(child))
                        attempts=1
                        elapsed_total=res['elapsed']
                        n=int(delta.get('tokens',res.get('usage',{}).get('completion_tokens',0)) or 0)
                        sec=float(delta.get('decode_seconds',0) or 0)
                        if sec<=0:sec=float(res.get('timings',{}).get('predicted_ms',0) or 0)/1000
                        tps=n/sec if sec>0 else None
                        drafted=max(0,int(delta.get('drafted',0)));accepted=max(0,int(delta.get('accepted',0)))
                        usage_n=int(res.get('usage',{}).get('completion_tokens',0) or 0)
                        truncated=is_truncated(res,limit)
                        detail=[];valid=bool(n>=48 and tps is not None and math.isfinite(tps) and res['chars']>0)
                        if not valid:detail.append('Insufficient tokens or timing')
                        if enabled and (drafted==0 or accepted==0):valid=False;detail.append('MTP draft acceptance not confirmed')
                        if not enabled and drafted>0:valid=False;detail.append('Unexpected draft tokens in OFF')
                        if usage_n and abs(n-usage_n)>max(15,usage_n*.10):
                            valid=False;detail.append('Concurrent request contamination or metrics mismatch')
                        if truncated:detail.append('Answer truncated at fixed max_tokens; no retry')
                        if reasoning_mode=='off' and res.get('reasoning','').strip():
                            detail.append('Reasoning suppression not confirmed: model still emitted reasoning_content')
                        quality=qe.grade(task['id'],res.get('visible',''),res.get('reasoning',''),
                                         'length' if truncated else res.get('finish_reason'),sandbox=sandbox)
                        answer={'model_id':model_id,'phase':phase,'trial':trial+1,'replica':replica,
                                'task':task['id'],'visible':res.get('visible',''),
                                'reasoning':res.get('reasoning',''),'finish_reason':res.get('finish_reason'),
                                'quality':quality,'token_limit':limit,'reasoning_mode':reasoning_mode}
                        answers.append(answer)
                        record={'model_id':model_id,'phase':phase,'task':task['id'],'group':task['group'],
                                'trial':trial+1,'replica':replica,'valid':valid,
                                'finish_reason':res.get('finish_reason'),'token_limit':limit,
                                'attempts':attempts,'truncated':truncated,'reasoning_mode':reasoning_mode,
                                'reasoning_chars':len(res.get('reasoning','')),'visible_chars':len(res.get('visible','')),
                                'visible_sha256':res.get('visible_sha256',qe.sha(res.get('visible',''))),
                                'reasoning_sha256':res.get('reasoning_sha256',qe.sha(res.get('reasoning',''))),
                                'output_sha256':res['output_sha256'],
                                'quality_status':quality['status'],'quality':quality,
                                'tokens':n,'decode_seconds':round(sec,4),
                                'decode_tps':round(tps,3) if tps else None,
                                'elapsed':round(res['elapsed'],3),'elapsed_total':round(elapsed_total,3),
                                'prompt_tokens':round(delta.get('prompt_tokens',0)),
                                'prompt_seconds':round(delta.get('prompt_seconds',0),3),
                                'drafted':drafted,'accepted':accepted,
                                'ctx':child.get('ctx'),'gpu_layers':child.get('gpu_layers'),
                                'draft_gpu_layers':child.get('draft_gpu_layers'),
                                'kv_k':child.get('kv_k'),'kv_v':child.get('kv_v'),
                                'flash':child.get('flash'),'mmproj':child.get('mmproj'),
                                'detail':'; '.join(detail)}
                        rows.append(record);STATE.add_row(record)
                    # Hardware snapshot outside timed request/quality evaluation.
                    hardware.append({'stage':'replica_done','phase':phase,'trial':trial+1,'replica':replica,
                                     'gpu':hd.snapshot(child.get('pid'))})
                notes.append(f'Cycle {trial+1} {phase}: MTP={child["mtp"]}, ctx={ctx}')
        if STATE.cancel.is_set():notes.append('User cancelled; partial results retained')
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
                # Housekeeping: keep only the newest preset backups on disk.
                pruned=ms.prune_backups(preset.parent,preset.name+'.mtp-lab-backup-*')
                if pruned:notes.append('Pruned '+str(len(pruned))+' old preset backup(s).')
            except Exception as exc:
                notes.append('RESTORE FAILED: '+str(exc))
                STATE.update(error=(STATE.read().get('error') or '')+'; RESTORE FAILED: '+str(exc))
        else:restored=True
        if model is None:model={'id':model_id,'mtp_kind':'unknown','has_mmproj':False}
        try:
            STATE.stage('report','Writing benchmark reports')
            result=write_report(folder,rows,notes,model,restored,configs,ctx,answers,hardware,reasoning_mode,tasks if model else [])
        except Exception as exc:
            STATE.update(state='error',stage='Report failed',error=str(exc),restored=restored)
            return
        STATE.update(state='cancelled' if STATE.cancel.is_set() else ('error' if STATE.read().get('error') else 'done'),
                     stage='Done' if restored else 'Recovery required',summary=result['summary'],
                     comparable=result['comparable'],comparability=result['comparability'],report_path=result['path'],configs=result['configs'],
                     restored=restored,notes=notes,parity=result['parity'],
                     quality_counts=result['quality_counts'],hardware_info=result['hardware_info'],step_kind='finished',
                     stage_started_at=time.time(),live_port=None,live_baseline=None,live_token_limit=None)
