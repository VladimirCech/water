from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, drm, games, sessions

app = FastAPI(title="water API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(games.router, prefix="/games", tags=["games"])
app.include_router(drm.router, prefix="/", tags=["launch"])
app.include_router(sessions.router, prefix="/sessions", tags=["sessions"])


@app.get("/healthz")
def healthz():
    return {"ok": True}
