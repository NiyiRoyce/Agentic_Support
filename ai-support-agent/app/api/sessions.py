from fastapi import APIRouter

router = APIRouter(prefix="/sessions")

@router.post("/")
async def create_session():
    return {"session_id": "stub"}
