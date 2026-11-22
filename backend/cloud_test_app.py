"""Loopback-only test application for authenticated cloud streaming.

Start with: uvicorn cloud_test_app:app --host 127.0.0.1 --port 8450
Never expose this test server to the public internet.
"""
from fastapi import FastAPI
from cloud_stream import router

app = FastAPI(
    title="Aggilli Music Cloud Streaming - Isolated Test",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
app.include_router(router)

@app.get("/health")
async def health():
    return {"status": "ok", "environment": "cloud-stream-test"}
