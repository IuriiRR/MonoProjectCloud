import os
from sqlmodel import SQLModel, create_engine, Session

# Put database inside secrets/ or a persistent local volume folder
DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "secrets")
os.makedirs(DB_DIR, exist_ok=True)
sqlite_file_name = os.path.join(DB_DIR, "cloudapi_local.db")

sqlite_url = f"sqlite:///{sqlite_file_name}"

connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, echo=False, connect_args=connect_args)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
