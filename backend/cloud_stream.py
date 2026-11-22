"""Authenticated, range-aware WebDAV media streaming for Aggilli Music.

This router is NOT mounted in production. Register it explicitly only after
validating authorization, proxy rules and browser playback. Credentials stay
server-side; the browser never connects to WebDAV directly.
"""
import os
from pathlib import PurePosixPath
from urllib.parse import quote

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import StreamingResponse

from main import require_upload_auth

router = APIRouter()
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
    client = httpx.AsyncClient(
        auth=httpx.BasicAuth(username, password),
        timeout=httpx.Timeout(connect=10, read=60, write=10, pool=10),
        follow_redirects=False,
    )
    try:
        request = client.build_request(method, url, headers=headers)
        upstream = await client.send(request, stream=True)
    except httpx.HTTPError:
        await client.aclose()
        raise HTTPException(502, detail="Cloud storage unavailable")

    if upstream.status_code not in {200, 206}:
        status = upstream.status_code
        await upstream.aclose()
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
        await client.aclose()
        from fastapi import Response
        return Response(status_code=upstream.status_code, headers=response_headers)

    async def stream():
        try:
            async for chunk in upstream.aiter_raw(chunk_size=128 * 1024):
                yield chunk
        finally:
            await upstream.aclose()
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
