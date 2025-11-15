"""Status model - Document status and relevance tracking"""

from pydantic import BaseModel, Field
from typing import Optional


class Status(BaseModel):
    """Document status and relevance tracking"""

    relevance_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Computed relevance score (0.0-1.0)"
    )

    archived: bool = Field(
        ...,
        description="Whether document is archived"
    )

    consolidated_into: Optional[str] = Field(
        None,
        pattern=r"^[0-9A-HJKMNP-TV-Z]{26}$",
        description="ULID of synthesis document if consolidated, null otherwise"
    )

    human_edited: Optional[bool] = Field(
        None,
        description="Whether document was manually edited after agent creation"
    )

    class Config:
        extra = "forbid"
        json_schema_extra = {
            "examples": [
                {
                    "relevance_score": 0.82,
                    "archived": False,
                    "consolidated_into": None,
                    "human_edited": False
                }
            ]
        }
