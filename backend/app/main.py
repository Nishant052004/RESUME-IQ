"""ResumeIQ — FastAPI application entry point (wires all modules together)."""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .auth.router import router as auth_router
from .config import settings
from .database import Base, engine
from .ingestion.router import router as ingestion_router
from .review.router import router as review_router
from .scoring.router import router as scoring_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="AI resume screening & candidate ranking with explainable scores, "
                "PII redaction, bias-aware ranking and human-in-the-loop review.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(ingestion_router)
app.include_router(scoring_router)
app.include_router(review_router)


@app.get("/api/health", tags=["meta"])
def health():
    return {"status": "ok", "app": settings.APP_NAME}


FRONTEND_DIST = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist"))
if os.path.isdir(FRONTEND_DIST):
    # Serve the built SPA (single-container deploys). Registered after the /api
    # routers, so API routes win; unknown paths fall back to index.html so
    # client-side routes survive a hard refresh.
    index_file = os.path.join(FRONTEND_DIST, "index.html")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        candidate = os.path.normpath(os.path.join(FRONTEND_DIST, full_path))
        if full_path and candidate.startswith(FRONTEND_DIST) and os.path.isfile(candidate):
            return FileResponse(candidate)
        return FileResponse(index_file)
