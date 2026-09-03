import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Load backend/.env (if present) into the environment. This is the earliest,
# most widely-imported module in the app (main.py, seed.py, ai_extraction.py,
# every router — all import from here directly or indirectly), so loading
# .env here guarantees GROQ_API_KEY / ANTHROPIC_API_KEY are available before
# anything that needs them (llm_client.py) is ever called.
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

DB_PATH = os.path.join(os.path.dirname(__file__), "senus.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()