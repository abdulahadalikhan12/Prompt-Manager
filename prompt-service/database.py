import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# The engine is the actual connection pool to Postgres. Created once,
# reused for the lifetime of the app -- we don't open a new connection
# for every request, that would be wasteful.
engine = create_engine(DATABASE_URL)

# SessionLocal is a factory for creating new database sessions. Each
# request gets its OWN session (see get_db() below) so that concurrent
# requests don't accidentally share or corrupt each other's transactions.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base is what our ORM model classes (in models.py) inherit from.
# SQLAlchemy uses this to know which Python classes map to which
# database tables.
Base = declarative_base()


def get_db():
    """
    FastAPI dependency (used via Depends(get_db) in routers).

    Opens a new session, hands it to the route function, and guarantees
    the session is closed afterward -- even if the route raises an
    exception. This "yield then cleanup" pattern is the standard way
    FastAPI manages anything that needs explicit teardown.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
