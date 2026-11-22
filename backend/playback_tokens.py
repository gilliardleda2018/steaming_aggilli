"""Short-lived signed playback URLs for the isolated authenticated test player.

Tokens are scoped to a single filename and are not Nextcloud credentials.
Set AGGILLI_STREAM_TOKEN_SECRET to a random 32+ byte secret in the test server.
"""
import base64
import hashlib
import hmac
import os
import time
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from pydantic import BaseModel
from main import require_upload_auth
from cloud_stream import remote_url, proxy_media

router = APIRouter()
TTL_SECONDS = 600

class PlaybackRequest(BaseModel):
    filename: str

def secret() -> bytes:
    value = os.environ.get("AGGILLI_STREAM_TOKEN_SECRET", "")
    if len(value.encode()) < 32:
        raise HTTPException(503, detail="Playback signing not configured")
    return value.encode()

def signature(filename: str, expires: int, key: bytes) -> str:
    payload = f"{expires}:{filename}".encode()
    return base64.urlsafe_b64encode(hmac.new(key, payload, hashlib.sha256).digest()).rstrip(b"=").decode()

def verify(filename: str, expires: int, token: str) -> None:
    remote_url(filename)
    if expires < int(time.time()) or expires > int(time.time()) + TTL_SECONDS:
        raise HTTPException(403, detail="Playback token expired or invalid")
    expected = signature(filename, expires, secret())
    if not hmac.compare_digest(token, expected):
        raise HTTPException(403, detail="Playback token invalid")

@router.post("/playback-token", dependencies=[Depends(require_upload_auth)])
async def playback_token(request: PlaybackRequest):
    remote_url(request.filename)
    expires = int(time.time()) + TTL_SECONDS
    return {"expires": expires, "token": signature(request.filename, expires, secret())}

@router.get("/signed-cloud/{filename}")
@router.head("/signed-cloud/{filename}")
async def signed_stream(filename: str, expires: int, token: str, request: Request, range: str | None = Header(default=None)):
    verify(filename, expires, token)
    return await proxy_media(filename, request.method, range)
