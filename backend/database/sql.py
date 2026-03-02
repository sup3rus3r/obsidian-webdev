from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Session

from config import settings


def _build_connect_args() -> dict:
    if "sqlite" in settings.SQLITE_URL:
        return {"check_same_thread": False}
    return {}


engine = create_engine(settings.SQLITE_URL, connect_args=_build_connect_args())
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
