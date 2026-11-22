#!/usr/bin/env python3
"""Refresh Winamp catalog using only AzuraCast's actual On-Demand endpoint."""
import json
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

import httpx

CATALOG = Path("/var/www/aggilli-music/catalogo.json")
API_KEY = Path("/etc/aggilli-music/azuracast-api-key")
URL = "http://127.0.0.1:8080/api/station/1/ondemand"


def main():
    key = API_KEY.read_text().strip()
    response = httpx.get(URL, headers={"X-API-Key": key}, timeout=30)
    response.raise_for_status()
    items = response.json()
    if not isinstance(items, list) or not items:
        raise RuntimeError("AzuraCast returned an empty or invalid On-Demand catalog")
    ids = set()
    for item in items:
        if not isinstance(item, dict):
            raise RuntimeError("Invalid track")
        track_id = item.get("track_id")
        download_url = item.get("download_url")
        if not isinstance(track_id, str) or not track_id or track_id in ids:
            raise RuntimeError("Missing or duplicate track id")
        if download_url != f"/api/station/1/ondemand/download/{track_id}":
            raise RuntimeError("Unexpected download route")
        if not isinstance(item.get("media"), dict):
            raise RuntimeError("Missing media metadata")
        ids.add(track_id)

    # Avoid replacing a previously healthy catalog with an unexpectedly
    # smaller one; preserve the original until investigated.
    if CATALOG.exists():
        previous = json.loads(CATALOG.read_text(encoding="utf-8"))
        if isinstance(previous, list) and len(items) < len(previous):
            raise RuntimeError(f"Catalog shrank from {len(previous)} to {len(items)}; refusing update")
        backup = CATALOG.with_name(
            "catalogo.json.backup-" + datetime.now().strftime("%Y%m%d-%H%M%S")
        )
        shutil.copy2(CATALOG, backup)
    else:
        raise RuntimeError("Existing player catalog missing; refusing creation")

    fd, name = tempfile.mkstemp(prefix=".catalogo-", suffix=".json", dir=CATALOG.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(items, file, ensure_ascii=False, indent=2)
            file.write("\n")
        shutil.copymode(CATALOG, name)
        os.replace(name, CATALOG)
    finally:
        if os.path.exists(name):
            os.unlink(name)
    print(f"Winamp catalog updated: {len(items)} On-Demand tracks")


if __name__ == "__main__":
    main()
