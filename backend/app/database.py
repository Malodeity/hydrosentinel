# Database connection. engine = the connection pool, SessionLocal = a factory for sessions, Base = the parent class of every table in models.py.
# get_db() is the FastAPI dependency that gives each request its own session and always closes it.

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


# this creates the database connection using the url from the environment settings
engine = create_engine(settings.database_url, future=True)
# this builds a reusable database session factory for every request or script
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    # this opens one database session for the current request and closes it when the request finishes
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
