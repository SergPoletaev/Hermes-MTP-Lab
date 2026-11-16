import importlib.util
from pathlib import Path
import tempfile,unittest
from unittest.mock import patch
p=Path(__file__).resolve().parents[1]/'dashboard'/'hardware_diag.py'
s=importlib.util.spec_from_file_location('hw_test',p)
hd=importlib.util.module_from_spec(s);s.loader.exec_module(hd)
class TestHardware(unittest.TestCase):
    def test_missing_nvidia_smi_is_not_faked(self):
        with patch.object(hd.shutil,'which',return_value=None):
            self.assertEqual(hd.snapshot(123)['gpu_source'],'unavailable')
            self.assertIsNone(hd.snapshot(123)['process_vram_mib'])
    def test_system_vs_process_memory_disambiguated(self):
        def fake(args):
            if args[0].startswith('--query-gpu'):return ['0, NVIDIA Mock, 16384, 6000, 23, 580.12']
            return ['13, 1000','42, 3500','42, 200']
        with patch.object(hd,'_csv',side_effect=fake):
            s=hd.snapshot(42)
        self.assertEqual(s['process_vram_mib'],3700)
        self.assertEqual(s['gpus'][0]['vram_used_global_mib'],6000)
    def test_fingerprint_only_partial_not_full(self):
        with tempfile.TemporaryDirectory() as folder:
            gguf=Path(folder)/'mtp.gguf';gguf.write_bytes(b'GGUF'+b'x'*1000)
            v=hd.file_identity(gguf)
            self.assertEqual(v['bytes'],1004)
            self.assertNotIn(str(gguf.parent),str(v))
            self.assertIn('NOT full-file',v['fingerprint_scope'])
if __name__=='__main__': unittest.main()
