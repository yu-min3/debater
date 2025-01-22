from pydantic import BaseModel, Field

from src.model.state.role import DebateRole


class PrepareState(BaseModel):
    agenda: str = Field(
        default="", description="user_inputに対して、洞察を深めるための議題"
    )
    reporter_role: DebateRole = Field(
        default=DebateRole(), description="議題についてレポートする人の立場"
    )
    opponent_role: DebateRole = Field(
        default=DebateRole(), description="レポートを受けて、反証する人の立場"
    )
