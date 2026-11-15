import importlib.util,json,sys,tempfile,types,unittest
from pathlib import Path
from unittest.mock import patch
p=Path(__file__).resolve().parents[1]/'dashboard'/'bench_core.py'
spec=importlib.util.spec_from_file_location('bench_mock_generic',p)
core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core)
class Sup:
    def __init__(self,path):self.preset_path=path;self.phase='ON';self.count=0
    def is_idle(self):return True
    def reload_presets(self):self.phase='ON' if 'spec-type = draft-mtp' in self.preset_path.read_text() else 'OFF'
    def ensure_model_ready(self,mid):return True
class TestFullMock(unittest.TestCase):
    def test_model_agnostic_recovery_and_text_only(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);(root/'Desktop').mkdir();assets=root/'assets';assets.mkdir()
            head=assets/'mtp-head.gguf';head.write_bytes(b'GGUFmock')
            native='[Different-Model-Q6_K]\nmodel = /different.gguf\nctx-size = 65536\ncache-type-k = q8_0\n'
            preset=root/'presets.ini';preset.write_text(native)
            manifest=assets/'model-companions.json';manifest.write_text(json.dumps({'version':1,'models':{'Different-Model-Q6_K':{'mtp_head':str(head),'enable_mtp':True}}}))
            model=core.ms.model_specs(preset,manifest)[0];sup=Sup(preset)
            boot=types.ModuleType('hermes_cli.local_runtime.bootstrap');boot.assets_dir=lambda:assets
            local=types.ModuleType('hermes_cli.local_runtime');local.bootstrap=boot
            hermes=types.ModuleType('hermes_cli');hermes.local_runtime=local
            def route(*args,**kwargs):
                sup.count+=1
                return {'elapsed':2,'usage':{'completion_tokens':100},'timings':{},'chars':400,'output_sha256':'deadbeef'}
            def child(sup,model):
                return {'pid':11,'port':42,'mtp':sup.phase=='ON','ctx':'32768','kv_k':'q8_0','kv_v':'q8_0',
                        'flash':'on','batch':'1024','ubatch':'512','mmproj':False,'draft_n':'3'}
            metric_call=[0]
            def metrics(_):
                # Each before/after metrics pair brackets one request.
                metric_call[0]+=1
                n=metric_call[0]//2
                return {'tokens':n*100,'decode_seconds':n*2,'drafted':n*120 if sup.phase=='ON' else 0,
                        'accepted':n*100 if sup.phase=='ON' else 0,'prompt_tokens':n*20,'prompt_seconds':n*.4}
            core.STATE.update(state='running',done=0,total=8,rows=[],error=None,summary=[],report_path=None)
            with patch.dict(sys.modules,{'hermes_cli':hermes,'hermes_cli.local_runtime':local,'hermes_cli.local_runtime.bootstrap':boot}),\
                 patch.object(core,'ensure_owned_idle',return_value=sup),\
                 patch.object(core,'get_model_environment',return_value=(sup,preset,manifest,[model])),\
                 patch.object(core,'route_request',side_effect=route),\
                 patch.object(core,'child_info',side_effect=child),\
                 patch.object(core,'child_metrics',side_effect=metrics),\
                 patch.object(core.Path,'home',return_value=root):
                core.STATE.cancel.clear();core._run('Different-Model-Q6_K',1);result=core.STATE.read()
            self.assertEqual(preset.read_text(),native)
            self.assertFalse((assets/'.mtp-lab-pending.json').exists())
            self.assertTrue(result['restored'])
            self.assertEqual(result['done'],8)
            self.assertTrue(all(row['valid'] for row in result['rows']),result['rows'])
            self.assertTrue(Path(result['report_path'],'summary.md').exists())
            self.assertEqual(json.loads(manifest.read_text())['models']['Different-Model-Q6_K']['enable_mtp'],True)
if __name__=='__main__':unittest.main()
