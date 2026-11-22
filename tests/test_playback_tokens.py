"""Offline HMAC token checks; no WebDAV network calls."""
import os
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from fastapi import HTTPException
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from playback_tokens import signature, verify

class SignedPlaybackTests(unittest.TestCase):
    def test_valid_signature(self):
        key = "A" * 40
        expiry = int(time.time()) + 300
        with patch.dict(os.environ, {"AGGILLI_STREAM_TOKEN_SECRET": key}):
            verify("music.mp4", expiry, signature("music.mp4", expiry, key.encode()))

    def test_tampered_filename(self):
        key = "B" * 40
        expiry = int(time.time()) + 300
        with patch.dict(os.environ, {"AGGILLI_STREAM_TOKEN_SECRET": key}):
            with self.assertRaises(HTTPException):
                verify("other.mp4", expiry, signature("music.mp4", expiry, key.encode()))

    def test_expired_token(self):
        key = "C" * 40
        expiry = int(time.time()) - 1
        with patch.dict(os.environ, {"AGGILLI_STREAM_TOKEN_SECRET": key}):
            with self.assertRaises(HTTPException):
                verify("music.mp4", expiry, signature("music.mp4", expiry, key.encode()))

if __name__ == "__main__":
    unittest.main()
