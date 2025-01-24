from pydantic import BaseModel, Field


class SelfReflection(BaseModel):
    needs_retry: bool | None = Field(
        default=None,
        description="タスクの実行結果は適切だったと思いますか？貴方の判断を真偽値で示してください。",
    )
    confidence: float | None = Field(
        default=None,
        description="あなたの判断に対するあなたの自信度合いを0から1の間で示してください。",
    )
    reflection_reasons: list[str] | None = Field(
        default=None,
        description="タスクの実行結果の適切性とそれに対する自信度について、判断に至った理由を簡潔に列挙して下さい。",
    )
    reflection: str | None = Field(
        default=None,
        description="このタスクに取り組んだ際のあなたの思考プロセスを振り返ってください。何か改善できる点はありましたか? 次に同様のタスクに取り組む際に、より良い結果を出すための教訓を2〜3文程度で簡潔に述べてください。",
    )


class SelfReflectionState(BaseModel):
    max_reflection_num: int = Field(default=3, description="reflectionする最大回数")
    current_task_id: str = Field(default="", description="タスクのID")
    current_task: str = Field(default="", description="タスクの内容")
    current_result: str = Field(default="", description="タスクの結果")
    reflection_instruction: str = Field(default="", description="リフレクションの指示")
    reflections: dict[str, list[SelfReflection]] = Field(
        default={}, description="リフレクションの内容"
    )
