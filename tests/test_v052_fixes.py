"""v0.5.2 regression guard: atomic backups, adaptive timeouts, BOM, pruning, graceful reports."""
import importlib.util
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
DASH = ROOT / 'dashboard'


def load_core_from(directory: Path):
    """Load an isolated bench_core copy (with its sibling modules) from `directory`."""
    spec = importlib.util.spec_from_file_location('mtp_core_v052_' + directory.name, directory / 'bench_core.py')
    core = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(core)
    return core


core = load_core_from(DASH)
ms = core.ms


class RequestTimeoutTests(unittest.TestCase):
    def test_base_policy_without_probe(self):
        self.assertEqual(core.request_timeout(768), 691)
        self.assertEqual(core.request_timeout(100), 480)
        self.assertEqual(core.request_timeout(1536), 1382)

    def test_probe_derives_longer_timeout_for_slow_models(self):
        probe = {'elapsed': 100.0, 'usage': {'completion_tokens': 50}}
        self.assertEqual(core.request_timeout(768, probe), 3252)

    def test_upper_bound_is_7200(self):
        probe = {'elapsed': 2000.0, 'usage': {'completion_tokens': 10}}
        self.assertEqual(core.request_timeout(768, probe), 7200)

    def test_fast_probe_never_shrinks_below_base(self):
        probe = {'elapsed': 0.01, 'usage': {'completion_tokens': 100}}
        self.assertEqual(core.request_timeout(768, probe), 691)

    def test_invalid_probe_falls_back_to_base(self):
        for bad in (None, {}, {'elapsed': 0, 'usage': {}}, {'elapsed': 'x', 'usage': {'completion_tokens': 10}}):
            self.assertEqual(core.request_timeout(768, bad), 691)

    def test_route_request_accepts_explicit_timeout(self):
        class Fake:
            base_url = 'http://127.0.0.1:18434/v1'
            api_key = 'not-real'
        seen = []

        def fake_http(url, key, body, timeout=480):
            seen.append(timeout)
            return {'usage': {'completion_tokens': 5}, 'choices': [{'finish_reason': 'stop', 'message': {'content': 'OK'}}]}
        with patch.object(core, 'http_json', side_effect=fake_http):
            core.route_request(Fake(), 'Demo', {'prompt': 'x', 'image': False}, None, 128,
                               reasoning_mode='off', timeout=777)
        self.assertEqual(seen, [777])


class BomPreservationTests(unittest.TestCase):
    def test_apply_phase_keeps_bom_and_restore_is_exact(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            head = root / 'head.gguf'
            head.write_bytes(b'GGUFmock')
            original = b'\xef\xbb\xbf[Selected]\r\nmodel = /selected.gguf\r\nctx-size = 8192\r\n'
            preset = root / 'presets.ini'
            preset.write_bytes(original)
            model = {'id': 'Selected', 'mtp_head': str(head), 'mtp_kind': 'external',
                     'mtp_supported': True, 'has_mmproj': False, 'draft_n': 3}

            class Sup:
                def is_idle(self):
                    return True

                def reload_presets(self):
                    pass
            core.apply_phase(Sup(), preset, original, model, True, 4096)
            self.assertTrue(preset.read_bytes().startswith(b'\xef\xbb\xbf'))
            self.assertIn(b'spec-type = draft-mtp', preset.read_bytes())
            core.restore_presets(Sup(), preset, original)
            self.assertEqual(preset.read_bytes(), original)

    def test_apply_phase_stays_bomless_without_native_bom(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            head = root / 'head.gguf'
            head.write_bytes(b'GGUFmock')
            original = b'[Selected]\nmodel = /selected.gguf\nctx-size = 8192\n'
            preset = root / 'presets.ini'
            preset.write_bytes(original)
            model = {'id': 'Selected', 'mtp_head': str(head), 'mtp_kind': 'external',
                     'mtp_supported': True, 'has_mmproj': False, 'draft_n': 3}

            class Sup:
                def is_idle(self):
                    return True

                def reload_presets(self):
                    pass
            core.apply_phase(Sup(), preset, original, model, True, 4096)
            self.assertFalse(preset.read_bytes().startswith(b'\xef\xbb\xbf'))


class PruneBackupTests(unittest.TestCase):
    def test_only_newest_five_backups_are_kept(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            names = [f'presets.ini.mtp-lab-backup-20260101-00000{i}-00000{i}' for i in range(8)]
            for name in names:
                (root / name).write_bytes(b'backup')
            (root / 'unrelated.txt').write_bytes(b'keep me')
            removed = ms.prune_backups(root, 'presets.ini.mtp-lab-backup-*')
            self.assertEqual(len(removed), 3)
            self.assertTrue((root / names[-1]).is_file())
            self.assertFalse((root / names[0]).is_file())
            self.assertTrue((root / 'unrelated.txt').is_file())

    def test_pruning_never_touches_fewer_than_five(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for i in range(3):
                (root / f'presets.ini.mtp-lab-backup-20260101-00000{i}-00000{i}').write_bytes(b'x')
            self.assertEqual(ms.prune_backups(root, 'presets.ini.mtp-lab-backup-*'), [])

    def test_companion_backup_is_atomic_and_content_exact(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            head = root / 'mtp.gguf'
            head.write_bytes(b'GGUFhead')
            comp = root / 'model-companions.json'
            original = json.dumps({'version': 1, 'models': {'X': {'mtp_head': 'old.gguf'}}})
            comp.write_text(original)
            ms.set_companion(comp, 'X', {'X'}, str(head), '')
            backups = list(root.glob('model-companions.json.mtp-lab-config-*'))
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_text(), original)


class CandidateCacheTests(unittest.TestCase):
    def test_candidates_refresh_when_folder_changes(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            main = root / 'model.gguf'
            main.write_bytes(b'GGUFmain')
            proj = root / 'model-mmproj.gguf'
            proj.write_bytes(b'GGUFproj')
            os.utime(proj, (1_700_000_000, 1_700_000_000))
            first = ms.projector_candidates(str(main))
            self.assertEqual(len(first), 1)
            second = ms.projector_candidates(str(main))
            self.assertEqual(second, first)  # cached copy is identical
            extra = root / 'model-mmproj-v2.gguf'
            extra.write_bytes(b'GGUFproj2')
            os.utime(extra, (1_700_000_100, 1_700_000_100))
            os.utime(root, (1_700_000_100, 1_700_000_100))
            third = ms.projector_candidates(str(main))
            self.assertEqual(len(third), 2)  # fingerprint invalidated by folder change

    def test_cache_is_per_directory(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            main = root / 'model.gguf'
            main.write_bytes(b'GGUFmain')
            other = root / 'others'
            other.mkdir()
            (other / 'model-mmproj.gguf').write_bytes(b'GGUFproj')
            os.utime(other, (1_700_000_000, 1_700_000_000))
            self.assertEqual(ms.projector_candidates(str(main)), [])
            self.assertEqual(len(ms.projector_candidates(str(main), str(other))), 1)


class SandboxHarnessTests(unittest.TestCase):
    def test_harness_reads_whole_payload_with_cap(self):
        harness = core.qe.CODE_HARNESS
        self.assertIn('sys.stdin.read()', harness)
        self.assertIn('payload_too_large', harness)
        self.assertNotIn('sys.stdin.read(25000)', harness)


class GracefulImageReportTests(unittest.TestCase):
    def test_missing_reference_image_degrades_report_not_destroys_it(self):
        with tempfile.TemporaryDirectory() as d:
            shutil.copytree(DASH, Path(d) / 'isolated', dirs_exist_ok=True)
            isolated = load_core_from(Path(d) / 'isolated')
            model = {'id': 'Demo', 'mtp_kind': 'embedded', 'has_mmproj': True, 'model_path': '',
                    'mtp_head': '', 'mmproj': ''}
            task = next(t for t in isolated.TASKS if t['id'] == 'grounding')
            rows = [{'phase': 'OFF', 'trial': 1, 'replica': 1, 'model_id': 'Demo',
                     'task': 'grounding', 'group': 'Распознавание деталей', 'valid': True,
                     'token_limit': 768, 'decode_tps': 20., 'elapsed': 4., 'drafted': 0,
                     'accepted': 0, 'quality_status': 'manual_review',
                     'quality': {'status': 'manual_review'}, 'tokens': 80, 'decode_seconds': 4.}]
            out_root = Path(d) / 'report'
            result = isolated.write_report(out_root, rows, ['note'], model, True, {}, 32768,
                                           [], [], 'off', [task])
            protocol = json.loads((out_root / 'protocol.json').read_text(encoding='utf-8'))
            self.assertIsNone(protocol['reference_image'])
            self.assertIsNotNone(protocol['reference_image_warning'])
            self.assertEqual(protocol['request_timeout_policy'], 'warmup_derived_bounded_480_7200')
            summary = (out_root / 'summary.md').read_text(encoding='utf-8')
            self.assertIn('Bundled benchmark image missing', summary)
            self.assertFalse((out_root / 'assets').exists())
            self.assertIn('summary', result)

    def test_run_fails_fast_when_vision_image_is_missing(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            shutil.copytree(DASH, Path(d) / 'isolated', dirs_exist_ok=True)
            isolated = load_core_from(Path(d) / 'isolated')
            import types
            assets = root / 'assets'
            assets.mkdir()
            head = assets / 'mtp-head.gguf'
            head.write_bytes(b'GGUFmock')
            proj = assets / 'mmproj.gguf'
            proj.write_bytes(b'GGUFproj')
            native = '[Vision-Model]\nmodel = /vision.gguf\nctx-size = 8192\n'
            preset = root / 'presets.ini'
            preset.write_text(native)
            manifest = assets / 'model-companions.json'
            manifest.write_text(json.dumps({'version': 1, 'models': {'Vision-Model': {
                'mtp_head': str(head), 'mmproj': str(proj)}}}))
            model = isolated.ms.model_specs(preset, manifest)[0]
            self.assertTrue(model['has_mmproj'])

            class Sup:
                preset_path = preset

                def is_idle(self):
                    return True

                def reload_presets(self):
                    pass

                def ensure_model_ready(self, mid):
                    return True
            boot = types.ModuleType('hermes_cli.local_runtime.bootstrap')
            boot.assets_dir = lambda: assets
            local = types.ModuleType('hermes_cli.local_runtime')
            local.bootstrap = boot
            hermes = types.ModuleType('hermes_cli')
            hermes.local_runtime = local
            import sys
            isolated.STATE.update(state='running', done=0, total=4, rows=[], error=None,
                                   summary=[], report_path=None)
            with patch.dict(sys.modules, {'hermes_cli': hermes, 'hermes_cli.local_runtime': local,
                                          'hermes_cli.local_runtime.bootstrap': boot}), \
                 patch.object(isolated, 'ensure_owned_idle', return_value=Sup()), \
                 patch.object(isolated, 'get_model_environment', return_value=(Sup(), preset, manifest, [model])), \
                 patch.object(isolated.Path, 'home', return_value=root):
                isolated.STATE.cancel.clear()
                isolated._run('Vision-Model', 1)
                state = isolated.STATE.read()
            self.assertIn('Bundled benchmark image is missing', state.get('error') or '')
            self.assertTrue(state.get('restored'))


class AtomicPresetBackupTests(unittest.TestCase):
    def test_run_backup_roundtrip_and_prune_notes(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'Desktop').mkdir()
            assets = root / 'assets'
            assets.mkdir()
            head = assets / 'mtp-head.gguf'
            head.write_bytes(b'GGUFmock')
            native = '[Model-Q5]\nmodel = /model.gguf\nctx-size = 8192\n'
            preset = root / 'presets.ini'
            preset.write_text(native)
            manifest = assets / 'model-companions.json'
            manifest.write_text(json.dumps({'version': 1, 'models': {'Model-Q5': {'mtp_head': str(head)}}}))
            model = ms.model_specs(preset, manifest)[0]

            class Sup:
                preset_path = preset

                def is_idle(self):
                    return True

                def reload_presets(self):
                    pass

                def ensure_model_ready(self, mid):
                    return True
            import types
            import sys
            boot = types.ModuleType('hermes_cli.local_runtime.bootstrap')
            boot.assets_dir = lambda: assets
            local = types.ModuleType('hermes_cli.local_runtime')
            local.bootstrap = boot
            hermes = types.ModuleType('hermes_cli')
            hermes.local_runtime = local

            def route(*args, **kwargs):
                return {'elapsed': 2, 'usage': {'completion_tokens': 100}, 'timings': {},
                        'chars': 400, 'output_sha256': 'deadbeef', 'visible': 'x' * 50,
                        'reasoning': '', 'finish_reason': 'stop',
                        'visible_sha256': 'a', 'reasoning_sha256': 'b'}

            def child(sup, model):
                return {'pid': 11, 'port': 42, 'mtp': True, 'ctx': '32768', 'kv_k': 'q8_0',
                        'kv_v': 'q8_0', 'flash': 'on', 'batch': '1024', 'ubatch': '512',
                        'mmproj': False, 'draft_n': '3'}
            meter = [0]

            def metrics(_):
                meter[0] += 1
                n = meter[0] // 2
                return {'tokens': n * 100, 'decode_seconds': n * 2,
                        'drafted': n * 120, 'accepted': n * 100,
                        'prompt_tokens': n * 20, 'prompt_seconds': n * .4}
            core.STATE.update(state='running', done=0, total=16, rows=[], error=None,
                              summary=[], report_path=None)
            with patch.dict(sys.modules, {'hermes_cli': hermes, 'hermes_cli.local_runtime': local,
                                          'hermes_cli.local_runtime.bootstrap': boot}), \
                 patch.object(core, 'ensure_owned_idle', return_value=Sup()), \
                 patch.object(core, 'get_model_environment', return_value=(Sup(), preset, manifest, [model])), \
                 patch.object(core, 'route_request', side_effect=route), \
                 patch.object(core, 'child_info', side_effect=child), \
                 patch.object(core, 'child_metrics', side_effect=metrics), \
                 patch.object(core.hd, 'snapshot', return_value={'gpu_source': 'unavailable'}), \
                 patch.object(core.qe, 'docker_ready', return_value=(False, 'docker_unavailable')), \
                 patch.object(core.Path, 'home', return_value=root):
                core.STATE.cancel.clear()
                core._run('Model-Q5', 1)
                state = core.STATE.read()
            self.assertTrue(state['restored'], state.get('error'))
            backups = list(preset.parent.glob(preset.name + '.mtp-lab-backup-*'))
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_bytes(), native.encode('utf-8'))
            self.assertEqual(preset.read_text(), native)
            self.assertFalse((assets / '.mtp-lab-pending.json').exists())


if __name__ == '__main__':
    unittest.main()
