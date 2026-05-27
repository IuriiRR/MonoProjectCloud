from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def list_accounts():
    return {"accounts": []}
