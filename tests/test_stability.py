import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class CatalogTests(unittest.TestCase):
    def test_no_catalog_shrink(self):
        with tempfile.TemporaryDirectory() as directory:
            catalog = Path(directory) / "catalogo.json"
            old = [{"track_id": "a"}, {"track_id": "b"}]
            catalog.write_text(json.dumps(old))
            mod = load("refresh_catalog", "integrations/nextcloud_azura/refresh_player_catalog.py")
            class Response:
                def raise_for_status(self): pass
                def json(self): return [{"track_id":"a","download_url":"/api/station/1/ondemand/download/a","media":{}}]
            with patch.object(mod, "CATALOG", catalog), patch.object(mod, "API_KEY", catalog), patch.object(mod.httpx, "get", return_value=Response()):
                with self.assertRaisesRegex(RuntimeError, "shrank"):
                    mod.main()
            self.assertEqual(json.loads(catalog.read_text()), old)

    def test_normalization(self):
        mod = load("sync_media", "integrations/nextcloud_azura/sync.py")
        self.assertEqual(mod.normalized_filename("Música Teste.mp4"), "musica_teste")
        self.assertEqual(mod.normalized_filename("Música Teste.mp3"), "musica_teste")

if __name__ == "__main__":
    unittest.main()
