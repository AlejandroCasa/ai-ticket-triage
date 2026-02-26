from pydantic import BaseModel, Field
from typing import Optional

class ClassificationRequest(BaseModel):
    """
    DTO for incoming classification requests.
    """
    description: str = Field(..., min_length=5, description="The raw text of the IT ticket")
    request_id: Optional[str] = Field(None, description="Optional external ID for tracing")

class ClassificationResponse(BaseModel):
    """
    DTO for the classification result.
    """
    category: str
    confidence_source: str = Field(..., description="Source of the truth: 'AI_Generated' or 'Cache_Hit'")
    ticket_id: Optional[int] = Field(None, description="Internal DB ID if persisted")