import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine
from .routers import financials, insights, documents


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure tables exist even if `python -m app.seed` hasn't been run yet.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Senus PLC Board Report API",
    description=(
        "AI-native financial reporting backend for Senus PLC. Serves growth, "
        "profitability, cash & liquidity, solvency, and returns metrics computed "
        "from AI-extracted historical financial data, plus on-demand AI board commentary."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# Local dev origins are always allowed. In production, set ALLOWED_ORIGINS to
# a comma-separated list of the deployed frontend URL(s), e.g.
#   ALLOWED_ORIGINS=https://senus-board-report-ui.onrender.com
# so the deployed frontend can actually call this API — without this, every
# request from the live site fails CORS even though the API itself is up.
_extra_origins = [
    o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "").split(",") if o.strip()
]
_allowed_origins = ["http://localhost:5173", "http://127.0.0.1:5173"] + _extra_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(financials.router)
app.include_router(insights.router)
app.include_router(documents.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "senus-board-report-api"}