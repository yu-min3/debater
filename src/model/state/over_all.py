import operator
from typing import Annotated

from pydantic import BaseModel, Field

from src.model.state.debater import DebaterState
from src.model.state.prepare import PrepareState
from src.model.state.search import SearchState


class OverAllState(BaseModel):
    user_input: str = Field(
        description="ユーザーが疑問に思ってることなど、議論してほしい内容"
    )
    current_node: str = Field(default="prepare", description="現在のノード")
    prepare_state: PrepareState = Field(
        default=PrepareState(), description="議論の準備状況"
    )
    search_state: SearchState = Field(default=SearchState(), description="検索の状態")
    debater_state: DebaterState = Field(
        default=DebaterState(), description="議論の状態"
    )

    # self_reflection_state: SelfReflectionState = Field(
    #     default=SelfReflectionState(), description="リフレクションの状態"
    # )
    # reflection_needs_retry: bool = Field(
    #     default=True, description="リフレクションを再実行するかどうか"
    # )
    # reflection_task_id: str = Field(
    #     default="", description="リフレクションを行うタスクのID"
    # )
