"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.deps import _get_store
from backend.routes.bunq_oauth import router as bunq_router
from backend.routes.chat import router as chat_router
from backend.routes.onboard import router as onboard_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Eagerly initialise the SQLite store and create tables on startup.
    _get_store()
    yield


app = FastAPI(title="bunq Nest", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(onboard_router, prefix="/onboard")
app.include_router(chat_router, prefix="/chat")
app.include_router(bunq_router, prefix="/bunq")


@app.get("/health")
def health():
    return {"ok": True}
