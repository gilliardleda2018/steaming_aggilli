#!/usr/bin/env python3
"""One-way Nextcloud WebDAV -> AzuraCast synchronization (no remote deletes).

Run as root with /etc/aggilli-music/nextcloud-sync.env loaded.
Uses the same AzuraCast upload API as the existing Aggilli Music backend.
"""
import json
import os
import unicodedata
import subprocess
import tempfile
import re
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit
from xml.etree import ElementTree as ET

import httpx

DAV_BASE = "https://nuvem.aggillintelligence.com.br/remote.php/dav/files/aggilli-admin/"
DEFAULT_DAV_FOLDER = "musicas"


def webdav_folder_url():
    """Use the configured Nextcloud folder; never silently fall back on 403."""
    folder = os.environ.get("AGGILLI_WEBDAV_FOLDER", DEFAULT_DAV_FOLDER).strip().strip("/")
    if not folder or folder in {".", ".."} or "/" in folder or chr(92) in folder or "?" in folder or "#" in folder:
        raise RuntimeError("Invalid AGGILLI_WEBDAV_FOLDER; use one folder name")
    return DAV_BASE + quote(folder, safe="") + "/"


DAV_URL = webdav_folder_url()

AZURA = "http://127.0.0.1:8080/api/station/1"
API_KEY_FILE = Path("/etc/aggilli-music/azuracast-api-key")
STATE_FILE = Path("/var/lib/aggilli-music/nextcloud-azura-state.json")
MAX_BYTES = 2 * 1024**3
DAV = "{DAV:}"


def list_remote(client):
    xml = b'<d:propfind xmlns:d="DAV:"><d:prop><d:resourcetype/><d:getcontentlength/><d:getetag/></d:prop></d:propfind>'
    response = client.request("PROPFIND", DAV_URL, headers={"Depth": "1", "Content-Type": "application/xml"}, content=xml)
    if response.status_code == 403:
        raise RuntimeError(
            "Nextcloud WebDAV HTTP 403: access denied to folder "
            + DAV_URL + " (check AGGILLI_WEBDAV_FOLDER and user permissions)"
        )
    response.raise_for_status()
    if response.status_code != 207:
        raise RuntimeError(f"WebDAV PROPFIND HTTP {response.status_code}")
    if len(response.content) > 8 * 1024**2:
        raise RuntimeError("WebDAV listing too large")
    root = ET.fromstring(response.content)
    result = []
    for item in root.findall(f"{DAV}response"):
        name = unquote(urlsplit(item.findtext(f"{DAV}href") or "").path).rstrip("/").split("/")[-1]
        props = item.find(f".//{DAV}prop")
        if not props or props.find(f"{DAV}resourcetype/{DAV}collection") is not None:
            continue
        if not name or "/" in name or "\\" in name or name.startswith(".") or name.lower().endswith(".temp.mp4") or Path(name).suffix.lower() not in {".mp3", ".mp4"}:
            continue
        size = props.findtext(f"{DAV}getcontentlength") or ""
        if not size.isdecimal() or int(size) > MAX_BYTES or int(size) == 0:
            continue
        result.append((name, int(size), props.findtext(f"{DAV}getetag") or ""))
    return sorted(result)


def download(client, name, size, target):
    with client.stream("GET", DAV_URL + quote(name, safe="")) as r:
        r.raise_for_status()
        if r.status_code != 200:
            raise RuntimeError(f"Download HTTP {r.status_code}")
        count = 0
        with target.open("wb") as f:
            for chunk in r.iter_bytes(chunk_size=256 * 1024):
                count += len(chunk)
                if count > size or count > MAX_BYTES:
                    raise RuntimeError("Download exceeded expected size")
                f.write(chunk)
        if count != size:
            raise RuntimeError(f"Partial download: {count}/{size}")


def normalized_filename(name):
    ascii_name = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode('ascii')
    return re.sub(r'[^a-z0-9]+', '_', Path(ascii_name).stem.lower()).strip('_')


def assign_playlists(azura, headers, media_id, playlist_ids=(1, 2)):
    """Assign approved station playlists using AzuraCast's documented media PUT."""
    if not isinstance(media_id, int) or media_id <= 0:
        raise RuntimeError("Upload response did not provide a numeric media ID")
    response = azura.put(
        f"{AZURA}/file/{media_id}",
        headers=headers,
        json={"playlists": list(playlist_ids)},
    )
    response.raise_for_status()
    check = azura.get(AZURA + "/files", headers=headers)
    check.raise_for_status()
    media = next((x for x in check.json() if x.get("id") == media_id), None)
    if media is None:
        raise RuntimeError(f"Media {media_id} not found after playlist update")
    actual = {p["id"] for p in media.get("playlists", []) if isinstance(p, dict) and "id" in p}
    if not set(playlist_ids).issubset(actual):
        raise RuntimeError(f"Media {media_id}: playlist assignment not confirmed ({sorted(actual)})")
    print(f"PLAYLISTS OK: media {media_id} -> {sorted(actual)}", flush=True)


def main():
    user = os.environ.get("AGGILLI_WEBDAV_USER")
    password = os.environ.get("AGGILLI_WEBDAV_APP_PASSWORD")
    if not user or not password:
        raise RuntimeError("Missing WebDAV environment credentials")
    key = API_KEY_FILE.read_text().strip()
    headers = {"X-API-Key": key}
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    state = json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}
    limit = int(os.environ.get("AGGILLI_SYNC_MAX_FILES", "1"))
    if limit < 1 or limit > 100:
        raise RuntimeError("AGGILLI_SYNC_MAX_FILES must be 1..100")
    imported = 0
    with httpx.Client(auth=(user, password), timeout=httpx.Timeout(120, connect=15), follow_redirects=False) as cloud, httpx.Client(timeout=240) as azura:
        files = azura.get(AZURA + "/files", headers=headers)
        files.raise_for_status()
        existing = {normalized_filename(Path(x.get("path", "")).name) for x in files.json()}
        for name, size, etag in list_remote(cloud):
            if imported >= limit:
                break
            output = name if name.lower().endswith(".mp3") else Path(name).stem + ".mp3"
            if normalized_filename(output) in existing or (name in state and state[name].get("etag") == etag):
                print(f"SKIP exists: {output}", flush=True)
                continue
            print(f"SYNC: {name} -> {output}", flush=True)
            with tempfile.TemporaryDirectory(prefix="aggilli-sync-") as td:
                source = Path(td) / name
                download(cloud, name, size, source)
                if name.lower().endswith(".mp4"):
                    converted = Path(td) / output
                    subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y", "-i", str(source), "-map", "0:a:0", "-vn", "-codec:a", "libmp3lame", "-b:a", "192k", str(converted)], check=True, timeout=3600)
                    source = converted
                if source.stat().st_size > 100 * 1024**2:
                    print(f"SKIP exceeds upload limit: {output}", flush=True)
                    continue
                with source.open("rb") as stream:
                    response = azura.post(AZURA + "/files/upload", headers=headers, files={"file": (output, stream, "audio/mpeg")})
                response.raise_for_status()
                uploaded = response.json()
                if not isinstance(uploaded, dict):
                    raise RuntimeError("Unexpected AzuraCast upload response")
                media_id = uploaded.get("id")
                if not isinstance(media_id, int):
                    # Some installations return a wrapper; use the files listing
                    # to resolve the exact uploaded path rather than guessing.
                    listing = azura.get(AZURA + "/files", headers=headers)
                    listing.raise_for_status()
                    matches = [
                        x for x in listing.json()
                        if normalized_filename(Path(x.get("path", "")).name)
                        == normalized_filename(output)
                    ]
                    if len(matches) != 1:
                        raise RuntimeError("Cannot uniquely identify uploaded media")
                    media_id = matches[0].get("id")
                assign_playlists(azura, headers, media_id)
                existing.add(normalized_filename(output))
                imported += 1
                state[name] = {"etag": etag, "azuracast_filename": output}
                temp = STATE_FILE.with_suffix(".tmp")
                temp.write_text(json.dumps(state, ensure_ascii=False, indent=2))
                os.chmod(temp, 0o600)
                os.replace(temp, STATE_FILE)
                print(f"OK: {output}", flush=True)
        print(f"FINISHED: {imported} imported (limit {limit})", flush=True)


if __name__ == "__main__":
    main()
