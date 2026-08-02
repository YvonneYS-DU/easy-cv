"""
Multi-agent resume system — FastAPI entrypoint.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure agi_agents llm_wrapper is importable (sibling monorepo package)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agi_agents"))

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from resume_agents.api.routes import router
from resume_agents.orchestrator import ResumeOrchestrator

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
FORCE_MOCK = os.getenv("RESUME_MOCK", "").lower() in {"1", "true", "yes"}
USE_MOCK = FORCE_MOCK or not API_KEY

if USE_MOCK:
    orchestrator = ResumeOrchestrator(mock=True)
else:
    from langchain_openai import ChatOpenAI

    model = ChatOpenAI(
        model_name=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        temperature=0,
        api_key=API_KEY,
    )
    orchestrator = ResumeOrchestrator(model=model, mock=False)

app = FastAPI(
    title="Easy CV API",
    description="Easy CV — materials, resume generation, JD matching, block rewrite",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/api/v1/meta")
def meta():
    return {
        "status": "ok",
        "service": "easy-cv",
        "mode": "mock" if USE_MOCK else "llm",
        "model": os.getenv("LLM_MODEL", "gpt-4o-mini") if not USE_MOCK else None,
    }


@app.get("/health")
def health():
    return {"status": "healthy", "mode": "mock" if USE_MOCK else "llm"}


@app.get("/")
def spa_index():
    index = STATIC_DIR / "index.html"
    if index.exists():
        return FileResponse(index)
    return {
        "status": "ok",
        "service": "easy-cv",
        "mode": "mock" if USE_MOCK else "llm",
        "hint": "frontend not built yet; run frontend build into ./static",
    }


if STATIC_DIR.exists():
    assets_dir = STATIC_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")


@app.get("/{full_path:path}")
def spa_fallback(full_path: str):
    # Keep API 404s explicit; only serve SPA assets/fallback for non-API paths.
    if full_path.startswith("api/") or full_path in {"docs", "openapi.json", "redoc", "health"}:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Not Found")
    if not STATIC_DIR.exists():
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Not Found")
    candidate = STATIC_DIR / full_path
    if candidate.is_file():
        return FileResponse(candidate)
    index = STATIC_DIR / "index.html"
    if index.exists():
        return FileResponse(index)
    from fastapi import HTTPException

    raise HTTPException(status_code=404, detail="Not Found")


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8002"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
