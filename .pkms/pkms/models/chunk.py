"""Chunk model - Text chunk with content-addressable ID"""

from pydantic import BaseModel, Field
from typing import Optional, Literal


class Chunk(BaseModel):
    """Text chunk with content-addressable ID"""

    doc_id: str = Field(
        ...,
        pattern=r"^[0-9A-HJKMNP-TV-Z]{26}$",
        description="ULID of parent document"
    )

    chunk_id: str = Field(
        ...,
        pattern=r"^[0-9A-HJKMNP-TV-Z]{26}:[a-f0-9]{12}$",
        description="Composite ID: doc_id:chunk_hash"
    )

    chunk_hash: str = Field(
        ...,
        pattern=r"^[a-f0-9]{12}$",
        description="Content-addressable hash (xxhash64 first 12 hex chars)"
    )

    chunk_index: int = Field(
        ...,
        ge=0,
        description="Sequential index within document (for ordering)"
    )

    text: str = Field(
        ...,
        min_length=1,
        description="Chunk text content"
    )

    tokens: int = Field(
        ...,
        ge=0,
        description="Token count (for context window management)"
    )

    section: Optional[str] = Field(
        None,
        description="Heading/section name if applicable"
    )

    subsection: Optional[str] = Field(
        None,
        description="Sub-heading name if applicable"
    )

    page: Optional[int] = Field(
        None,
        ge=1,
        description="Page number (for PDFs)"
    )

    modality: Literal["text", "caption", "ocr", "figure", "table", "asr", "summary"] = Field(
        "text",
        description="Content modality type"
    )

    language: str = Field(
        ...,
        pattern=r"^[a-z]{2}$",
        description="ISO 639-1 language code",
        examples=["de", "en", "fr"]
    )

    class Config:
        extra = "forbid"
        json_schema_extra = {
            "examples": [
                {
                    "doc_id": "01HAR6DP2M7G1KQ3Y3VQ8C0Q",
                    "chunk_id": "01HAR6DP2M7G1KQ3Y3VQ8C0Q:a3f2bc1d",
                    "chunk_hash": "a3f2bc1d",
                    "chunk_index": 7,
                    "text": "Bei 300°C wird der Pizzastein optimal heiß...",
                    "tokens": 472,
                    "section": "Ofentemperatur",
                    "subsection": None,
                    "page": None,
                    "modality": "text",
                    "language": "de"
                }
            ]
        }
