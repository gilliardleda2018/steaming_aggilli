#!/usr/bin/env python3
"""Read-only diagnostic of AzuraCast On-Demand media and playlist associations."""
from collections import Counter
from pathlib import Path
import httpx

ROOT = "http://127.0.0.1:8080/api/station/1"


def main():
    key = Path("/etc/aggilli-music/azuracast-api-key").read_text().strip()
    with httpx.Client(headers={"X-API-Key": key}, timeout=30) as client:
        files_response = client.get(ROOT + "/files")
        files_response.raise_for_status()
        ondemand_response = client.get(ROOT + "/ondemand")
        ondemand_response.raise_for_status()
        playlists_response = client.get(ROOT + "/playlists")
        playlists_response.raise_for_status()
        files = files_response.json()
        ondemand = ondemand_response.json()
        playlists = playlists_response.json()

    if not all(isinstance(x, list) for x in (files, ondemand, playlists)):
        raise RuntimeError("Unexpected AzuraCast response")
    print(f"Files: {len(files)}; On-Demand entries: {len(ondemand)}")
    for playlist in playlists:
        print("Playlist:", {k: playlist.get(k) for k in ("id", "name", "type", "source", "is_enabled", "is_ondemand")})

    assignments = Counter()
    for item in files:
        playlist_ids = item.get("playlists") or []
        assignments[str(playlist_ids)] += 1
    print("Playlist assignment distribution:", dict(assignments))
    print("On-Demand media IDs (sample):", [x.get("media", {}).get("id") for x in ondemand[:3] if isinstance(x.get("media"), dict)])
    print("Files with no playlists (sample):", [
        {"id": x.get("id"), "path": x.get("path")}
        for x in files if not x.get("playlists")
    ][:5])
    print("Read-only diagnostic complete. No changes made.")


if __name__ == "__main__":
    main()
