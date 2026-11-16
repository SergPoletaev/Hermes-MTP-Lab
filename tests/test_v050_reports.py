"""v0.5.0 regression guard: self-contained outputs and deterministic settings."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('mtp_v050_core',ROOT/'dashboard'/'bench_core.py')
core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core)

class ReportProtocolTests(unittest.TestCase):
    def test_fixed_vision_report_includes_reference_and_all_inputs(self):
        with tempfile.TemporaryDirectory() as temp:
            model={'id':'Demo','mtp_kind':'external','has_mmproj':True,'model_path':'','mtp_head':'','mmproj':''}
            task=next(t for t in core.TASKS if t['id']=='grounding')
            rows=[]
            for phase in ('OFF','ON'):
                rows.append({'phase':phase,'trial':1,'replica':1,'model_id':'Demo',
                    'task':'grounding','group':'Распознавание деталей',
                    'valid':True,'token_limit':core.token_budget(task,32768),
                    'decode_tps':20.,'elapsed':4.,'drafted':12 if phase=='ON' else 0,
                    'accepted':10 if phase=='ON' else 0,'quality_status':'manual_review',
                    'quality':{'status':'manual_review'},'tokens':80,'decode_seconds':4.})
            config={'ctx':'32768','kv_k':'q8_0','kv_v':'q8_0','flash':'on',
                    'batch':'','ubatch':'','mmproj':True,'gpu_layers':None,'mtp':False}
            out=core.write_report(Path(temp),rows,[],model,True,
                                  {'OFF':config,'ON':{**config,'mtp':True}},32768,
                                  [],[],'off',[task])
            protocol=json.loads((Path(temp)/'protocol.json').read_text())
            compare=json.loads((Path(temp)/'comparability.json').read_text())
            self.assertEqual(out['comparability']['status'],'uncertain')
            self.assertEqual(compare['differences'],{})
            self.assertEqual(compare['unequal_caps'],0)
            self.assertTrue(protocol['fixed_token_caps'])
            self.assertFalse(protocol['adaptive_retries'])
            self.assertEqual(protocol['tasks'][0]['prompt'],task['prompt'])
            self.assertEqual(protocol['reference_image']['path'],'assets/benchmark_scene.jpg')
            original=(ROOT/'data'/'benchmark_scene.jpg').read_bytes()
            copy=(Path(temp)/'assets/benchmark_scene.jpg').read_bytes()
            self.assertEqual(original,copy)
            self.assertEqual(protocol['reference_image']['sha256'],hashlib.sha256(original).hexdigest())
            required={'summary.md','results.json','results.csv','answers.jsonl',
                      'task_summary.json','hardware.json','comparisons.json',
                      'comparability.json','protocol.json','assets/benchmark_scene.jpg'}
            found={p.relative_to(temp).as_posix() for p in Path(temp).rglob('*') if p.is_file()}
            self.assertEqual(found,required)
            self.assertIn('Launch comparability: uncertain',(Path(temp)/'summary.md').read_text())
    def test_no_vision_reference_when_not_needed(self):
        with tempfile.TemporaryDirectory() as temp:
            task=next(t for t in core.TASKS if t['id']=='network')
            core.write_report(Path(temp),[],[],{'id':'Demo','has_mmproj':False},True,{},32768,[],[],'native',[task])
            protocol=json.loads((Path(temp)/'protocol.json').read_text())
            self.assertEqual(protocol['reasoning_mode'],'native')
            self.assertIsNone(protocol['reference_image'])
            self.assertFalse((Path(temp)/'assets').exists())

if __name__=='__main__':unittest.main()
