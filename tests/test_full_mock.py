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
            self.assertEqual(result['done'],16)
            self.assertTrue(all(row['valid'] for row in result['rows']),result['rows'])
            self.assertTrue(Path(result['report_path'],'summary.md').exists())
            self.assertTrue(Path(result['report_path'],'comparisons.json').exists())
            self.assertTrue(Path(result['report_path'],'answers.jsonl').exists())
            self.assertEqual(result['parity']['OFF/OFF']['pairs'],4)
            self.assertEqual(result['parity']['ON/ON']['pairs'],4)
            self.assertEqual(json.loads(manifest.read_text())['models']['Different-Model-Q6_K']['enable_mtp'],True)
    def test_three_cycles_reverse_phase_order_and_parity(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);(root/'Desktop').mkdir();assets=root/'assets';assets.mkdir()
            head=assets/'head.gguf';head.write_bytes(b'GGUFtest')
            native='[Any-Model]\nmodel = /any.gguf\nctx-size = 4096\n'
            preset=root/'presets.ini';preset.write_text(native)
            manifest=assets/'model-companions.json';manifest.write_text(json.dumps({'version':1,'models':{'Any-Model':{'mtp_head':str(head)}}}))
            model=core.ms.model_specs(preset,manifest)[0]
            class RecordingSup(Sup):
                def __init__(self,path):super().__init__(path);self.phases=[]
                def reload_presets(self):
                    super().reload_presets();self.phases.append(self.phase)
            sup=RecordingSup(preset)
            boot=types.ModuleType('hermes_cli.local_runtime.bootstrap');boot.assets_dir=lambda:assets
            local=types.ModuleType('hermes_cli.local_runtime');local.bootstrap=boot
            hermes=types.ModuleType('hermes_cli');hermes.local_runtime=local
            def route(*args,**kwargs):
                text=({'red':380,'blue':203,'green':206,'total':789} if args[2].get('id')=='structured' else {})
                visible=json.dumps(text) if text else 'Identical visible response.'
                return {'elapsed':3,'usage':{'completion_tokens':100},'timings':{},'chars':len(visible),
                        'visible':visible,'reasoning':'phase '+sup.phase,'finish_reason':'stop',
                        'output_sha256':'mock-digest'}
            def child(sup,model):
                return {'pid':11,'port':42,'mtp':sup.phase=='ON','ctx':'4096','kv_k':'q8_0','kv_v':'q8_0',
                        'flash':'on','batch':'1024','ubatch':'512','mmproj':False,'gpu_layers':'12'}
            meter=[0]
            def metrics(_):
                meter[0]+=1
                n=meter[0]//2
                return {'tokens':n*100,'decode_seconds':n*2,'drafted':n*100 if sup.phase=='ON' else 0,
                        'accepted':n*80 if sup.phase=='ON' else 0}
            core.STATE.update(state='running',done=0,rows=[],error=None)
            with patch.dict(sys.modules,{'hermes_cli':hermes,'hermes_cli.local_runtime':local,'hermes_cli.local_runtime.bootstrap':boot}),\
                 patch.object(core,'ensure_owned_idle',return_value=sup),\
                 patch.object(core,'get_model_environment',return_value=(sup,preset,manifest,[model])),\
                 patch.object(core,'route_request',side_effect=route),\
                 patch.object(core,'child_info',side_effect=child),\
                 patch.object(core,'child_metrics',side_effect=metrics),\
                 patch.object(core.hd,'snapshot',return_value={'gpu_source':'unavailable'}),\
                 patch.object(core.qe,'docker_ready',return_value=(False,'docker_unavailable')),\
                 patch.object(core.Path,'home',return_value=root):
                core.STATE.cancel.clear();core._run('Any-Model',3)
                result=core.STATE.read()
            self.assertTrue(result['restored'],result.get('error'))
            self.assertEqual(result['done'],48)
            self.assertEqual(sup.phases[:6],['OFF','ON','ON','OFF','OFF','ON'])
            self.assertEqual(preset.read_text(),native)
            self.assertEqual(result['parity']['OFF/OFF']['same_visible'],12)
            self.assertEqual(result['parity']['ON/ON']['same_visible'],12)
            self.assertEqual(result['parity']['OFF/ON']['same_visible'],24)
            self.assertEqual(result['parity']['OFF/ON']['same_reasoning'],0)
            self.assertGreater(result['quality_counts']['pass'],0)
            self.assertTrue(Path(result['report_path'],'task_summary.json').exists())
if __name__=='__main__':unittest.main()
