from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from local_server.database import get_session
from local_server.models import User

router = APIRouter()


class UserCreate(BaseModel):
    user_id: str
    username: Optional[str] = None
    mono_token: str


@router.get("/")
def list_users(session: Session = Depends(get_session)):
    users = session.exec(select(User)).all()
    return {"users": users}


@router.post("/")
def create_user(body: UserCreate, session: Session = Depends(get_session)):
    existing = session.get(User, body.user_id)
    if existing:
        raise HTTPException(status_code=409, detail=f"User {body.user_id} already exists")
    user = User(user_id=body.user_id, username=body.username, mono_token=body.mono_token)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user
