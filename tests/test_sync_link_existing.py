import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PATH = Path(__file__).resolve().parents[1] / "integrations" / "nextcloud_azura" / "sync.py"
SPEC = importlib.util.spec_from_file_location("aggilli_nextcloud_sync_link", PATH)
sync = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sync)


class Response:
    def __init__(self, data=None):
        self.data = data

    def raise_for_status(self):
        return None

    def json(self):
        return self.data


class FakeAzura:
    """Minimal AzuraCast double: media listing plus the playlist PUT."""

    def __init__(self, media):
        self.media = media
        self.puts = []
        self.uploads = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get(self, url, **kwargs):
        return Response([dict(m, playlists=[{"id": i} for i in m["playlists"]]) for m in self.media])

    def put(self, url, json, **kwargs):
        media_id = int(url.rsplit("/", 1)[1])
        self.puts.append((media_id, json["playlists"]))
        next(m for m in self.media if m["id"] == media_id)["playlists"] = json["playlists"]
        return Response({})

    def post(self, url, **kwargs):
        self.uploads.append(url)
        raise AssertionError("existing media must not be uploaded again")


class FakeCloud:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class LinkExistingMediaTests(unittest.TestCase):
    def run_sync(self, media, remote, limit="20"):
        azura = FakeAzura(media)
        clients = iter([FakeCloud(), azura])
        with tempfile.TemporaryDirectory() as td:
            key_file = Path(td) / "key"
            key_file.write_text("test-key")
            env = {"AGGILLI_WEBDAV_USER": "u", "AGGILLI_WEBDAV_APP_PASSWORD": "p", "AGGILLI_SYNC_MAX_FILES": limit}
            with patch.dict(os.environ, env), \
                 patch.object(sync, "API_KEY_FILE", key_file), \
                 patch.object(sync, "STATE_FILE", Path(td) / "state.json"), \
                 patch.object(sync, "list_remote", lambda client: remote), \
                 patch.object(sync.httpx, "Client", lambda *a, **k: next(clients)):
                sync.main()
        return azura

    def test_m4a_already_in_library_is_linked_to_player_playlists(self):
        media = [{"id": 7, "path": "ESTL - Voyage voyage [wn1OPI6lwnY].mp3", "playlists": []}]
        azura = self.run_sync(media, [("ESTL - Voyage voyage [wn1OPI6lwnY].m4a", 10, "e1")])
        self.assertEqual(azura.puts, [(7, [1, 2])])
        self.assertEqual(azura.uploads, [])

    def test_other_playlists_are_preserved(self):
        media = [{"id": 8, "path": "Round Again.mp3", "playlists": [3]}]
        azura = self.run_sync(media, [("Round Again.mp4", 10, "e2")])
        self.assertEqual(azura.puts, [(8, [1, 2, 3])])

    def test_media_already_in_playlists_is_left_alone(self):
        media = [{"id": 9, "path": "Backwater.mp3", "playlists": [1, 2]}]
        azura = self.run_sync(media, [("Backwater.mp4", 10, "e3")])
        self.assertEqual(azura.puts, [])

    def test_duplicate_library_names_are_not_guessed(self):
        media = [{"id": 10, "path": "a/Tangled Hearts.mp3", "playlists": []},
                 {"id": 11, "path": "b/Tangled Hearts.mp3", "playlists": []}]
        azura = self.run_sync(media, [("Tangled Hearts.mp4", 10, "e4")])
        self.assertEqual(azura.puts, [])

    def test_links_count_toward_the_limit(self):
        media = [{"id": i, "path": f"faixa {i}.mp3", "playlists": []} for i in (1, 2, 3)]
        remote = [(f"faixa {i}.m4a", 10, f"e{i}") for i in (1, 2, 3)]
        azura = self.run_sync(media, remote, limit="2")
        self.assertEqual([p[0] for p in azura.puts], [1, 2])


if __name__ == "__main__":
    unittest.main()
