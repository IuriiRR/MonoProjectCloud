from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def get_report():
    return {"report": "Not implemented"}
