import importlib.util
from pathlib import Path
import json
import unittest
from unittest.mock import patch,MagicMock
P=Path(__file__).resolve().parents[1]/'dashboard'/'quality_eval.py'
spec=importlib.util.spec_from_file_location('quality_test',P)
qe=importlib.util.module_from_spec(spec);spec.loader.exec_module(qe)

class TestQuality(unittest.TestCase):
    def test_structured_correct_and_incorrect(self):
        valid='Answer: ```json\n{"red":380,"blue":203,"green":206,"total":789}\n```'
        self.assertEqual(qe.grade('structured',valid)['status'],'pass')
        self.assertEqual(qe.grade('structured',valid.replace('789','790'))['status'],'fail')
        self.assertEqual(qe.grade('structured','{"red":true,"blue":203,"green":206,"total":789}')['status'],'fail')
        self.assertEqual(qe.grade('structured','no json')['status'],'fail')
    def test_truncated_has_priority_over_correct_json(self):
        value='{"red":380,"blue":203,"green":206,"total":789}'
        self.assertEqual(qe.grade('structured',value,finish_reason='length')['status'],'incomplete')
    def test_vision_reference_checks(self):
        self.assertEqual(qe.grade('grounding','The card says TEST 47. The notebooks are red, green, yellow.')['status'],'pass')
        self.assertEqual(qe.grade('grounding','The card says TEST 48. The notebooks are red, green, yellow.')['status'],'fail')
    def test_generated_code_is_not_executed_on_host(self):
        src='```python\ndef merge_intervals(intervals):\n    return []\n```'
        with patch.object(qe,'docker_ready',return_value=(False,'docker_unavailable')):
            r=qe.grade('code',src)
        self.assertEqual(r['status'],'unverified');self.assertEqual(r['reason'],'docker_unavailable')
        self.assertEqual(qe.grade('code','def nope():\n pass',sandbox=(False,'no'))['status'],'fail')
        self.assertEqual(qe.grade('code','def merge_intervals(:',sandbox=(False,'no'))['status'],'fail')
    def test_optional_docker_is_safe_and_no_pull(self):
        binary='docker'
        with patch.object(qe.shutil,'which',return_value=binary),patch.object(qe.subprocess,'run') as run:
            run.return_value=MagicMock(returncode=1)
            self.assertEqual(qe.docker_ready(),(False,'sandbox_image_not_cached'))
            self.assertEqual(run.call_args.args[0],['docker','image','inspect',qe.CODE_IMAGE])
    def test_pair_exposes_both_channels_and_does_not_label_unequal_quality_failed(self):
        source={'model_id':'A','trial':1,'task':'network','phase':'OFF','replica':1,
                'visible':'Hello','reasoning':'X','quality':{'status':'manual_review'}}
        other={**source,'phase':'ON','visible':'Hello','reasoning':'Y'}
        comp=qe.pair(source,other,'OFF/ON')
        self.assertTrue(comp['visible_equal']);self.assertFalse(comp['reasoning_equal'])
        self.assertEqual(comp['quality_left'],'manual_review')
    def test_comparisons_three_pair_types(self):
        vals=[]
        for phase in ('OFF','ON'):
            for replica in (1,2):
                vals.append({'model_id':'a','trial':1,'task':'x','phase':phase,'replica':replica,
                             'visible':phase,'reasoning':''})
        comps=qe.comparisons(vals)
        self.assertEqual(len(comps),4)
        s=qe.comparison_summary(comps)
        self.assertEqual(s['OFF/OFF']['same_visible'],1)
        self.assertEqual(s['ON/ON']['same_visible'],1)
        self.assertEqual(s['OFF/ON']['same_visible'],0)
    def test_open_ended_never_claims_automatic_accuracy(self):
        self.assertEqual(qe.grade('network','A paragraph')['status'],'manual_review')
        self.assertEqual(qe.grade('narrative','A story')['status'],'manual_review')
        self.assertEqual(qe.grade('scene','A picture')['status'],'manual_review')

if __name__=='__main__': unittest.main()
