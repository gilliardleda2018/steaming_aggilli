#!/usr/bin/env python3
"""List MP3 files from a Nextcloud WebDAV folder without modifying remote data.

Environment:
  AGGILLI_WEBDAV_URL (optional, defaults to the music folder)
  AGGILLI_WEBDAV_USER (required)
  AGGILLI_WEBDAV_APP_PASSWORD (required)

Uses Python standard library only. Does not download or upload files.
"""
import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

DEFAULT_URL = (
    "https://nuvem.aggillintelligence.com.br/"
    "remote.php/dav/files/aggilli-admin/musica/"
)
DAV_NS = "{DAV:}"


def list_mp3(url: str, username: str, password: str) -> list[dict]:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("WebDAV URL must use HTTPS")
    if not url.endswith("/"):
        url += "/"
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    request = urllib.request.Request(
        url,
        data=b'<?xml version="1.0"?><d:propfind xmlns:d="DAV:"><d:prop><d:resourcetype/><d:getcontentlength/><d:getetag/></d:prop></d:propfind>',
        headers={
            "Authorization": f"Basic {token}",
            "Depth": "1",
            "Content-Type": "application/xml",
            "Accept": "application/xml",
        },
        method="PROPFIND",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        if response.status != 207:
            raise RuntimeError(f"Unexpected WebDAV status: {response.status}")
        body = response.read(10 * 1024 * 1024 + 1)
        if len(body) > 10 * 1024 * 1024:
            raise RuntimeError("WebDAV listing too large")
    root = ET.fromstring(body)
    entries = []
    for item in root.findall(f"{DAV_NS}response"):
        href = item.findtext(f"{DAV_NS}href") or ""
        name = urllib.parse.unquote(urllib.parse.urlsplit(href).path).rstrip("/").rsplit("/", 1)[-1]
        if not name.lower().endswith(".mp3"):
            continue
        props = item.find(f".//{DAV_NS}prop")
        if props is None:
            continue
        if props.find(f"{DAV_NS}resourcetype/{DAV_NS}collection") is not None:
            continue
        size_text = props.findtext(f"{DAV_NS}getcontentlength")
        entries.append({
            "name": name,
            "size_bytes": int(size_text) if size_text and size_text.isdigit() else None,
            "etag": props.findtext(f"{DAV_NS}getetag"),
        })
    return sorted(entries, key=lambda e: e["name"].casefold())


def main() -> int:
    user = os.environ.get("AGGILLI_WEBDAV_USER")
    password = os.environ.get("AGGILLI_WEBDAV_APP_PASSWORD")
    if not user or not password:
        print("Missing AGGILLI_WEBDAV_USER or AGGILLI_WEBDAV_APP_PASSWORD", file=sys.stderr)
        return 2
    try:
        entries = list_mp3(os.environ.get("AGGILLI_WEBDAV_URL", DEFAULT_URL), user, password)
    except urllib.error.HTTPError as exc:
        print(f"WebDAV returned HTTP {exc.code}", file=sys.stderr)
        return 1
    except (urllib.error.URLError, ValueError, RuntimeError, ET.ParseError) as exc:
        print(f"WebDAV listing failed: {type(exc).__name__}", file=sys.stderr)
        return 1
    print(json.dumps({"count": len(entries), "files": entries}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
