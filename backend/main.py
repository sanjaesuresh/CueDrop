"""CueDrop FastAPI application — all endpoints."""

from fastapi import FastAPI

app = FastAPI(title="CueDrop", version="0.1.0")


@app.get("/health")
async def health():
    return {"status": "ok"}
