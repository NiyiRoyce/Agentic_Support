from fastapi import APIRouter

router = APIRouter(prefix="/chat")

@router.post("/")
async def chat():
    return {"message": "chat endpoint (stub)"}
