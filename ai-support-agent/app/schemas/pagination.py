from pydantic import BaseModel

class Page(BaseModel):
    items: list
    total: int
