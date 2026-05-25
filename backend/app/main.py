from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routers import admin, annotations, artworks, auth, cultural_entities, import_notes, museums, research, visits

app = FastAPI(title="CultureGraph API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

upload_path = Path(settings.upload_dir)
upload_path.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(upload_path)), name="uploads")

app.include_router(visits.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(museums.router, prefix="/api")
app.include_router(artworks.router, prefix="/api")
app.include_router(cultural_entities.router, prefix="/api")
app.include_router(annotations.router, prefix="/api")
app.include_router(research.router, prefix="/api")
app.include_router(import_notes.router, prefix="/api")
app.include_router(admin.router, prefix="/api")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
