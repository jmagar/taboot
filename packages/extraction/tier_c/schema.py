"""Tier C Pydantic schemas for triple validation."""

from pydantic import BaseModel, Field


class Triple(BaseModel):
    """Represents an extracted knowledge triple (subject, predicate, object)."""

    subject: str = Field(..., min_length=1, description="Subject entity")
    predicate: str = Field(..., min_length=1, description="Relationship type")
    object: str = Field(..., min_length=1, description="Object entity")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Extraction confidence (0-1)")


class ExtractionResult(BaseModel):
    """Result from Tier C LLM extraction containing triples."""

    triples: list[Triple] = Field(default_factory=list, description="Extracted triples")
