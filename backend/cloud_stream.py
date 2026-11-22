"""Authenticated, range-aware WebDAV media streaming for Aggilli Music.

This router is NOT mounted in production. Register it explicitly only after
validating authorization, proxy rules and browser playback. Credentials stay
server-side; the browser never connects to WebDAV directly.
"""
import os
import base64
from contextlib import asynccontextmanager
from pathlib import PurePosixPath
from urllib.parse import quote

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import StreamingResponse

from main import require_upload_auth

_shared_client: httpx.AsyncClient | None = None

@asynccontextmanager
async def cloud_lifespan(_app):
    global _shared_client
    client = httpx.AsyncClient(
        timeout=httpx.Timeout(connect=10, read=60, write=10, pool=10),
        limits=httpx.Limits(max_connections=12, max_keepalive_connections=6, keepalive_expiry=30),
        follow_redirects=False,
    )
    _shared_client = client
    try:
        yield
    finally:
        _shared_client = None
        await client.aclose()

router = APIRouter(lifespan=cloud_lifespan)
ALLOWED_EXTENSIONS = {".mp3", ".mp4"}
BASE_URL = (
    "https://nuvem.aggillintelligence.com.br/"
    "remote.php/dav/files/aggilli-admin/musica/"
)
FORWARDED_HEADERS = (
    "content-type", "content-length", "content-range", "accept-ranges",
    "etag", "last-modified",
)


def remote_url(filename: str) -> str:
    # One path component only: no traversal, slash, backslash or URL injection.
    if (not filename or filename in {".", ".."} or "/" in filename
            or "\\" in filename or "\x00" in filename
            or PurePosixPath(filename).suffix.lower() not in ALLOWED_EXTENSIONS):
        raise HTTPException(400, detail="Invalid media filename")
    return BASE_URL + quote(filename, safe="")


async def proxy_media(filename: str, method: str, range_header: str | None):
    username = os.environ.get("AGGILLI_WEBDAV_USER")
    password = os.environ.get("AGGILLI_WEBDAV_APP_PASSWORD")
    if not username or not password:
        raise HTTPException(503, detail="Cloud media not configured")

    headers = {}
    if range_header:
        # Restrict header syntax and length before passing it upstream.
        import re
        if len(range_header) > 128 or not re.fullmatch(
            r"bytes=(?:\d+-\d*|-\d+)", range_header
        ):
            raise HTTPException(416, detail="Unsupported byte range")
        headers["Range"] = range_header

    url = remote_url(filename)
    basic = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
    headers["Authorization"] = f"Basic {basic}"
    own_client = _shared_client is None
    client = _shared_client or httpx.AsyncClient(
        timeout=httpx.Timeout(connect=10, read=60, write=10, pool=10),
        follow_redirects=False,
    )
    try:
        request = client.build_request(method, url, headers=headers)
        upstream = await client.send(request, stream=True)
    except httpx.HTTPError:
        if own_client:
            await client.aclose()
        raise HTTPException(502, detail="Cloud storage unavailable")

    if upstream.status_code not in {200, 206}:
        status = upstream.status_code
        await upstream.aclose()
        if own_client:
            await client.aclose()
        if status == 404:
            raise HTTPException(404, detail="Media not found")
        if status in {401, 403}:
            raise HTTPException(502, detail="Cloud storage authorization failed")
        if status == 416:
            raise HTTPException(416, detail="Range not satisfiable")
        raise HTTPException(502, detail=f"Cloud storage HTTP {status}")

    # A server ignoring Range could stream an entire multi-GB video.
    if range_header and upstream.status_code != 206:
        await upstream.aclose()
        if own_client:
            await client.aclose()
        raise HTTPException(502, detail="Cloud storage did not honor byte range")

    response_headers = {
        k: v for k, v in upstream.headers.items() if k.lower() in FORWARDED_HEADERS
    }
    response_headers["Cache-Control"] = "private, no-store"
    response_headers["X-Content-Type-Options"] = "nosniff"
    response_headers["Content-Disposition"] = "inline"
    if method == "HEAD":
        await upstream.aclose()
        if own_client:
            await client.aclose()
        from fastapi import Response
        return Response(status_code=upstream.status_code, headers=response_headers)

    async def stream():
        try:
            async for chunk in upstream.aiter_raw(chunk_size=128 * 1024):
                yield chunk
        finally:
            await upstream.aclose()
            if own_client:
                await client.aclose()

    return StreamingResponse(
        stream(),
        status_code=upstream.status_code,
        headers=response_headers,
    )


@router.get("/cloud/{filename}", dependencies=[Depends(require_upload_auth)])
async def get_cloud_media(filename: str, range: str | None = Header(default=None)):
    return await proxy_media(filename, "GET", range)


@router.head("/cloud/{filename}", dependencies=[Depends(require_upload_auth)])
async def head_cloud_media(filename: str, range: str | None = Header(default=None)):
    return await proxy_media(filename, "HEAD", range)
