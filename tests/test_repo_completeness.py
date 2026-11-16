"""Checks that publication is complete and not only a partial CI hotfix."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
import unittest

ROOT = Path(__file__).resolve().parents[1]


class WholeRepositoryTests(unittest.TestCase):
    def test_every_public_file_is_known_and_nonempty(self):
        import sys
        sys.path.insert(0, str(ROOT / 'tools'))
        try:
            from verify_repo import EXPECT
        finally:
            sys.path.remove(str(ROOT / 'tools'))
        actual = {
            p.relative_to(ROOT).as_posix()
            for p in ROOT.rglob('*')
            if p.is_file() and not any(x in p.relative_to(ROOT).parts
                for x in ('.git', 'dist', '__pycache__', '.pytest_cache', 'node_modules'))
            and p.suffix not in ('.pyc', '.pyo', '.zip')
        }
        self.assertEqual(actual, set(EXPECT), 'Release source has unreviewed or missing files')
        for filename in EXPECT:
            with self.subTest(file=filename):
                self.assertGreater((ROOT / filename).stat().st_size, 0)

    def test_text_utf8_assets_and_json(self):
        for p in ROOT.rglob('*'):
            if not p.is_file() or any(x in p.parts for x in ('dist', '__pycache__')):
                continue
            with self.subTest(path=p.relative_to(ROOT).as_posix()):
                if p.suffix in ('.md', '.py', '.js', '.cjs', '.txt', '.ps1', '.cmd', '.json', '.yaml', '.yml') or p.name in ('.gitignore', '.gitattributes', 'LICENSE'):
                    s = p.read_text(encoding='utf-8-sig')
                    self.assertNotIn('\x00', s)
                    if p.suffix == '.json':
                        json.loads(s)
                if p.suffix == '.png':
                    self.assertEqual(p.read_bytes()[:8], b'\x89PNG\r\n\x1a\n')
                if p.suffix in ('.jpg', '.jpeg'):
                    self.assertEqual(p.read_bytes()[:3], b'\xff\xd8\xff')

    def test_relative_markdown_links_exist(self):
        import re
        for doc in ROOT.rglob('*.md'):
            for target in re.findall(r'\]\(([^)]+)\)', doc.read_text(encoding='utf-8-sig')):
                if target.startswith(('https://', 'http://', '#', 'mailto:')):
                    continue
                file = target.split('#', 1)[0].split(' ', 1)[0]
                if file:
                    with self.subTest(doc=doc.name, target=target):
                        self.assertTrue((doc.parent / file).exists())

    def test_native_projector_is_resolved_beside_model(self):
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location('mtp_path_resolution', ROOT / 'dashboard' / 'model_support.py')
        ms = module_from_spec(spec); spec.loader.exec_module(ms)
        with TemporaryDirectory() as directory:
            root = Path(directory)
            models = root / 'models'; models.mkdir()
            assets = root / 'assets'; assets.mkdir()
            main = models / 'Gemma-v4-Q4.gguf'; main.write_bytes(b'GGUFmock')
            proj = models / 'mmproj-Gemma-v4.gguf'; proj.write_bytes(b'GGUFmock')
            preset = root / 'presets.ini'
            preset.write_text(f'[Gemma]\nmodel = {main}\nmmproj = {proj.name}\nctx-size = 8192\n')
            item = ms.model_specs(preset, assets / 'model-companions.json')[0]
            self.assertEqual(Path(item['mmproj']), proj)
            self.assertTrue(item['has_mmproj'])
            proj.write_bytes(b'NOT-GGUF')
            self.assertFalse(ms.model_specs(preset, assets / 'model-companions.json')[0]['has_mmproj'])
            proj.write_bytes(b'GGUFmock')
            # Explicit link is assets-relative, even if a model-side match exists.
            alt = assets / proj.name; alt.write_bytes(b'GGUFanother')
            (assets / 'model-companions.json').write_text(json.dumps({'version': 1, 'models': {'Gemma': {'mmproj': proj.name}}}))
            item = ms.model_specs(preset, assets / 'model-companions.json')[0]
            self.assertEqual(Path(item['mmproj']), alt)

    def test_native_relative_mtp_head_and_corrupt_head(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location('mtp_native_head', ROOT / 'dashboard' / 'model_support.py')
        ms = importlib.util.module_from_spec(spec); spec.loader.exec_module(ms)
        with TemporaryDirectory() as directory:
            root = Path(directory);folder=root/'models';folder.mkdir()
            main=folder/'AnyModel.gguf';main.write_bytes(b'GGUFbase')
            head=folder/'mtp-AnyModel.gguf';head.write_bytes(b'GGUFhead')
            preset=root/'presets.ini';preset.write_text(f'[Test]\nmodel = {main}\nspec-type = draft-mtp\nmodel-draft = {head.name}\nctx-size = 8192\n')
            model=ms.model_specs(preset,root/'assets'/'model-companions.json')[0]
            self.assertEqual(model['mtp_head'],str(head))
            self.assertTrue(model['mtp_supported'])
            head.write_bytes(b'CORRUPT')
            self.assertFalse(ms.model_specs(preset,root/'assets'/'model-companions.json')[0]['mtp_supported'])

    def test_second_benchmark_cannot_start_concurrently(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location('mtp_concurrent_test', ROOT / 'dashboard' / 'bench_core.py')
        core = importlib.util.module_from_spec(spec); spec.loader.exec_module(core)
        example = {'id': 'Model', 'has_mmproj': False, 'mtp_supported': True}
        class DeferredThread:
            def __init__(self, *args, **kwargs):
                pass
            def start(self):
                pass
        with patch.object(core, 'get_model_environment', return_value=(None, None, None, [example])), \
             patch.object(core.threading, 'Thread', DeferredThread):
            self.assertEqual(core.execute_benchmark('Model', 1), 16)
            with self.assertRaisesRegex(RuntimeError, 'already running'):
                core.execute_benchmark('Model', 1)

    def test_recovery_warning_does_not_invent_original_mtp_state(self):
        js = (ROOT / 'desktop' / 'plugin.js').read_text(encoding='utf-8')
        core = (ROOT / 'dashboard' / 'bench_core.py').read_text(encoding='utf-8')
        self.assertIn("'original':'draft-mtp'", core)
        self.assertIn("state.pending_original_mtp===false?'OFF':'—'", js)

    def test_owner_publish_tools_never_enter_public_source(self):
        forbidden = (
            'Publish-Hermes-MTP-Lab.cmd',
            'Publish-Hermes-MTP-Lab.ps1',
            'docs/PUBLISH_WITH_GITHUB_DESKTOP_RU.md',
        )
        for name in forbidden:
            with self.subTest(path=name):
                self.assertFalse((ROOT / name).exists())
        # The Windows job must validate the plugin installer, not a private owner-side script.
        workflow = (ROOT / '.github/workflows/ci.yml').read_text(encoding='utf-8')
        self.assertIn('Install-Hermes-MTP-Lab.ps1', workflow)
        self.assertNotIn('Publish-Hermes-MTP-Lab', workflow)
        verifier = (ROOT / 'tools/verify_repo.py').read_text(encoding='utf-8')
        self.assertIn('forbidden_public', verifier)

    def test_both_release_lists_exclude_publishers(self):
        import sys
        sys.path.insert(0, str(ROOT / 'tools'))
        try:
            from package_release import portable_list, source_list
            for files in (portable_list(), source_list()):
                self.assertTrue(files)
                self.assertFalse(any('Publish-Hermes-MTP-Lab' in str(path) for path in files))
                self.assertTrue(all(path.is_file() for path in files))
        finally:
            sys.path.remove(str(ROOT / 'tools'))

if __name__ == '__main__':
    unittest.main()
