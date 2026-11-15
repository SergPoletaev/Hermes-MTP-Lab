import importlib.util,json,sys,tempfile,time,types,unittest
from pathlib import Path
from unittest.mock import patch
p=Path(__file__).resolve().parents[1]/'dashboard'/'plugin_api.py'
s=importlib.util.spec_from_file_location('mtp_api_test',p)
api=importlib.util.module_from_spec(s);s.loader.exec_module(api)
class TestStatus(unittest.TestCase):
    def env(self,root):
        assets=root/'assets';assets.mkdir()
        preset=root/'presets.ini';preset.write_text('[General-Q4]\nmodel = /general.gguf\nctx-size = 8192\nspec-type = draft-mtp\n')
        from unittest.mock import MagicMock
        sup=types.SimpleNamespace(proc=types.SimpleNamespace(poll=lambda:None),preset_path=preset,primary_model='General-Q4')
        boot=types.ModuleType('hermes_cli.local_runtime.bootstrap');boot.assets_dir=lambda:assets
        local=types.ModuleType('hermes_cli.local_runtime');local.bootstrap=boot
        hermes=types.ModuleType('hermes_cli');hermes.local_runtime=local
        return {'hermes_cli':hermes,'hermes_cli.local_runtime':local,'hermes_cli.local_runtime.bootstrap':boot},(sup,preset,assets/'model-companions.json',api.bench.ms.model_specs(preset,assets/'model-companions.json'))
    def test_current_marker_not_a_crash(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);modules,environment=self.env(root)
            (root/'assets'/'.mtp-lab-pending.json').write_text(json.dumps({'schema':2,'model':'General-Q4','backup':'backup'}))
            with patch.dict(sys.modules,modules),patch.object(api.bench,'get_model_environment',return_value=environment),patch.object(api.bench.STATE,'read',return_value={'state':'running','step_kind':'loading','run_started_at':time.time()-10,'stage_started_at':time.time()-2}):
                result=api.status()
            self.assertFalse(result['recovery_needed']);self.assertEqual(result['model'],'General-Q4')
            self.assertEqual(result['tasks_per_phase'],4)
    def test_orphan_marker_reported(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);modules,environment=self.env(root)
            (root/'assets'/'.mtp-lab-pending.json').write_text(json.dumps({'schema':2,'model':'General-Q4'}))
            with patch.dict(sys.modules,modules),patch.object(api.bench,'get_model_environment',return_value=environment),patch.object(api.bench.STATE,'read',return_value={'state':'idle'}):
                self.assertTrue(api.status()['recovery_needed'])
    def test_progress_resets_counters(self):
        state=api.bench.BenchmarkState();state.update(live_port=12345,live_baseline=20)
        state.stage('loading','Load',phase='OFF')
        self.assertIsNone(state.read()['live_port'])
if __name__=='__main__':unittest.main()
