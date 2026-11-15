#!/usr/bin/env python3
"""Offline, non-mutating sanity checks of the public Hermes MTP Lab sources."""
from __future__ import annotations
from pathlib import Path
import re
import sys
ROOT = Path(__file__).resolve().parents[1]
VERSION = '0.3.3'
EXPECT = [
    '.gitignore', '.gitattributes', '.github/workflows/ci.yml', 'README.md', 'docs/assets/mtp-lab-dashboard.png',
    'LICENSE', 'SECURITY.md', 'CONTRIBUTING.md', 'CHANGELOG.md',
    'RELEASE_NOTES.md', 'requirements-ci.txt',
    'Install-Hermes-MTP-Lab.cmd', 'Install-Hermes-MTP-Lab.ps1',
    'plugin.yaml', '__init__.py',
    'desktop/plugin.js', 'dashboard/manifest.json',
    'dashboard/plugin_api.py', 'dashboard/bench_core.py', 'dashboard/model_support.py',
    'data/benchmark_scene.jpg',
    'tests/test_bench_core.py', 'tests/test_companion_api.py',
    'tests/test_desktop_registration.cjs',
    'tests/test_full_mock.py',
    'tests/test_progress_status.py', 'tests/test_repo_layout.py',
    'tests/test_repo_completeness.py',
    'docs/ARCHITECTURE.md', 'docs/BENCHMARK_METHODOLOGY.md',
    'docs/EXAMPLE_RESULTS_2026-11-15.md',
    'tools/verify_repo.py', 'tools/package_release.py', 'tools/check_dist.py'
]

def check():
    problems = []
    for f in EXPECT:
        p = ROOT/f
        if not p.is_file():problems.append(f'Missing public file: {f}')
    if problems:return problems
    yaml = (ROOT/'plugin.yaml').read_text(encoding='utf-8')
    m = re.search(r'^version:\s*[\'"]?([^\s\'"]+)', yaml, re.M)
    if not m or m.group(1)!=VERSION:problems.append('Plugin version does not match v'+VERSION)
    texts = [
        ('Install-Hermes-MTP-Lab.cmd', r'v'+VERSION),
        ('Install-Hermes-MTP-Lab.ps1', r'v'+VERSION),
        ('README.md', VERSION), ('CHANGELOG.md', VERSION),
        ('RELEASE_NOTES.md', VERSION), ('desktop/plugin.js', 'v'+VERSION)
    ]
    for f,needle in texts:
        if needle not in (ROOT/f).read_text(encoding='utf-8-sig'):
            problems.append(f'Version marker missing from {f}: {needle}')
    if (ROOT/'README_RU.md').exists():problems.append('README_RU.md must not exist: use the single four-language README.md')
    # Publishing helpers are owner-side tools, never part of public source or CI.
    forbidden_public = ('Publish-Hermes-MTP-Lab.cmd', 'Publish-Hermes-MTP-Lab.ps1', 'docs/PUBLISH_WITH_GITHUB_DESKTOP_RU.md')
    for private_path in forbidden_public:
        if (ROOT/private_path).exists():
            problems.append('Owner-side publishing file leaked into the public repository: '+private_path)
    for public_text in ('README.md', 'RELEASE_NOTES.md', 'CHANGELOG.md', 'SECURITY.md', 'docs/ARCHITECTURE.md', '.github/workflows/ci.yml'):
        if 'Publish-Hermes-MTP-Lab' in (ROOT/public_text).read_text(encoding='utf-8-sig'):
            problems.append('Public repository still references owner-side publishing script: '+public_text)
    attrs=(ROOT/'.gitattributes').read_text(encoding='utf-8')
    for rule in ('* text=auto eol=lf', '*.cmd text eol=crlf', '*.png binary', '*.jpg binary'):
        if rule not in attrs:
            problems.append('Missing cross-platform Git EOL rule: '+rule)
    if (ROOT/'hermes-mtp-lab').exists():
        problems.append('Obsolete nested plugin: root plugin.yaml and desktop/plugin.js are required for plain Git installation')
    if (ROOT/'BUILD-MANIFEST.json').exists():
        problems.append('Obsolete BUILD-MANIFEST.json: remove manual source checksum tracking')
    if 'fastapi==0.128.2' not in (ROOT/'requirements-ci.txt').read_text(encoding='utf-8'):
        problems.append('FastAPI test dependency missing: requirements-ci.txt')
    if 'httpx==0.28.1' not in (ROOT/'requirements-ci.txt').read_text(encoding='utf-8'):
        problems.append('HTTPX TestClient dependency missing: requirements-ci.txt')
    if 'python -m pip install -r requirements-ci.txt' not in (ROOT/'.github/workflows/ci.yml').read_text(encoding='utf-8'):
        problems.append('CI does not install the Python API test dependencies')
    readme=(ROOT/'README.md').read_text(encoding='utf-8')
    anchors=['<a id="ru"></a>','<a id="en"></a>','<a id="zh"></a>','<a id="hi"></a>']
    if any(marker not in readme for marker in anchors) or [readme.find(marker) for marker in anchors]!=sorted(readme.find(marker) for marker in anchors):
        problems.append('README must contain RU, EN, ZH and Hindi sections in that order')
    if 'docs/assets/mtp-lab-dashboard.png' not in readme:problems.append('README dashboard screenshot is missing')
    method=(ROOT/'docs/BENCHMARK_METHODOLOGY.md').read_text(encoding='utf-8')
    if 'four text tasks' not in method or 'six tasks' not in method or 'user-selected MTP-compatible' not in method:
        problems.append('Methodology must describe the generic 4/6 workload selection')
    if 'Only the compatible local Gemma 4 model is targeted' in method:
        problems.append('Obsolete model-specific restriction in methodology')
    screen=ROOT/'docs/assets/mtp-lab-dashboard.png'
    if not screen.exists() or screen.read_bytes()[:8]!=b'\x89PNG\r\n\x1a\n':problems.append('Dashboard screenshot missing or not PNG')
    js=(ROOT/'desktop/plugin.js').read_text(encoding='utf-8')
    for required in ('usePluginI18n','ctx.i18n.register(STRINGS)',"const PREF_KEY", 'languageAuto:', 'languageEn:', 'languageRu:', 'v0.3.3'):
        if required not in js:problems.append('UI translation/persistence check failed: '+required)
    # Root layout is mandatory: Hermes Install from Git must discover both halves.
    if not (ROOT/'plugin.yaml').is_file() or not (ROOT/'desktop/plugin.js').is_file():
        problems.append('Plain Git install incompatible: plugin.yaml and desktop/plugin.js must be at repository root')
    # No per-file SHA manifest: source edits must not require manual checksum maintenance.
    img=ROOT/'data/benchmark_scene.jpg'
    if img.stat().st_size < 10000 or img.read_bytes()[:3]!=b'\xff\xd8\xff':
        problems.append('Benchmark JPG absent/invalid')
    allowed=set(EXPECT)
    for p in ROOT.rglob('*'):
        if not p.is_file() or any(x in p.parts for x in ('__pycache__','dist','.git')):continue
        rel=p.relative_to(ROOT).as_posix()
        if rel not in allowed and not any(x in p.relative_to(ROOT).parts for x in ('build', 'node_modules', '.pytest_cache')) and p.suffix not in ('.pyc', '.pyo', '.zip'):
            problems.append('Unreviewed file would enter the source tree: '+rel)
        if p.name in ('config.yaml','model-companions.json','server.json','.env'):
            problems.append('Sensitive machine-specific file in tree: '+rel)
        if p.suffix.lower() in ('.gguf','.safetensors','.key','.pem','.p12','.pfx'):
            problems.append('Unexpected model/secret file in public tree: '+rel)
    return problems

if __name__=='__main__':
    failures=check()
    if failures:
        for f in failures:print('ERROR:',f)
        sys.exit(1)
    print('PASS: source structure, Git line endings, versions, image, tests prerequisites and privacy checks (no manual hashes)')
