"""Loopback-only test application for authenticated cloud streaming.

Start with: uvicorn cloud_test_app:app --host 127.0.0.1 --port 8450
Never expose this test server to the public internet.
"""
from pathlib import Path
from fastapi import FastAPI, Depends, Request
from fastapi.responses import HTMLResponse
from main import require_upload_auth
from cloud_stream import router
from cloud_catalog import router as catalog_router

app = FastAPI(
    title="Aggilli Music Cloud Streaming - Isolated Test",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
app.include_router(router)
app.include_router(catalog_router)

@app.get("/health")
async def health():
    return {"status": "ok", "environment": "cloud-stream-test"}

@app.get("/test-player", response_class=HTMLResponse, dependencies=[Depends(require_upload_auth)])
async def test_player():
    page = Path(__file__).with_name("cloud_test_player.html").read_text(encoding="utf-8")
    return HTMLResponse(
        page,
        headers={
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; media-src 'self'; connect-src 'self';",
        },
    )


@app.exception_handler(401)
async def authentication_required(request: Request, exc):
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=401,
        content={"detail": "Autenticacao necessaria"},
        headers={"WWW-Authenticate": 'Basic realm="Aggilli Music - Teste"'},
    )
