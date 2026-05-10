from urllib.parse import quote_plus
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASS

def make_db_url() -> str:
    user = quote_plus(DB_USER or "")
    pwd = quote_plus(DB_PASS or "")
    host = DB_HOST
    return f"mysql+pymysql://{user}:{pwd}@{host}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"

engine = create_engine(make_db_url(), pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)