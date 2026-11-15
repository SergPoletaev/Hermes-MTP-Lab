import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

D=Path(__file__).resolve().parents[1]/'dashboard'
def load(name,filename):
    spec=importlib.util.spec_from_file_location(name,D/filename)
    obj=importlib.util.module_from_spec(spec);spec.loader.exec_module(obj)
    return obj
core=load('mtp_core_test','bench_core.py')
ms=core.ms
class ModelAgnosticTests(unittest.TestCase):
    def test_metrics(self):
        m=core.metrics_from_text('llamacpp:tokens_predicted_total 200\nllamacpp:spec_decode_num_draft_tokens_total{slot="1"} 100\nllamacpp:spec_decode_num_accepted_tokens_total 75\n')
        self.assertEqual(m['tokens'],200);self.assertEqual(m['accepted'],75)
    def test_deltas(self):
        self.assertEqual(core.diff_metrics({'tokens':10},{'tokens':40}),{'tokens':30})
    def test_model_listing_no_hardcoded_model(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'presets.ini'
            p.write_text('[Alpha-Q8_0]\nmodel = /alpha.gguf\nctx-size = 1024\n[Beta-Q4_K_M]\nmodel = /beta.gguf\nctx-size = 4096\n',encoding='utf-8')
            ids=[m['id'] for m in ms.models_from_presets(p)]
            self.assertEqual(ids,['Alpha-Q8_0','Beta-Q4_K_M'])
    def test_separate_mtp_head_and_optional_projector(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);head=root/'other-head.gguf';head.write_bytes(b'GGUFhello')
            preset=root/'presets.ini';preset.write_text('[Model-Q5]\nmodel = /model.gguf\nctx-size = 8192\n')
            comp=root/'model-companions.json';comp.write_text(json.dumps({'version':1,'models':{'Model-Q5':{'mtp_head':str(head),'enable_mtp':False}}}))
            model=ms.model_specs(preset,comp)[0]
            self.assertEqual(model['mtp_kind'],'external');self.assertTrue(model['mtp_supported']);self.assertFalse(model['has_mmproj'])
            off=ms.benchmark_presets(preset.read_text(),model,False,4096)
            on=ms.benchmark_presets(preset.read_text(),model,True,4096)
            self.assertIn('spec-type = none',off);self.assertNotIn('model-draft',off)
            self.assertIn('spec-type = draft-mtp',on);self.assertIn(str(head),on)
            self.assertIn('spec-draft-n-max = 3',on)
    def test_text_only_no_vision_requirement(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'presets.ini';path.write_text('[T]\nmodel = /t.gguf\nctx-size = 8192\nspec-type = draft-mtp\n')
            models=ms.model_specs(path,Path(d)/'model-companions.json')
            self.assertTrue(models[0]['embedded_mtp']);self.assertFalse(models[0]['has_mmproj'])
            self.assertEqual(len([t for t in core.TASKS if not t['image']]),4)
    def test_unconfirmed_mtp_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'presets.ini';path.write_text('[T]\nmodel = /t.gguf\nctx-size = 8192\n')
            models=ms.model_specs(path,Path(d)/'model-companions.json')
            with self.assertRaisesRegex(RuntimeError,'No compatible MTP'):
                core.select_spec(models,'T')
    def test_other_models_byte_for_byte_preserved(self):
        text='[A]\r\nmodel = /a.gguf\r\nctx-size = 2048\r\n[B]\r\nmodel = /b.gguf\r\nctx-size = 8192\r\n'
        out=ms.section_override(text,'B',{'ctx-size':'4096','spec-type':'draft-mtp'})
        self.assertTrue(out.startswith('[A]\r\nmodel = /a.gguf\r\nctx-size = 2048\r\n'))
        self.assertIn('ctx-size = 4096',out);self.assertIn('spec-type = draft-mtp',out)
    def test_duplicate_ini_model_rejected(self):
        with self.assertRaisesRegex(ValueError,'Duplicate'):
            ms.ini_sections('[A]\nx = 1\n[A]\nx = 2\n')
    def test_explicit_pairing_and_preserve_unrelated(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);head=root/'mtp.gguf';head.write_bytes(b'GGUFhead')
            comp=root/'model-companions.json'
            comp.write_text(json.dumps({'version':1,'models':{'Other':{'mtp_head':'other.gguf'}},'unrelated':{'keep':True}}))
            ms.set_companion(comp,'Quant-X',{'Quant-X'},str(head),'')
            data=json.loads(comp.read_text())
            self.assertEqual(data['models']['Quant-X']['mtp_head'],str(head));self.assertEqual(data['unrelated'],{'keep':True})
            self.assertEqual(data['models']['Other'],{'mtp_head':'other.gguf'})
            self.assertTrue(any(root.glob('model-companions.json.mtp-lab-config-*')))
    def test_invalid_companion_rejected_without_edit(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);comp=root/'model-companions.json'
            comp.write_text('{"version":1,"models":{}}')
            with self.assertRaisesRegex(RuntimeError,'existing GGUF'):
                ms.set_companion(comp,'X',{'X'},str(root/'notfound.gguf'),'')
            self.assertEqual(json.loads(comp.read_text()),{'version':1,'models':{}})
    def test_user_selection(self):
        models=[{'id':'A'},{'id':'B'}]
        self.assertIsNone(ms.choose_model(models,None,None))
        self.assertEqual(ms.choose_model(models,'B',None),'B')
        self.assertEqual(ms.choose_model(models,'Missing','A'),'A')
    def test_preset_reload_failure_rolls_back_original_bytes(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);head=root/'head.gguf';head.write_bytes(b'GGUFmock')
            preset=root/'presets.ini'
            original='[Other]\nmodel = /other.gguf\nctx-size = 2048\n[Selected]\nmodel = /selected.gguf\nctx-size = 8192\n'
            preset.write_text(original)
            model={'id':'Selected','mtp_head':str(head),'mtp_kind':'external','mtp_supported':True,'has_mmproj':False}
            class FailingSupervisor:
                def is_idle(self):return True
                def reload_presets(self):raise RuntimeError('Reload refused')
            with self.assertRaisesRegex(RuntimeError,'Reload refused'):
                core.apply_phase(FailingSupervisor(),preset,preset.read_bytes(),model,True,4096)
            self.assertEqual(preset.read_text(),original)
    def test_mtp_head_not_mistaken_for_dflash_draft(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'presets.ini';p.write_text('[Other]\nmodel = /other.gguf\nctx-size = 4096\nspec-type = draft-dflash\nmodel-draft = /dflash.gguf\n')
            model=ms.model_specs(p,Path(d)/'model-companions.json')[0]
            self.assertEqual(model['mtp_kind'],'unsupported')

    def test_status_summary(self):
        rows=[{'group':'Text','phase':'OFF','valid':True,'decode_tps':25,'elapsed':10,'accepted':0,'drafted':0},
              {'group':'Text','phase':'ON','valid':True,'decode_tps':50,'elapsed':5,'accepted':90,'drafted':100}]
        result=core.summarize(rows)[0]
        self.assertEqual(result['speedup'],2);self.assertEqual(result['acceptance'],.9)
if __name__=='__main__':unittest.main()
