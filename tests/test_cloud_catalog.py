"""Offline catalog parsing tests."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from cloud_catalog import parse_catalog

XML = b'''<?xml version="1.0"?>
<d:multistatus xmlns:d="DAV:">
  <d:response><d:href>/remote.php/dav/files/aggilli-admin/musica/</d:href>
    <d:propstat><d:prop><d:resourcetype><d:collection/></d:resourcetype></d:prop></d:propstat>
  </d:response>
  <d:response><d:href>/remote.php/dav/files/aggilli-admin/musica/Test%20Video.mp4</d:href>
    <d:propstat><d:prop><d:getcontentlength>2800</d:getcontentlength><d:getetag>"v1"</d:getetag></d:prop></d:propstat>
  </d:response>
  <d:response><d:href>/remote.php/dav/files/aggilli-admin/musica/Audio.mp3</d:href>
    <d:propstat><d:prop><d:getcontentlength>300</d:getcontentlength></d:prop></d:propstat>
  </d:response>
  <d:response><d:href>/remote.php/dav/files/aggilli-admin/musica/cover.jpg</d:href>
    <d:propstat><d:prop><d:getcontentlength>200</d:getcontentlength></d:prop></d:propstat>
  </d:response>
</d:multistatus>'''

class CatalogTests(unittest.TestCase):
    def test_mp3_mp4_and_filter(self):
        tracks = parse_catalog(XML)
        self.assertEqual(len(tracks), 2)
        self.assertEqual(tracks[0]["track_id"], "cloud:Audio.mp3")
        self.assertEqual(tracks[1]["filename"], "Test Video.mp4")
        self.assertEqual(tracks[1]["size_bytes"], 2800)
        self.assertEqual(tracks[1]["source"], "nextcloud")
        self.assertEqual(tracks[1]["format"], "mp4")

if __name__ == "__main__":
    unittest.main()
