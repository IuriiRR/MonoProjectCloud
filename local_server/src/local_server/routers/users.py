from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from local_server.database import get_session
from local_server.models import User

router = APIRouter()

@router.get("/")
def list_users(session: Session = Depends(get_session)):
    users = session.exec(select(User)).all()
    return {"users": users}
