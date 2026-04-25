from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.routers.onboard import router as onboard_router

app = FastAPI(title="bunq Nest", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(onboard_router, prefix="/onboard")


@app.get("/health")
def health():
    return {"status": "ok"}
