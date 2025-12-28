from fastapi import APIRouter

router = APIRouter(prefix="/webhooks")

@router.post("/events")
async def webhook():
    return {"status": "received"}
