import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

def init():
    default_path = os.path.join(os.path.dirname(__file__), "database.sqlite")
    DB_PATH = os.getenv("DB_PATH", default_path)

    # Ensure the directory exists
    db_dir = os.path.dirname(DB_PATH)
    os.makedirs(db_dir, exist_ok=True)

    # Build the proper SQLite URI
    if os.path.isabs(DB_PATH):
        DATABASE_URL = f"sqlite:///{DB_PATH}"
    else:
        DATABASE_URL = f"sqlite:///{os.path.abspath(DB_PATH)}"

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
