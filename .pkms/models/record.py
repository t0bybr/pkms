"""Record model - Document metadata record (derived from markdown + frontmatter)"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime

from .link import Link
from .status import Status
from .embedding_meta import EmbeddingMeta


class Agent(BaseModel):
    """Agent metadata"""

    id: str = Field(
        ...,
        description="Agent identifier that created/modified this record"
    )

    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Agent confidence score"
    )

    reviewed: bool = Field(
        ...,
        description="Whether human reviewed agent output"
    )

    class Config:
        extra = "forbid"


class Source(BaseModel):
    """Git source metadata"""

    repo: str = Field(
        ...,
        description="Git repository URL"
    )

    commit: str = Field(
        ...,
        pattern=r"^[a-f0-9]{7,40}$",
        description="Git commit hash"
    )

    class Config:
        extra = "forbid"


class Record(BaseModel):
    """Document metadata record (derived from markdown + frontmatter)"""

    id: str = Field(
        ...,
        pattern=r"^[0-9A-HJKMNP-TV-Z]{26}$",
        description="ULID of document"
    )

    slug: str = Field(
        ...,
        pattern=r"^[a-z0-9-]{1,60}$",
        description="URL-safe slug derived from title"
    )

    path: str = Field(
        ...,
        pattern=r"^vault/.+\.md$",
        description="Relative path to markdown file in vault/"
    )

    title: str = Field(
        ...,
        min_length=1,
        description="Document title (from frontmatter)"
    )

    tags: List[str] = Field(
        default_factory=list,
        description="Tags (from frontmatter)"
    )

    aliases: List[str] = Field(
        default_factory=list,
        description="Alternative names for linking"
    )

    categories: List[str] = Field(
        default_factory=list,
        description="Categories (from frontmatter)"
    )

    language: str = Field(
        ...,
        pattern=r"^[a-z]{2}$",
        description="ISO 639-1 language code (auto-detected or from frontmatter)"
    )

    created: datetime = Field(
        ...,
        description="ISO 8601 creation timestamp (from file or frontmatter)"
    )

    updated: datetime = Field(
        ...,
        description="ISO 8601 last modified timestamp (from file mtime)"
    )

    date_semantic: Optional[datetime] = Field(
        None,
        description="Semantic date (when the event occurred, from frontmatter)"
    )

    full_text: str = Field(
        ...,
        description="Full markdown content (without frontmatter)"
    )

    links: List[Link] = Field(
        default_factory=list,
        description="Forward links (outgoing wikilinks)"
    )

    backlinks: List[Link] = Field(
        default_factory=list,
        description="Backlinks (incoming wikilinks from other docs)"
    )

    content_hash: str = Field(
        ...,
        pattern=r"^sha256:[a-f0-9]{64}$",
        description="SHA256 hash of full_text"
    )

    file_hash: str = Field(
        ...,
        pattern=r"^sha256:[a-f0-9]{64}$",
        description="SHA256 hash of entire file (including frontmatter)"
    )

    status: Status = Field(
        ...,
        description="Document status and relevance"
    )

    agent: Optional[Agent] = Field(
        None,
        description="Agent metadata"
    )

    embedding_meta: Optional[EmbeddingMeta] = Field(
        None,
        description="Embedding metadata per space"
    )

    facets: Dict[str, Any] = Field(
        default_factory=dict,
        description="Type-specific facets (invoice, pdf, etc.)"
    )

    source: Optional[Source] = Field(
        None,
        description="Git source metadata"
    )

    doc_type: Literal["note", "pdf", "invoice", "email", "image"] = Field(
        "note",
        description="Document type for faceting"
    )

    class Config:
        extra = "forbid"
        json_schema_extra = {
            "examples": [
                {
                    "id": "01HAR6DP2M7G1KQ3Y3VQ8C0Q",
                    "slug": "pizza-knusprig",
                    "path": "vault/2025-11/pizza-knusprig--01HAR6DP2M7G1KQ3Y3VQ8C0Q.md",
                    "title": "Pizza – knusprig bei 300°C",
                    "tags": ["kochen", "ofen"],
                    "categories": ["Kochen"],
                    "language": "de",
                    "created": "2025-01-10T14:22:31Z",
                    "updated": "2025-11-13T09:03:00Z",
                    "full_text": "...",
                    "content_hash": "sha256:abc123...",
                    "file_hash": "sha256:def456...",
                    "status": {
                        "relevance_score": 0.82,
                        "archived": False
                    }
                }
            ]
        }
