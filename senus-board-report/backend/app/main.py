from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine
from .routers import financials, insights


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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(financials.router)
app.include_router(insights.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "senus-board-report-api"}
