import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base


def init():
    db_vendor = "sqlite:///"
    DB_PATH = os.getenv(
        "DB_PATH",
        os.path.join(os.path.dirname(__file__), "database.sqlite"),
    )
    DATABASE_URL = f"{db_vendor}{DB_PATH}"
    db_engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    Base = declarative_base()
    # Base.metadata.reflect(db_engine)
    return db_engine, SessionLocal, Base


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_engine, SessionLocal, Base = init()
