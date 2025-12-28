from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="AI Support Agent")

    from .api import health
    app.include_router(health.router)

    return app
