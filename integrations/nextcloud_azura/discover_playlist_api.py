#!/usr/bin/env python3
"""Discover playlist/media update routes in the running AzuraCast OpenAPI schema.

Read-only. Never sends POST, PUT, PATCH or DELETE.
"""
import json
from pathlib import Path
import httpx

BASE = "http://127.0.0.1:8080"
KEY = Path("/etc/aggilli-music/azuracast-api-key").read_text().strip()
CANDIDATES = ("/api/openapi.json", "/api/swagger.json", "/api/openapi", "/api/docs.json")

with httpx.Client(headers={"X-API-Key": KEY}, timeout=20) as client:
    for route in CANDIDATES:
        try:
            response = client.get(BASE + route)
            print(f"{route}: HTTP {response.status_code}")
            if response.status_code != 200:
                continue
            schema = response.json()
            paths = schema.get("paths", {})
            if not isinstance(paths, dict) or not paths:
                continue
            print("=== POSSIBLE MEDIA/PLAYLIST OPERATIONS ===")
            for path, methods in paths.items():
                lower = path.lower()
                if "playlist" not in lower and "file" not in lower and "ondemand" not in lower:
                    continue
                if not isinstance(methods, dict):
                    continue
                for method, details in methods.items():
                    if method.lower() not in {"get", "put", "post", "patch", "delete"}:
                        continue
                    if not isinstance(details, dict):
                        continue
                    print(method.upper(), path, "-", details.get("operationId", details.get("summary", "")))
                    if method.lower() in {"put", "post", "patch"}:
                        request = details.get("requestBody", {})
                        if isinstance(request, dict):
                            print("  request content types:", list(request.get("content", {}).keys()))
                            print("  request schema:", json.dumps(request.get("content", {}), ensure_ascii=False)[:650])
            break
        except (ValueError, httpx.HTTPError) as exc:
            print(type(exc).__name__, str(exc)[:120])
    else:
        print("No OpenAPI JSON found. No changes made.")
