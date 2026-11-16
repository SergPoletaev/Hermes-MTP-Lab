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

    def test_projector_discovery_adjacent_without_implicit_binding(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d)
            main=folder/'Huihui-Qwen3.8-27B-abliterated.Q4_K_M.gguf'
            main.write_bytes(b'GGUFmain')
            proj=folder/'Huihui-Qwen3.8-27B-abliterated.mmproj-f16.gguf'
            proj.write_bytes(b'GGUFproj')
            (folder/'Unrelated-vision.gguf').write_bytes(b'GGUFother')
            (folder/'mmproj-Qwen3.8-17B.gguf').write_bytes(b'GGUFother')
            (folder/'mmproj-corrupt.gguf').write_bytes(b'NOT-GGUF')
            found=ms.projector_candidates(str(main))
            self.assertEqual(found[0]['name'],proj.name)
            self.assertEqual(found[0]['recommendation'],'strong')
            self.assertNotIn('mmproj-corrupt.gguf',[x['name'] for x in found])
            self.assertLess(ms._projector_score('Qwen3.8-27B-Q4','mmproj-Qwen3.8-17B-Q8'),75)
    def test_projector_scans_explicit_folder_only(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d)
            model=folder/'model.gguf';model.write_bytes(b'GGUFmain')
            other=folder/'others';other.mkdir()
            (other/'model-mmproj.gguf').write_bytes(b'GGUF')
            self.assertEqual(ms.projector_candidates(str(model)),[])
            self.assertEqual(len(ms.projector_candidates(str(model),str(other))),1)
    def test_confirmed_embedded_mtp_distinguished_from_preset(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d);model=folder/'universal.gguf';model.write_bytes(b'GGUFstub')
            preset=folder/'presets.ini';preset.write_text('[Any]\nmodel = '+str(model)+'\nctx-size = 8192\nspec-type = draft-mtp\n')
            comp=folder/'model-companions.json'
            with patch.object(ms,'detect_embedded_mtp',return_value=False):
                m=ms.model_specs(preset,comp)[0]
                self.assertTrue(m['embedded_mtp']);self.assertFalse(m['embedded_verified']);self.assertEqual(m['mtp_evidence'],'preset')
            with patch.object(ms,'detect_embedded_mtp',return_value=True):
                m=ms.model_specs(preset,comp)[0]
                self.assertTrue(m['embedded_verified']);self.assertEqual(m['mtp_evidence'],'gguf');self.assertEqual(m['mtp_kind'],'embedded')

    def test_balanced_phase_order_and_token_limits(self):
        self.assertEqual(core.phase_order(0),['OFF','ON'])
        self.assertEqual(core.phase_order(1),['ON','OFF'])
        self.assertEqual(core.phase_order(2),['OFF','ON'])
        code=next(t for t in core.TASKS if t['id']=='code')
        self.assertEqual(core.token_budget(code,32768),1536)
        self.assertEqual(core.token_budget(code,2048),512)
        self.assertTrue(core.is_truncated({'finish_reason':'length'},768))
        self.assertFalse(core.is_truncated({'finish_reason':'stop','usage':{'completion_tokens':200}},768))
        self.assertTrue(core.is_truncated({'finish_reason':None,'usage':{'completion_tokens':767}},768))
        self.assertEqual(core.REASONING_MODES,('off','native'))
    def test_comparability_reports_unknown_separately_from_mismatch(self):
        common={'ctx':'32768','kv_k':'q8_0','kv_v':'q8_0','flash':'on',
                'batch':'','ubatch':'','mmproj':True,'gpu_layers':None,
                'engine_version':'build 12292'}
        rows=[{'trial':1,'task':'code','replica':1,'phase':p,'token_limit':1536} for p in ('OFF','ON')]
        comparison=core.compare_configuration({'OFF':{**common,'mtp':False},'ON':{**common,'mtp':True,'spec_type':'draft-mtp'}},rows)
        self.assertEqual(comparison['status'],'uncertain')
        self.assertEqual(comparison['differences'],{})
        self.assertIn('batch',comparison['unknown_fields'])
        self.assertEqual(comparison['unequal_caps'],0)
        mismatch=core.compare_configuration({'OFF':common,'ON':{**common,'kv_k':'f16'}},rows)
        self.assertEqual(mismatch['status'],'mismatch')
        self.assertIn('kv_k',mismatch['differences'])
    def test_request_policy_off_and_native(self):
        class Fake:
            base_url='http://127.0.0.1:18434/v1'
            api_key='not-real'
        seen=[]
        def fake_http(url,key,body,timeout=480):
            seen.append(body)
            return {'usage':{'completion_tokens':10},'choices':[{'finish_reason':'stop','message':{'content':'OK'}}]}
        with patch.object(core,'http_json',side_effect=fake_http):
            for mode in ('off','native'):
                core.route_request(Fake(),'Demo',{'prompt':'hello','image':False},None,128,reasoning_mode=mode)
        self.assertEqual(seen[0]['chat_template_kwargs'],{'enable_thinking':False})
        self.assertEqual(seen[0]['reasoning_effort'],'none')
        self.assertNotIn('chat_template_kwargs',seen[1])
        self.assertNotIn('reasoning_effort',seen[1])
        for key in core.REQUEST_CONTRACT:
            self.assertEqual(seen[0][key],seen[1][key])

    def test_quality_statistics_are_not_timing_validity(self):
        rows=[{'group':'Test','phase':'OFF','valid':True,'decode_tps':10,'elapsed':1,'accepted':0,'drafted':0,'quality':{'status':'fail'}},
              {'group':'Test','phase':'ON','valid':True,'decode_tps':20,'elapsed':1,'accepted':100,'drafted':125,'quality':{'status':'pass'}}]
        a=core.summarize(rows)[0]
        self.assertEqual(a['off_quality_fail'],1)
        self.assertEqual(a['on_quality_pass'],1)
        self.assertEqual(a['speedup'],2)
    def test_status_summary(self):
        rows=[{'group':'Text','phase':'OFF','valid':True,'decode_tps':25,'elapsed':10,'accepted':0,'drafted':0},
              {'group':'Text','phase':'ON','valid':True,'decode_tps':50,'elapsed':5,'accepted':90,'drafted':100}]
        result=core.summarize(rows)[0]
        self.assertEqual(result['speedup'],2);self.assertEqual(result['acceptance'],.9)
if __name__=='__main__':unittest.main()
