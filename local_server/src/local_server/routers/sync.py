from fastapi import APIRouter

router = APIRouter()

@router.post("/accounts")
def sync_accounts():
    return {"status": "ok"}

@router.post("/transactions")
def sync_transactions():
    return {"status": "ok"}
