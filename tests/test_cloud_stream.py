"""Offline unit tests for cloud streaming; never contact Nextcloud."""
import asyncio
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from fastapi import HTTPException
import cloud_stream


class FakeResponse:
    def __init__(self, status=206):
        self.status_code = status
        self.headers = {
            "Content-Type": "video/mp4",
            "Content-Range": "bytes 0-3/100",
            "Content-Length": "4",
            "Accept-Ranges": "bytes",
        }
        self.closed = False

    async def aclose(self):
        self.closed = True

    async def aiter_raw(self, chunk_size=131072):
        yield b"test"


class FakeClient:
    def __init__(self, response):
        self.response = response
        self.closed = False
        self.request = None

    def build_request(self, method, url, headers=None, auth=None):
        self.request = (method, url, headers)
        return self.request

    async def send(self, request, stream=False):
        return self.response

    async def aclose(self):
        self.closed = True


class CloudTests(unittest.IsolatedAsyncioTestCase):
    def test_url_encoding(self):
        self.assertTrue(cloud_stream.remote_url("Música #1.mp4").endswith("M%C3%BAsica%20%231.mp4"))

    def test_reject_path_traversal(self):
        for name in ("../test.mp4", "dir/test.mp3", "dir\\test.mp4", "test.txt", "", "..", "x\x00.mp4"):
            with self.subTest(name=name):
                with self.assertRaises(HTTPException):
                    cloud_stream.remote_url(name)

    async def test_partial_stream(self):
        response = FakeResponse()
        client = FakeClient(response)
        with patch.dict(os.environ, {
            "AGGILLI_WEBDAV_USER": "user",
            "AGGILLI_WEBDAV_APP_PASSWORD": "test-only",
        }), patch.object(cloud_stream.httpx, "AsyncClient", return_value=client):
            result = await cloud_stream.proxy_media("demo.mp4", "GET", "bytes=0-3")
            self.assertEqual(result.status_code, 206)
            self.assertEqual(client.request[2]["Range"], "bytes=0-3")
            self.assertEqual(client.request[2]["Authorization"], "Basic dXNlcjp0ZXN0LW9ubHk=")
            chunks = [chunk async for chunk in result.body_iterator]
            self.assertEqual(b"".join(chunks), b"test")
            self.assertTrue(client.closed)
            self.assertTrue(response.closed)

    async def test_reject_ignored_range(self):
        response = FakeResponse(status=200)
        client = FakeClient(response)
        with patch.dict(os.environ, {
            "AGGILLI_WEBDAV_USER": "user",
            "AGGILLI_WEBDAV_APP_PASSWORD": "test-only",
        }), patch.object(cloud_stream.httpx, "AsyncClient", return_value=client):
            with self.assertRaises(HTTPException) as context:
                await cloud_stream.proxy_media("demo.mp4", "GET", "bytes=0-3")
            self.assertEqual(context.exception.status_code, 502)
            self.assertTrue(client.closed)
            self.assertTrue(response.closed)

    async def test_invalid_range(self):
        with patch.dict(os.environ, {
            "AGGILLI_WEBDAV_USER": "user",
            "AGGILLI_WEBDAV_APP_PASSWORD": "test-only",
        }):
            with self.assertRaises(HTTPException) as context:
                await cloud_stream.proxy_media("demo.mp4", "GET", "bytes=0-1,3-4")
            self.assertEqual(context.exception.status_code, 416)


if __name__ == "__main__":
    unittest.main()
