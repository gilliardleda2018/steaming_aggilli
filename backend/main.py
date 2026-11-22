import asyncio
import secrets
from pathlib import Path

import httpx
from fastapi import FastAPI, File, Header, HTTPException, UploadFile, Depends
from fastapi.responses import JSONResponse

app = FastAPI(
    title="Aggilli Music Upload",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

SECRETS_DIR = Path("/etc/aggilli-music")
AZURA_URL = "http://127.0.0.1:8080/api/station/1/files/upload"
MAX_SIZE = 100 * 1024 * 1024


def authenticate(authorization: str | None):
    expected = (SECRETS_DIR / "upload-token").read_text().strip()

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Autenticação necessária")

    provided = authorization.removeprefix("Bearer ").strip()

    if not secrets.compare_digest(provided, expected):
        raise HTTPException(status_code=403, detail="Acesso negado")



def authenticate_admin(username: str, password: str):
    import bcrypt

    credentials = (
        SECRETS_DIR / "apache-auth" / "upload-users"
    ).read_text().splitlines()

    for entry in credentials:
        stored_user, separator, stored_hash = entry.partition(":")
        if not separator:
            continue

        if stored_user == username and bcrypt.checkpw(
            password.encode("utf-8"),
            stored_hash.encode("utf-8"),
        ):
            return True

    raise HTTPException(
        status_code=401,
        detail="Credenciais administrativas invalidas",
    )


@app.get("/health")
async def health():
    return {"status": "ok", "service": "aggilli-music-upload"}


def require_upload_auth(authorization: str | None = Header(default=None)):
    if authorization and authorization.startswith("Basic "):
        import base64
        import binascii

        try:
            encoded = authorization.removeprefix("Basic ").strip()
            decoded = base64.b64decode(encoded, validate=True).decode("utf-8")
            username, password = decoded.split(":", 1)
        except (ValueError, UnicodeError, binascii.Error):
            raise HTTPException(
                status_code=401,
                detail="Credenciais administrativas invalidas",
            )

        authenticate_admin(username, password)
    else:
        authenticate(authorization)


upload_lock = asyncio.Lock()


@app.post("/upload")
async def upload_music(
    file: UploadFile = File(...),
    _: None = Depends(require_upload_auth),
):
    if upload_lock.locked():
        raise HTTPException(
            status_code=409,
            detail="Outro upload esta em andamento",
        )

    async with upload_lock:
        return await process_upload(file)


async def process_upload(file: UploadFile):
    filename = Path(file.filename or "").name

    if not filename.lower().endswith(".mp3"):
        raise HTTPException(status_code=400, detail="Somente MP3")

    data = await file.read(MAX_SIZE + 1)

    if len(data) > MAX_SIZE:
        raise HTTPException(status_code=413, detail="Arquivo acima de 100 MB")

    if not data or not (
        data.startswith(b"ID3")
        or (len(data) >= 2 and data[0] == 0xFF and (data[1] & 0xE0) == 0xE0)
    ):
        raise HTTPException(status_code=400, detail="MP3 inválido")

    api_key = (SECRETS_DIR / "azuracast-api-key").read_text().strip()

    try:
        async with httpx.AsyncClient(timeout=180) as client:
            existing = await client.get(
                "http://127.0.0.1:8080/api/station/1/files",
                headers={"X-API-Key": api_key},
            )
            existing.raise_for_status()

            for item in existing.json():
                current = Path(item.get("path", "")).name
                if current.casefold() == filename.casefold():
                    raise HTTPException(
                        status_code=409,
                        detail="Arquivo já existe na biblioteca",
                    )

            response = await client.post(
                AZURA_URL,
                headers={"X-API-Key": api_key},
                files={"file": (filename, data, "audio/mpeg")},
            )
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="AzuraCast indisponível")

    if response.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail=f"AzuraCast recusou o upload (HTTP {response.status_code})",
        )

    return JSONResponse({
        "success": True,
        "filename": filename,
        "message": "Arquivo recebido pelo AzuraCast",
    })


# Requests are queued by the unprivileged upload API and consumed by a
# separate root-owned systemd worker. Never run sudo from the web process.
SYNC_QUEUE = Path("/var/lib/aggilli-music/sync-requests")
SYNC_STATUS = Path("/var/lib/aggilli-music/sync-status.json")


@app.post("/sync-nextcloud")
async def start_nextcloud_sync(_: None = Depends(require_upload_auth)):
    import os
    import time
    request = SYNC_QUEUE / "pending"
    try:
        fd = os.open(str(request), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "w") as output:
            output.write(str(int(time.time())) + "\\n")
    except FileExistsError:
        return {"accepted": True, "message": "Já existe uma sincronização aguardando processamento"}
    except OSError:
        raise HTTPException(503, detail="Fila indisponível ou sem permissão de escrita")
    return {"accepted": True, "message": "Solicitação registrada para processamento"}


@app.get("/sync-nextcloud/status")
async def nextcloud_sync_status(_: None = Depends(require_upload_auth)):
    import json
    try:
        status = json.loads(SYNC_STATUS.read_text())
        return {k: status.get(k) for k in ("state", "updated_at", "message")}
    except (FileNotFoundError, ValueError, OSError):
        return {"state": "unknown", "message": "Nenhuma execução registrada"}
