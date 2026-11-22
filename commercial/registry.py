"""Local, isolated rights registry for commercial staging.

No production endpoints or AzuraCast writes. Persist only rights metadata;
never store contracts, credentials, or customer data in the registry.
"""
import json
import os
import tempfile
from pathlib import Path
from typing import Mapping

from commercial.rights import eligible_for_streaming, commercial_catalog


class RightsRegistry:
    def __init__(self, path: Path):
        self.path = Path(path)

    def read(self) -> dict:
        if not self.path.exists():
            return {}
        data = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or any(not isinstance(k, str) or not isinstance(v, dict) for k, v in data.items()):
            raise ValueError("Invalid rights registry")
        return data

    def save(self, records: Mapping):
        if not isinstance(records, Mapping) or any(not isinstance(k, str) or not k or not isinstance(v, dict) for k, v in records.items()):
            raise ValueError("Invalid registry entries")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=".rights-", dir=self.path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as out:
                json.dump(dict(records), out, ensure_ascii=False, indent=2, sort_keys=True)
                out.write("\n")
                out.flush()
                os.fsync(out.fileno())
            os.chmod(tmp, 0o600)
            os.replace(tmp, self.path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    def put(self, track_id: str, record: dict):
        if not isinstance(track_id, str) or not track_id or not isinstance(record, dict):
            raise ValueError("Invalid track or rights record")
        data = self.read()
        data[track_id] = record
        self.save(data)

    def revoke(self, track_id: str):
        data = self.read()
        if track_id not in data:
            raise KeyError(track_id)
        data[track_id] = {**data[track_id], "status": "revoked"}
        self.save(data)

    def catalog(self, tracks: list[dict], territory: str, today=None):
        return commercial_catalog(tracks, self.read(), territory, today)
