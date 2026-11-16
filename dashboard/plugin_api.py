"""Local-only MTP Lab API: user-selected managed model, never a hardcoded GGUF."""
import hashlib
import json
import time
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException
try:
    from . import bench_core as bench
except ImportError:
    import importlib.util
    file=Path(__file__).resolve().with_name('bench_core.py')
    spec=importlib.util.spec_from_file_location('hermes_mtp_lab_bench_core',file)
    bench=importlib.util.module_from_spec(spec);spec.loader.exec_module(bench)
router=APIRouter()
API_VERSION="0.5.2"

def environment():
    sup,preset,comp,models=bench.get_model_environment()
    mid=bench.selected_id(comp,models,sup)
    return sup,preset,comp,models,mid

@router.get('/status')
def status():
    s=bench.STATE.read();now=time.time()
    for field,out in (('run_started_at','run_elapsed_s'),('stage_started_at','stage_elapsed_s')):
        value=s.get(field)
        s[out]=round(max(0,now-value),1) if isinstance(value,(int,float)) else None
    s['live_tokens']=None
    if s.get('state')=='running' and s.get('step_kind')=='request' and isinstance(s.get('live_port'),int) and isinstance(s.get('live_baseline'),(int,float)):
        try:
            live=bench.child_metrics({'port':s['live_port']},timeout=.8)
            total=live.get('tokens')
            if isinstance(total,(int,float)) and total>=s['live_baseline']:
                s['live_tokens']=int(total-s['live_baseline'])
        except Exception:pass
    try:
        sup,preset,comp,models,mid=environment()
        s['owns_router']=bool(sup and getattr(sup,'proc',None) and sup.proc.poll() is None)
        s['models']=models;s['model']=mid
        selected=next((m for m in models if m['id']==mid),None)
        if s.get('state')=='running' and s.get('selected_model')==mid and isinstance(s.get('model_spec'),dict):
            selected=s['model_spec']
        s['selected']=selected
        s['api_version']=API_VERSION
        if selected:
            s['projector_candidates']=bench.ms.projector_candidates(selected['model_path'])
            s['head_candidates']=bench.ms.head_candidates(selected['model_path'])
        else:
            s['projector_candidates']=[];s['head_candidates']=[]
        s['mtp_flag']=selected['native_mtp'] if selected else None
        s['mtp_manifest_flag']=selected['persistent_flag'] if selected else None
        s['tasks_per_phase']=len([x for x in bench.TASKS if not x['image'] or (selected and selected['has_mmproj'])])
        s['measurements_per_task_per_cycle']=4
        s['reasoning_modes']=['off','native']
        s['quality_methods']={'structured':'exact_json','code':'optional_local_docker_sandbox',
                              'grounding':'reference_heuristic','open_ended':'human_review'}
        from hermes_cli.local_runtime.bootstrap import assets_dir
        marker=Path(assets_dir())/'.mtp-lab-pending.json'
        if marker.exists():
            info=json.loads(marker.read_text(encoding='utf-8'))
            s['recovery_needed']=s.get('state')!='running'
            s['pending_original_mtp']=info.get('original')
            s['pending_model']=info.get('model')
        else:s['recovery_needed']=False
    except Exception as exc:
        s['status_warning']=str(exc);s.setdefault('models',[]);s['owns_router']=False;s['api_version']=API_VERSION
    return s

@router.post('/select')
def select(body:dict):
    if bench.STATE.read()['state']=='running':raise HTTPException(409,'Cannot change model during benchmark')
    mid=body.get('model_id')
    if not isinstance(mid,str):raise HTTPException(400,'model_id must be a string')
    try:
        _,_,comp,models,_=environment()
        bench.set_selection(comp,models,mid)
    except Exception as exc:raise HTTPException(409,str(exc))
    return {'ok':True,'model_id':mid}

@router.post('/configure')
def configure(body:dict):
    if bench.STATE.read()['state']=='running':raise HTTPException(409,'Cannot modify companions during benchmark')
    head=body.get('mtp_head','');proj=body.get('mmproj','')
    if not isinstance(head,str) or not isinstance(proj,str):raise HTTPException(400,'Paths must be strings')
    try:
        bench.ensure_owned_idle()
        _,_,comp,models,mid=environment()
        if not mid:raise RuntimeError('Choose a model first')
        entry=bench.ms.set_companion(comp,mid,{m['id'] for m in models},head.strip(),proj.strip())
    except Exception as exc:raise HTTPException(409,str(exc))
    return {'ok':True,'message':'Companion links saved with backup. Hermes will regenerate native presets on its next restart.',
            'entry':entry}

@router.post('/start')
def start(body:dict):
    trials=body.get('trials',1)
    if type(trials) is not int or trials not in (1,3):raise HTTPException(400,'trials must be 1 or 3')
    if bench.STATE.read()['state']=='running':raise HTTPException(409,'Benchmark already running')
    reasoning_mode=body.get('reasoning_mode','off')
    if reasoning_mode not in bench.REASONING_MODES:raise HTTPException(400,'reasoning_mode must be off or native')
    try:
        bench.ensure_owned_idle()
        _,_,comp,models,mid=environment()
        if not mid:raise RuntimeError('Select a local Hermes model first')
        bench.select_spec(models,mid)
        from hermes_cli.local_runtime.bootstrap import assets_dir
        if (Path(assets_dir())/'.mtp-lab-pending.json').exists():
            raise RuntimeError('A recovery marker exists; restore original presets first')
        total=bench.execute_benchmark(mid,trials,reasoning_mode)
    except Exception as exc:raise HTTPException(409,str(exc))
    return {'ok':True,'model_id':mid,'total':total}

@router.post('/cancel')
def cancel():
    if bench.STATE.read()['state']=='running':
        bench.STATE.cancel.set()
        return {'ok':True,'message':'Stopping after current request; original presets restored when idle'}
    return {'ok':True,'message':'No benchmark is running'}

@router.post('/toggle')
def toggle(body:dict):
    """Temporary selection-scoped toggle. No global manifest/other-model mutation."""
    enabled=body.get('enabled')
    if type(enabled) is not bool:raise HTTPException(400,'enabled must be boolean')
    if bench.STATE.read()['state']=='running':raise HTTPException(409,'Cannot toggle while benchmarking')
    try:
        sup=bench.ensure_owned_idle()
        _,preset,comp,models,mid=environment()
        model=bench.select_spec(models,mid)
        if model['mtp_kind']=='embedded' and not bench.ms.detect_embedded_mtp(model['model_path']):
            raise RuntimeError('Embedded MTP was inferred only from the native preset; manual toggles could hide that evidence. Use the benchmark instead, which always restores the original preset.')
        section=bench.ms.ini_sections(preset.read_text(encoding='utf-8-sig'))[mid]
        native=int(section.get('ctx-size',0))
        if native<=0:raise RuntimeError('No native context configured')
        original=preset.read_bytes()
        backup=preset.with_name(preset.name+'.mtp-lab-manual-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
        bench.ms.atomic_write(backup,original)
        bench.apply_phase(sup,preset,original,model,enabled,native)
        bench.ms.prune_backups(preset.parent,preset.name+'.mtp-lab-manual-*')
    except Exception as exc:raise HTTPException(409,str(exc))
    return {'ok':True,'enabled':enabled,'persistence':'session-only',
            'message':'Current Hermes preset changed. It may reset on next native planner restart; backup saved.'}

@router.post('/recover')
def recover():
    if bench.STATE.read()['state']=='running':raise HTTPException(409,'Benchmark still running')
    try:
        sup=bench.ensure_owned_idle()
        from hermes_cli.local_runtime.bootstrap import assets_dir
        marker=Path(assets_dir())/'.mtp-lab-pending.json'
        if not marker.exists():return {'ok':True,'message':'No recovery needed'}
        info=json.loads(marker.read_text(encoding='utf-8'))
        if info.get('schema')!=2:
            raise RuntimeError('Legacy recovery marker. Do not overwrite it; use the previous plugin to recover.')
        backup=Path(info['backup'])
        if not backup.is_file():raise RuntimeError('Original preset backup file is missing')
        original=backup.read_bytes()
        if hashlib.sha256(original).hexdigest()!=info.get('sha256'):
            raise RuntimeError('Original preset backup SHA-256 mismatch')
        preset=Path(sup.preset_path)
        bench.restore_presets(sup,preset,original)
        marker.unlink()
    except Exception as exc:raise HTTPException(409,str(exc))
    return {'ok':True,'restored':True}
