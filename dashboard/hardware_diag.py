"""Best-effort, read-only GPU / llama.cpp process diagnostics.

No driver changes, no hardcoded GPU assumptions, no network, no credentials.
GPU-wide VRAM is never mislabeled as memory used by the benchmark model.
"""
from __future__ import annotations
import hashlib
from functools import lru_cache
from pathlib import Path
import platform
import shutil
import subprocess


def _csv(args):
    if not shutil.which('nvidia-smi'):return None
    try:
        result=subprocess.run(['nvidia-smi',*args],capture_output=True,text=True,timeout=4)
    except (OSError,subprocess.TimeoutExpired):return None
    if result.returncode:return None
    return [x.strip() for x in result.stdout.splitlines() if x.strip()]


def _num(x):
    try:return int(x.strip())
    except (ValueError,TypeError):return None


def snapshot(pid=None):
    data={'gpu_source':'nvidia-smi','gpus':[],'process_vram_mib':None}
    lines=_csv(['--query-gpu=index,name,memory.total,memory.used,utilization.gpu,driver_version',
                '--format=csv,noheader,nounits'])
    if lines is None:
        data['gpu_source']='unavailable';return data
    for line in lines:
        fields=[x.strip() for x in line.split(',')]
        if len(fields)>=6:
            data['gpus'].append(dict(index=_num(fields[0]),name=fields[1],
                 vram_total_mib=_num(fields[2]),vram_used_global_mib=_num(fields[3]),
                 utilization_gpu_pct=_num(fields[4]),driver_version=fields[5]))
    # WDDM on Windows often reports N/A for per-process VRAM. Keep null.
    processes=_csv(['--query-compute-apps=pid,used_gpu_memory','--format=csv,noheader,nounits'])
    if pid is not None and processes:
        entries=[]
        for line in processes:
            fields=[x.strip() for x in line.split(',')]
            if len(fields)>=2 and _num(fields[0])==pid and _num(fields[1]) is not None:
                entries.append(_num(fields[1]))
        if entries:data['process_vram_mib']=sum(entries)
    return data


def environment():
    return {'os':platform.system(),'arch':platform.machine(),
            'python':platform.python_version(),'gpu_snapshot_note':'GPU usage is system-wide unless process_vram_mib is provided'}


def file_identity(path):
    """No costly full hash of multi-GB GGUF on HDD; fingerprint is labeled partial."""
    if not path:return None
    file=Path(path)
    try:
        with file.open('rb') as f:header=f.read(65536)
        return {'filename':file.name,'bytes':file.stat().st_size,
                'first_64k_sha256':hashlib.sha256(header).hexdigest(),
                'fingerprint_scope':'first 65536 bytes, NOT full-file SHA-256'}
    except OSError:return {'filename':file.name,'available':False}


@lru_cache(maxsize=8)
def engine_version(process_exe):
    if not process_exe:return None
    try:
        result=subprocess.run([process_exe,'--version'],capture_output=True,text=True,timeout=5)
        value=(result.stdout or result.stderr).strip()
        return value.splitlines()[0][:200] if result.returncode==0 and value else None
    except (OSError,subprocess.TimeoutExpired):return None
