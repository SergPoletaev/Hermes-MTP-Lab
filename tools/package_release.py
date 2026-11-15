#!/usr/bin/env python3
"""Build source and portable distribution ZIPs without any network/Git dependence."""
from __future__ import annotations
from pathlib import Path
import argparse, zipfile
ROOT = Path(__file__).resolve().parents[1]
VERSION='0.3.3'
PROJECT='Hermes-MTP-Lab'
PREFIX='Hermes_MTP_Lab_v'+VERSION
PLUGIN_TOP=['plugin.yaml','__init__.py']
PLUGIN_DIRS={'dashboard','desktop','data'}
INSTALL_TOP=[
    'Install-Hermes-MTP-Lab.cmd', 'Install-Hermes-MTP-Lab.ps1',
    'README.md','docs/assets/mtp-lab-dashboard.png',
    'docs/ARCHITECTURE.md','docs/BENCHMARK_METHODOLOGY.md','docs/EXAMPLE_RESULTS_2026-11-15.md',
    'LICENSE','SECURITY.md','CHANGELOG.md'
]
SKIP_DIR={'__pycache__','.git','.idea','.vscode','.pytest_cache','dist','build','node_modules'}
SKIP_EXT={'.pyc','.pyo','.zip','.tmp','.log'}

def source_list():
    # Only audited source files are packaged. Untracked files, local state,
    # credentials and old archives must never enter a public release by accident.
    from verify_repo import EXPECT
    return [ROOT / name for name in sorted(EXPECT)]

def portable_list():
    files=[ROOT/x for x in INSTALL_TOP]
    files += [ROOT/x for x in PLUGIN_TOP]
    files += [p for p in source_list() if p.relative_to(ROOT).parts[0] in PLUGIN_DIRS]
    return sorted(set(files))

def write_zip(dest:Path, files:list[Path], prefix=''):
    dest.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(dest,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in files:
            zi=zipfile.ZipInfo(prefix+p.relative_to(ROOT).as_posix(),date_time=(2026,11,15,0,0,0))
            zi.compress_type=zipfile.ZIP_DEFLATED
            zi.external_attr=(0o644<<16)
            z.writestr(zi,p.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)

def build(out:Path):
    from verify_repo import check
    failures=check()
    if failures:raise RuntimeError('Source verification failed: '+'; '.join(failures))
    out=out.resolve()
    f=out/(PREFIX+'_FULL_SOURCE.zip')
    p=out/(PREFIX+'_PORTABLE_INSTALL.zip')
    # The source has a containing folder. The portable archive has installer at root.
    write_zip(f,source_list(),f'{PROJECT}-v{VERSION}/')
    write_zip(p,portable_list())
    print('FULL SOURCE:',f,'\nPORTABLE:',p)

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=ROOT/'dist')
    args=parser.parse_args()
    build(args.output)
