"""Regression checks for v0.3.3 companion discovery, metadata, and backend sync."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import importlib.util
import struct
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('mtp_033',ROOT/'dashboard/model_support.py')
ms=importlib.util.module_from_spec(spec);spec.loader.exec_module(ms)


def synthetic_gguf(meta:dict[str,int]):
    blob=bytearray(b'GGUF')
    blob+=struct.pack('<IQQ',3,0,len(meta))
    for key,val in meta.items():
        raw=key.encode('utf-8')
        blob+=struct.pack('<Q',len(raw))+raw+struct.pack('<Ii',5,val)
    return bytes(blob)


class TestCompanionDiscovery(unittest.TestCase):
    def test_native_gguf_header_confirms_embedded_mtp(self):
        with TemporaryDirectory() as temp:
            f=Path(temp)/'arbitrary.Q4_K_M.gguf'
            f.write_bytes(synthetic_gguf({'qwen35.nextn_predict_layers':2,'misc.counter':0}))
            self.assertTrue(ms.detect_embedded_mtp(str(f)))
            f2=Path(temp)/'dense.gguf';f2.write_bytes(synthetic_gguf({'qwen35.nextn_predict_layers':0}))
            self.assertFalse(ms.detect_embedded_mtp(str(f2)))
    def test_gguf_header_detection_not_model_name(self):
        with TemporaryDirectory() as temp:
            f=Path(temp)/'mtp-in-name-only.gguf';f.write_bytes(synthetic_gguf({'meta.some_field':1}))
            self.assertFalse(ms.detect_embedded_mtp(str(f)))
            f2=Path(temp)/'model-without-mtp-in-name.gguf'
            f2.write_bytes(synthetic_gguf({'new_arch.nextn_predict_layers':1}))
            self.assertTrue(ms.detect_embedded_mtp(str(f2)))
    def test_both_companion_types_discovered_and_no_binding(self):
        with TemporaryDirectory() as temp:
            d=Path(temp); main=d/'My-Model-Q4_K_M.gguf';main.write_bytes(b'GGUF'+b'\0'*64)
            proj=d/'My-Model-mmproj-f16.gguf';proj.write_bytes(b'GGUFprojector')
            head=d/'mtp-My-Model-Q8.gguf';head.write_bytes(b'GGUFhead')
            (d/'mtp-broken.gguf').write_bytes(b'NOTAGGUF')
            p=ms.projector_candidates(str(main));h=ms.head_candidates(str(main))
            self.assertEqual([x['name'] for x in p],[proj.name])
            self.assertEqual([x['name'] for x in h],[head.name])
            self.assertNotIn('mtp-broken.gguf',[x['name'] for x in h])
            self.assertFalse((d/'model-companions.json').exists())
    def test_api_version_and_candidates_share_the_existing_status_route(self):
        from fastapi.testclient import TestClient
        # Import API module as a package to preserve relative imports.
        import sys,types
        group=types.ModuleType('local_plugin_api_033');group.__path__=[str(ROOT/'dashboard')]
        sys.modules[group.__name__]=group
        try:
            api_spec=importlib.util.spec_from_file_location(group.__name__+'.plugin_api',ROOT/'dashboard/plugin_api.py')
            api=importlib.util.module_from_spec(api_spec)
            sys.modules[api_spec.name]=api
            api_spec.loader.exec_module(api)
            from fastapi import FastAPI
            app=FastAPI();app.include_router(api.router)
            self.assertFalse(any(getattr(route,'path','')=='/projectors' for route in app.routes))
            with TemporaryDirectory() as temp:
                d=Path(temp);main=d/'Arbitrary.gguf';main.write_bytes(b'GGUFmain')
                projector=d/'Arbitrary-mmproj.gguf';projector.write_bytes(b'GGUFprojector')
                preset=d/'presets.ini';preset.write_text('[Arbitrary]\nmodel = '+str(main)+'\nctx-size = 8192\n')
                comp=d/'model-companions.json'
                import types
                fake=types.SimpleNamespace(proc=None)
                with patch.object(api,'environment',return_value=(fake,preset,comp,api.bench.ms.model_specs(preset,comp),'Arbitrary')):
                    import sys
                    boot=types.ModuleType('hermes_cli.local_runtime.bootstrap')
                    boot.assets_dir=lambda:str(d)
                    local=types.ModuleType('hermes_cli.local_runtime');local.bootstrap=boot
                    hermes=types.ModuleType('hermes_cli');hermes.local_runtime=local
                    with patch.dict(sys.modules,{'hermes_cli':hermes,'hermes_cli.local_runtime':local,'hermes_cli.local_runtime.bootstrap':boot}):
                        result=TestClient(app).get('/status')
                self.assertEqual(result.status_code,200)
                data=result.json()
                self.assertEqual(data['api_version'],'0.5.0')
                self.assertEqual([x['name'] for x in data['projector_candidates']],[projector.name])
        finally:
            for key in list(sys.modules):
                if key==group.__name__ or key.startswith(group.__name__+'.'):sys.modules.pop(key,None)

if __name__=='__main__':unittest.main()
