from pydantic import BaseModel, Field


class JourneyTrait(BaseModel):
    """Value object representing a trait associated with a journey"""
    
    name: str = Field(..., min_length=1, max_length=255)
    confidence: float = Field(..., ge=0.0, le=1.0)
