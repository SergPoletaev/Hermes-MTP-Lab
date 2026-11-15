"""Guarantee the plain Git repository URL is directly discoverable by Hermes."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class TestGitInstallLayout(unittest.TestCase):
    def test_plain_repo_has_hybrid_plugin_at_root(self):
        required = ('plugin.yaml','__init__.py','desktop/plugin.js','dashboard/manifest.json','dashboard/plugin_api.py')
        for name in required:
            with self.subTest(path=name):
                self.assertTrue((ROOT/name).is_file(), f'Hermes Install from Git cannot discover {name}')
        self.assertFalse((ROOT/'hermes-mtp-lab').exists(), 'Obsolete nested plugin remains')

    def test_yaml_and_dashboard_match_plugin_id(self):
        yaml = (ROOT/'plugin.yaml').read_text(encoding='utf-8')
        self.assertIn('name: hermes-mtp-lab', yaml)
        manifest = (ROOT/'dashboard/manifest.json').read_text(encoding='utf-8')
        self.assertIn('"name":"hermes-mtp-lab"', manifest)
