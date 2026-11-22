import importlib.util
import os
import unittest
from pathlib import Path
from unittest.mock import patch
import httpx

PATH = Path(__file__).resolve().parents[1] / "integrations" / "nextcloud_azura" / "sync.py"
SPEC = importlib.util.spec_from_file_location("aggilli_nextcloud_sync_test", PATH)
sync = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sync)


class FakeClient:
    def __init__(self, status):
        self.status = status
    def request(self, method, url, **kwargs):
        self.url = url
        return httpx.Response(self.status, request=httpx.Request(method, url))


class WebDavFolderTests(unittest.TestCase):
    def test_default_musicas_folder(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertTrue(sync.webdav_folder_url().endswith("/musicas/"))

    def test_override_folder(self):
        with patch.dict(os.environ, {"AGGILLI_WEBDAV_FOLDER": "Minhas Músicas"}):
            self.assertTrue(sync.webdav_folder_url().endswith("/Minhas%20M%C3%BAsicas/"))

    def test_reject_path_traversal(self):
        for value in ("../musica", "musicas/other", "..", "bad\\name", ""):
            with self.subTest(value=value), patch.dict(os.environ, {"AGGILLI_WEBDAV_FOLDER": value}):
                with self.assertRaises(RuntimeError):
                    sync.webdav_folder_url()

    def test_403_message_explains_permission(self):
        with self.assertRaisesRegex(RuntimeError, "HTTP 403.*permissions"):
            sync.list_remote(FakeClient(403))

if __name__ == "__main__":
    unittest.main()
