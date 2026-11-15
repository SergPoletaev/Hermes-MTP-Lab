#!/usr/bin/env python3
"""Verify both release ZIPs by reading every entry and comparing to current source files.

No manifest, checksum updates, or manual SHA-256 maintenance are required.
ZIP CRC checks and byte-for-byte source comparisons are done automatically.
"""
from __future__ import annotations
from pathlib import Path
import argparse
import sys
import zipfile
from package_release import ROOT, PREFIX, PROJECT, VERSION, source_list, portable_list

SOURCE_ROOT=f'{PROJECT}-v{VERSION}/'


def check_zip(archive: Path, source_files: list[Path], prefix: str) -> None:
    if not archive.is_file():
        raise RuntimeError(f'Missing release file: {archive}')
    expected={prefix+f.relative_to(ROOT).as_posix():f for f in source_files}
    with zipfile.ZipFile(archive, 'r') as z:
        corrupt=z.testzip()
        if corrupt is not None:
            raise RuntimeError(f'ZIP damaged at {corrupt}: {archive}')
        names=z.namelist()
        if len(names)!=len(set(names)):
            raise RuntimeError(f'Duplicate ZIP entries: {archive}')
        missing=set(expected)-set(names)
        extra=set(names)-set(expected)
        if missing or extra:
            raise RuntimeError(f'{archive.name}: missing={sorted(missing)}, extra={sorted(extra)}')
        for name,src in expected.items():
            if z.read(name)!=src.read_bytes():
                raise RuntimeError(f'{archive.name}: packaged content differs from source: {name}')


def check(out: Path) -> None:
    f=out/(PREFIX+'_FULL_SOURCE.zip')
    p=out/(PREFIX+'_PORTABLE_INSTALL.zip')
    check_zip(f,source_list(),SOURCE_ROOT)
    check_zip(p,portable_list(),'')
    with zipfile.ZipFile(p) as z:
        if not {'plugin.yaml','__init__.py','desktop/plugin.js','dashboard/manifest.json','dashboard/plugin_api.py'}.issubset(z.namelist()):
            raise RuntimeError('Portable install is missing the root-level Hermes plugin layout')
        if any(n.startswith('hermes-mtp-lab/') for n in z.namelist()):
            raise RuntimeError('Obsolete nested plugin found in release package')
    print('PASS: both release ZIPs open and exactly match the current source files (no SHA manifest)')

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--directory',type=Path,required=True)
    try:
        check(parser.parse_args().directory)
    except Exception as exc:
        print('FAIL:',exc,file=sys.stderr)
        sys.exit(1)
