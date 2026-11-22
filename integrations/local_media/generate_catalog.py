#!/usr/bin/env python3
"""Generate a safe local-media catalog from explicitly published MP3/MP4 files.

Reads only /srv/aggilli-music/media/{musicas,videos}, never follows symlinks.
Does not alter AzuraCast or WebDAV catalogs.
"""
import json
import os
from pathlib import Path
from urllib.parse import quote

ROOT = Path("/srv/aggilli-music/media")
OUTPUT = Path("/var/www/aggilli-music/catalogo-local.json")
KINDS = {"musicas": ".mp3", "videos": ".mp4"}


def generate(root: Path = ROOT) -> list[dict]:
    tracks = []
    for directory, extension in KINDS.items():
        folder = root / directory
        if not folder.is_dir() or folder.is_symlink():
            continue
        for item in sorted(folder.iterdir(), key=lambda p: p.name.casefold()):
            if item.is_symlink() or not item.is_file() or item.suffix.lower() != extension:
                continue
            if item.name.startswith("."):
                continue
            stat = item.stat()
            if stat.st_size <= 0:
                continue
            tracks.append({
                "track_id": "local:" + directory + "/" + item.name,
                "source": "local",
                "format": extension[1:],
                "filename": item.name,
                "media": {"title": item.stem},
                "size_bytes": stat.st_size,
                "stream_url": "media/" + directory + "/" + quote(item.name, safe=""),
            })
    return tracks


def main() -> None:
    data = {"tracks": generate(), "source": "local"}
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temp = OUTPUT.with_name(OUTPUT.name + ".tmp")
    try:
        with temp.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.chmod(temp, 0o644)
        os.replace(temp, OUTPUT)
    finally:
        temp.unlink(missing_ok=True)
    print(f"Catalogo local: {len(data['tracks'])} arquivos -> {OUTPUT}")


if __name__ == "__main__":
    main()
