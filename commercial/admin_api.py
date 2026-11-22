"""Isolated commercial rights administration API (NOT mounted in production).

Run separately after provisioning AGGILLI_COMMERCIAL_ADMIN_TOKEN and a private
data directory. This module does not expose or proxy AzuraCast media.
"""
import fcntl
import json
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from commercial.registry import RightsRegistry

app = FastAPI(title="Aggilli Music Commercial Rights Admin", docs_url=None, redoc_url=None, openapi_url=None)
DATA_DIR = Path(os.environ.get("AGGILLI_COMMERCIAL_DATA_DIR", "/var/lib/aggilli-music-commercial"))
REGISTRY = DATA_DIR / "rights.json"
AUDIT = DATA_DIR / "rights-audit.jsonl"
LOCK = DATA_DIR / ".registry.lock"


class RightsInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str = Field(pattern="^(pending|approved|revoked)$")
    license_type: str = Field(pattern="^(interactive_streaming|web_radio)$")
    agreement_reference: str = Field(min_length=1, max_length=200)
    rights_holder: str = Field(min_length=1, max_length=200)
    recording_rights_confirmed: bool
    composition_rights_confirmed: bool
    territories: list[str] = Field(min_length=1, max_length=100)
    valid_from: str
    valid_until: str


def admin_auth(authorization: str | None = Header(default=None)):
    token = os.environ.get("AGGILLI_COMMERCIAL_ADMIN_TOKEN", "")
    if len(token) < 32:
        raise HTTPException(503, "Admin token not configured")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Admin token required", headers={"WWW-Authenticate": "Bearer"})
    if not secrets.compare_digest(authorization[7:], token):
        raise HTTPException(403, "Invalid admin token")


def write_audit(action: str, track_id: str):
    entry = {"timestamp": datetime.now(timezone.utc).isoformat(), "action": action, "track_id": track_id}
    fd = os.open(AUDIT, os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "a", encoding="utf-8") as out:
        out.write(json.dumps(entry, ensure_ascii=False) + "\n")
        out.flush()
        os.fsync(out.fileno())


def mutate(action: str, track_id: str, record: dict | None = None):
    DATA_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(LOCK, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "r+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        registry = RightsRegistry(REGISTRY)
        if action == "upsert":
            registry.put(track_id, record)
        else:
            registry.revoke(track_id)
        write_audit(action, track_id)


@app.get("/health")
def health():
    return {"status": "ok", "service": "aggilli-music-commercial-admin"}


@app.get("/admin/rights", dependencies=[Depends(admin_auth)])
def list_rights():
    return RightsRegistry(REGISTRY).read()


@app.put("/admin/rights/{track_id}", dependencies=[Depends(admin_auth)])
def put_rights(track_id: str, payload: RightsInput):
    if len(track_id) > 128 or not track_id.strip() or "/" in track_id:
        raise HTTPException(422, "Invalid track ID")
    from datetime import date
    try:
        start, end = date.fromisoformat(payload.valid_from), date.fromisoformat(payload.valid_until)
    except ValueError:
        raise HTTPException(422, "Invalid license dates")
    if end < start or any(len(t) != 2 or not t.isalpha() or t != t.upper() for t in payload.territories):
        raise HTTPException(422, "Invalid license period or territories")
    mutate("upsert", track_id, payload.model_dump())
    return {"success": True, "track_id": track_id}


@app.post("/admin/rights/{track_id}/revoke", dependencies=[Depends(admin_auth)])
def revoke_rights(track_id: str):
    try:
        mutate("revoke", track_id)
    except KeyError:
        raise HTTPException(404, "Unknown track")
    return {"success": True, "track_id": track_id, "status": "revoked"}
