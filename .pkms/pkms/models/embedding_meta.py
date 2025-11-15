"""EmbeddingMeta model - Embedding metadata per space (text, image, audio)"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class SpaceMeta(BaseModel):
    """Metadata for a single embedding space"""

    model: str = Field(
        ...,
        description="Embedding model name",
        examples=["text-3-large-2025-06", "nomic-embed-text", "clip-vit-large"]
    )

    dim: int = Field(
        ...,
        ge=1,
        description="Embedding dimension"
    )

    updated_at: datetime = Field(
        ...,
        description="ISO 8601 timestamp of last embedding update"
    )

    chunk_hashes: List[str] = Field(
        ...,
        description="List of chunk hashes that have embeddings"
    )

    store_path: Optional[str] = Field(
        None,
        description="Relative path to embedding storage directory",
        examples=["embeddings/text-3-large-2025-06/", "embeddings/nomic-embed-text/"]
    )

    class Config:
        extra = "forbid"


class EmbeddingMeta(BaseModel):
    """Embedding metadata per space (text, image, audio)"""

    text: Optional[SpaceMeta] = None
    image: Optional[SpaceMeta] = None
    audio: Optional[SpaceMeta] = None

    class Config:
        extra = "forbid"
        json_schema_extra = {
            "examples": [
                {
                    "text": {
                        "model": "nomic-embed-text",
                        "dim": 768,
                        "updated_at": "2025-11-14T08:10:01Z",
                        "chunk_hashes": ["a3f2bc1d", "f9e1a2b3", "c4d5e6f7"]
                    }
                }
            ]
        }
