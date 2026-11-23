"""Commercial staging API for listeners, catalog decisions and private audio."""
import hashlib
import hmac
import os
import re
import secrets
import sqlite3
import time
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from commercial.listeners import ListenerStore
from commercial.registry import RightsRegistry
from commercial.entitlements import allowed_to_play
from commercial.ani_dj import build_session

app = FastAPI(title="Aggilli Music Commercial Staging", docs_url=None, redoc_url=None, openapi_url=None)


def store():
    return ListenerStore(Path(os.environ.get("AGGILLI_COMMERCIAL_DATA_DIR", "/var/lib/aggilli-music-commercial")) / "listeners.db")


def registry():
    return RightsRegistry(Path(os.environ.get("AGGILLI_COMMERCIAL_DATA_DIR", "/var/lib/aggilli-music-commercial")) / "rights.json")


def enforce_limit(listener_id, scope, limit):
    try:
        retry_after = store().consume_limit(listener_id, scope, limit)
    except (OSError, ValueError, sqlite3.Error):
        raise HTTPException(503, "Request limit unavailable")
    if retry_after:
        raise HTTPException(429, "Too many requests", headers={"Retry-After": str(retry_after)})


class Credentials(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=12, max_length=256)


class SubscriptionInput(BaseModel):
    listener_id: str
    plan: str
    status: str
    access_until: str


def current_listener(authorization: str | None = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Authentication required")
    listener = store().authenticate(authorization[7:])
    if not listener:
        raise HTTPException(401, "Invalid or expired session")
    return listener


def admin(authorization: str | None = Header(default=None)):
    expected = os.environ.get("AGGILLI_COMMERCIAL_ADMIN_TOKEN", "")
    if len(expected) < 32:
        raise HTTPException(503, "Admin not configured")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Admin token required")
    if not secrets.compare_digest(authorization[7:], expected):
        raise HTTPException(403, "Forbidden")


@app.get("/health")
def health():
    return {"status": "ok", "service": "commercial-staging"}


@app.post("/listeners/register", status_code=201)
def register(payload: Credentials):
    try:
        listener_id = store().register(payload.email, payload.password)
    except sqlite3.IntegrityError:
        raise HTTPException(409, "Account already exists")
    except ValueError:
        raise HTTPException(422, "Invalid credentials")
    return {"id": listener_id, "status": "active"}


@app.post("/listeners/login")
def login(payload: Credentials):
    token = store().login(payload.email, payload.password)
    if token is None:
        raise HTTPException(401, "Invalid credentials")
    return {"access_token": token, "token_type": "bearer", "expires_in": 43200}


@app.post("/listeners/logout")
def logout(authorization: str | None = Header(default=None), listener=Depends(current_listener)):
    store().logout(authorization[7:])
    return {"success": True}


@app.get("/listeners/me")
def me(listener=Depends(current_listener)):
    sub = store().subscription(listener["id"])
    return {"id": listener["id"], "status": listener["status"],
            "subscription": sub or {"plan": "free", "status": "inactive"}}


@app.get("/listeners/access/{track_id}")
def check_access(track_id: str, territory: str = "BR", listener=Depends(current_listener)):
    if len(track_id) > 128 or not track_id:
        raise HTTPException(422, "Invalid track")
    # Rights and subscription are loaded server-side, not accepted from the caller.
    rights = registry().read().get(track_id)
    sub = store().subscription(listener["id"])
    return {"track_id": track_id, "allowed": allowed_to_play(listener, sub, rights, territory)}


@app.get("/listeners/playback/{track_id}")
@app.head("/listeners/playback/{track_id}")
def playback(track_id: str, listener=Depends(current_listener)):
    """Authorize each media request against the private staging library."""
    return FileResponse(playback_path(track_id, listener), media_type="audio/mpeg", headers={
        "Cache-Control": "private, no-store",
        "X-Content-Type-Options": "nosniff",
    })


def playback_path(track_id, listener):
    media_dir = os.environ.get("AGGILLI_COMMERCIAL_MEDIA_DIR")
    territory = os.environ.get("AGGILLI_COMMERCIAL_PLAYBACK_TERRITORY", "")
    if not media_dir or not re.fullmatch(r"[A-Z]{2}", territory):
        raise HTTPException(503, "Staging playback not configured")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", track_id):
        raise HTTPException(404, "Track unavailable")
    try:
        rights = registry().read().get(track_id)
        sub = store().subscription(listener["id"])
    except (OSError, ValueError, sqlite3.Error):
        raise HTTPException(503, "Playback authorization unavailable")
    if not allowed_to_play(listener, sub, rights, territory):
        raise HTTPException(403, "Playback not authorized")

    # The staging operator provisions this directory outside any web root.
    # Only direct, regular MP3 assets are served.
    path = Path(media_dir) / f"{track_id}.mp3"
    if path.is_symlink() or not path.is_file():
        raise HTTPException(404, "Track unavailable")
    return path


PLAYBACK_GRANT_TTL = 600


def playback_signature(track_id, session_hash, expires):
    key = os.environ.get("AGGILLI_COMMERCIAL_PLAYBACK_SECRET", "").encode()
    if len(key) < 32:
        raise HTTPException(503, "Playback grants not configured")
    return hmac.new(key, f"{track_id}:{session_hash}:{expires}".encode(), "sha256").hexdigest()


@app.post("/listeners/playback/{track_id}/grant")
def playback_grant(track_id: str, response: Response, authorization: str = Header(), listener=Depends(current_listener)):
    enforce_limit(listener["id"], "playback-grant", 30)
    playback_path(track_id, listener)
    session_hash = hashlib.sha256(authorization[7:].encode()).hexdigest()
    expires = int(time.time()) + PLAYBACK_GRANT_TTL
    signature = playback_signature(track_id, session_hash, expires)
    response.headers["Cache-Control"] = "private, no-store"
    return {"grant": f"{session_hash}.{expires}.{signature}"}


@app.get("/listeners/playback/{track_id}/audio")
@app.head("/listeners/playback/{track_id}/audio")
def playback_with_grant(track_id: str, grant: str):
    match = re.fullmatch(r"([a-f0-9]{64})\.([0-9]{1,12})\.([a-f0-9]{64})", grant)
    if not match or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", track_id):
        raise HTTPException(403, "Invalid playback grant")
    session_hash, expiry, signature = match.groups()
    expires = int(expiry)
    now = int(time.time())
    if not now < expires <= now + PLAYBACK_GRANT_TTL or not hmac.compare_digest(
        signature, playback_signature(track_id, session_hash, expires)
    ):
        raise HTTPException(403, "Invalid or expired playback grant")
    listener = store().authenticate_session_hash(session_hash)
    if not listener:
        raise HTTPException(401, "Invalid or expired session")
    return playback(track_id, listener)


@app.put("/admin/subscriptions", dependencies=[Depends(admin)])
def update_subscription(payload: SubscriptionInput):
    # Staging only: do not grant entitlements from unverified payment callbacks.
    try:
        store().set_subscription(payload.listener_id, payload.plan, payload.status, payload.access_until)
    except KeyError:
        raise HTTPException(404, "Listener not found")
    except ValueError:
        raise HTTPException(422, "Invalid subscription")
    return {"success": True}


class DjRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=400)
    territory: str = Field(default="BR", min_length=2, max_length=2)
    limit: int = Field(default=10, ge=1, le=50)


@app.post("/listeners/dj/session")
def dj_session(payload: DjRequest, listener=Depends(current_listener)):
    """AI-ready session planner. Does not serve media or expose public tracks.

    The catalog is a separately provisioned, rights-reviewed staging snapshot.
    Listener access and billing are always verified server-side.
    """
    from datetime import date
    import json
    enforce_limit(listener["id"], "dj-session", 10)
    catalog_path = Path(os.environ.get(
        "AGGILLI_COMMERCIAL_CATALOG_FILE",
        "/var/lib/aggilli-music-commercial/catalog.json",
    ))
    if not catalog_path.exists():
        raise HTTPException(503, "Licensed staging catalog not configured")
    try:
        tracks = json.loads(catalog_path.read_text(encoding="utf-8"))
        if not isinstance(tracks, list) or len(tracks) > 10000:
            raise ValueError("Invalid catalog")
        subscription = store().subscription(listener["id"])
        if not subscription or subscription.get("status") not in {"active", "trialing"}:
            raise HTTPException(403, "Active subscription required")
        if subscription.get("plan") not in {"premium", "family"}:
            raise HTTPException(403, "Premium subscription required")
        from datetime import datetime, timezone
        expiry = datetime.fromisoformat(subscription["access_until"].replace("Z", "+00:00"))
        if expiry.tzinfo is None or expiry <= datetime.now(timezone.utc):
            raise HTTPException(403, "Subscription expired")
        territory = os.environ.get("AGGILLI_COMMERCIAL_PLAYBACK_TERRITORY") or payload.territory.upper()
        return build_session(
            payload.prompt, tracks, registry().read(), territory,
            limit=payload.limit,
            model_enabled=os.environ.get("AGGILLI_ANI_ENABLED", "false").lower() == "true",
        )
    except (ValueError, TypeError, KeyError, OSError, json.JSONDecodeError):
        raise HTTPException(503, "Commercial catalog unavailable")
