"""Private cloud catalog for the isolated Aggilli Music test app.

Uses PROPFIND Depth:1; never exposes WebDAV credentials or private URLs.
"""
import os
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree as ET

import httpx
from fastapi import APIRouter, Depends, HTTPException
from main import require_upload_auth
from cloud_stream import BASE_URL

router = APIRouter()
DAV = "{DAV:}"
MAX_XML = 8 * 1024 * 1024


def parse_catalog(body: bytes) -> list[dict]:
    root = ET.fromstring(body)
    items = []
    for node in root.findall(f"{DAV}response"):
        href = node.findtext(f"{DAV}href") or ""
        name = unquote(urlsplit(href).path).rstrip("/").rsplit("/", 1)[-1]
        if not name.lower().endswith((".mp3", ".mp4")):
            continue
        props = node.find(f".//{DAV}prop")
        if props is None or props.find(f"{DAV}resourcetype/{DAV}collection") is not None:
            continue
        size = props.findtext(f"{DAV}getcontentlength")
        items.append({
            "track_id": "cloud:" + name,
            "source": "nextcloud",
            "filename": name,
            "format": name.rsplit(".", 1)[-1].lower(),
            "size_bytes": int(size) if size and size.isdigit() else None,
            "etag": props.findtext(f"{DAV}getetag"),
            "media": {"title": name.rsplit(".", 1)[0]},
        })
    return sorted(items, key=lambda t: t["filename"].casefold())


@router.get("/cloud-catalog", dependencies=[Depends(require_upload_auth)])
async def cloud_catalog():
    username = os.environ.get("AGGILLI_WEBDAV_USER")
    password = os.environ.get("AGGILLI_WEBDAV_APP_PASSWORD")
    if not username or not password:
        raise HTTPException(503, detail="Cloud catalog not configured")
    xml = b'<?xml version="1.0"?><d:propfind xmlns:d="DAV:"><d:prop><d:resourcetype/><d:getcontentlength/><d:getetag/></d:prop></d:propfind>'
    try:
        async with httpx.AsyncClient(
            auth=(username, password),
            timeout=30,
            follow_redirects=False,
        ) as client:
            response = await client.request(
                "PROPFIND", BASE_URL,
                headers={"Depth": "1", "Content-Type": "application/xml"},
                content=xml,
            )
            if response.status_code != 207:
                raise HTTPException(502, detail=f"Cloud catalog HTTP {response.status_code}")
            if len(response.content) > MAX_XML:
                raise HTTPException(502, detail="Cloud catalog too large")
            items = parse_catalog(response.content)
    except (httpx.HTTPError, ET.ParseError):
        raise HTTPException(502, detail="Cloud catalog unavailable")
    return {"count": len(items), "tracks": items}
