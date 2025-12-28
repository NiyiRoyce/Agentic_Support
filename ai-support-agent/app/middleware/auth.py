from fastapi import Request

async def auth_middleware(request: Request, call_next):
    # placeholder
    return await call_next(request)
