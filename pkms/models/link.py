"""Link model - Wikilink structure (forward or backlink)"""

from pydantic import BaseModel, Field
from typing import Optional, Literal


class Link(BaseModel):
    """Wikilink structure (forward or backlink)"""

    raw: str = Field(
        ...,
        description="Raw link text as found in markdown",
        examples=["[[kochen]]", "[[01HAR6DP]]", "[[Pizza|Rezept]]"]
    )

    type: Literal["slug", "id", "alias"] = Field(
        ...,
        description="Type of link resolution"
    )

    target: Optional[str] = Field(
        None,
        pattern=r"^[0-9A-HJKMNP-TV-Z]{26}$",
        description="Resolved ULID of target document, null if unresolved"
    )

    resolved: bool = Field(
        ...,
        description="Whether the link could be resolved"
    )

    context: Optional[str] = Field(
        None,
        max_length=200,
        description="Surrounding text context (for backlinks)"
    )

    class Config:
        extra = "forbid"
        json_schema_extra = {
            "examples": [
                {
                    "raw": "[[kochen]]",
                    "type": "slug",
                    "target": "01HAR6DP2M7G1KQ3Y3VQ8C0Q",
                    "resolved": True,
                    "context": "...bei 300°C [[kochen]]..."
                }
            ]
        }
