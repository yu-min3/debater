from pydantic import BaseModel, Field


class DebateRole(BaseModel):
    name: str = Field(default="", description="議論する立場の名前")
    description: str = Field(default="", description="議論する立場の説明")
