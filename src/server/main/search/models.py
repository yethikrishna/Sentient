from pydantic import BaseModel

class UnifiedSearchRequest(BaseModel):
    query: str