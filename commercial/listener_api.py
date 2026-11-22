"""Commercial staging API for listeners and read-only licensed catalog decisions.

NOT connected to public AzuraCast, billing or production playback.
"""
import os
import secrets
import sqlite3
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from commercial.listeners import ListenerStore
from commercial.registry import RightsRegistry
from commercial.entitlements import allowed_to_play

app = FastAPI(title="Aggilli Music Commercial Staging", docs_url=None, redoc_url=None, openapi_url=None)


def store():
    return ListenerStore(Path(os.environ.get("AGGILLI_COMMERCIAL_DATA_DIR", "/var/lib/aggilli-music-commercial")) / "listeners.db")


def registry():
    return RightsRegistry(Path(os.environ.get("AGGILLI_COMMERCIAL_DATA_DIR", "/var/lib/aggilli-music-commercial")) / "rights.json")


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
