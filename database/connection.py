import os

from dotenv import load_dotenv

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
SQLALCHEMY_ECHO = os.getenv("SQLALCHEMY_ECHO", "0").strip().lower() in {"1", "true", "yes", "on"}

if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found in .env")

# SQLAlchemy Engine
engine = create_engine(
    DATABASE_URL,
    echo=SQLALCHEMY_ECHO,
    future=True,
    pool_pre_ping=True,
    pool_recycle=1800,
)

# Session Factory
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    future=True
)
