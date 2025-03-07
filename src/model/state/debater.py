from pydantic import BaseModel, Field, field_validator


class DebaterResponse(BaseModel):
    conclusion: str = Field(description="結論。100文字以内で記述してください。")
    reasons: list[str] = Field(
        description="結論に至った理由。重要なものを合計で5個までに収めて下さい。各理由はそれぞれ200文字以内に収めて下さい。"
    )
    evidence: list[str] = Field(
        description="List of URLs of information used as references in creating the report"
    )

    @field_validator("conclusion")
    def validate_conclusion(cls, value: str) -> str:
        if len(value) > 100:
            raise ValueError(
                "The length of the conclusion must be less than 100 characters."
            )
        return value


class OpponentResponse(BaseModel):
    conclusion: str = Field(description="結論。100文字以内で記述してください。")
    opposite_reasons: list[str] = Field(
        description="反対する理由。重要なものを合計で5個までに収めて下さい。各理由はそれぞれ200文字以内に収めて下さい。"
    )

    @field_validator("conclusion")
    def validate_conclusion(cls, value: str) -> str:
        if len(value) > 100:
            raise ValueError(
                "The length of the conclusion must be less than 100 characters."
            )
        return value


class JudgeResponse(BaseModel):
    summary: str = Field(description="end_judgeをした理由")
    end_judge: bool = Field(
        default=False, description="十分な議論がされ,議論を終えても良いかどうかの判断。"
    )


class DebateHistory(BaseModel):
    report: DebaterResponse
    opponent: OpponentResponse | None = None
    judge: JudgeResponse | None = None


class DebaterState(BaseModel):
    reference_articles: list[tuple[str, str]] = Field(
        default=[], description="URL,記事本文のペアで与えられます。"
    )
    report_history: list[DebateHistory] = Field(
        default=[], description="The history of the reports."
    )
    end_judge: bool = Field(
        default=False, description="十分な議論がされ,議論を終えても良いかどうかの判断。"
    )
    max_debate_num: int = Field(default=3, description="議論の最大回数")

    def format_report_history(self, role_name: str, counter_role_name: str) -> str:
        """report_historyをマークダウン形式で整形して返す."""
        if len(self.report_history) == 0:
            return "## 過去の議論履歴：なし\n"  # 履歴がない場合のメッセージ

        markdown_output = "# 過去の議論履歴\n"
        count = 0
        for history in self.report_history:
            count += 1
            markdown_output += f"## {count}回目の議論：\n"
            markdown_output += f"## {role_name}の立場の意見：\n"
            markdown_output += f"### summary: {history.report.reasons}\n"
            markdown_output += f"### evidence:{history.report.evidence}\n"
            for evidence in history.report.evidence:
                markdown_output += f"- {evidence}\n"  # evidenceをリスト形式で表示
            markdown_output += f"### conclusion:{history.report.conclusion}\n"
            markdown_output += "\n"  # レポートごとに空行を追加

            if history.opponent:  # 反論がある場合
                markdown_output += f"## {counter_role_name}の反論：\n"
                markdown_output += "### 反対理由:\n"
                for reason in history.opponent.opposite_reasons:
                    markdown_output += f"- {reason}\n"
                markdown_output += f"### conclusion:{history.opponent.conclusion}\n"
                markdown_output += "\n"

            if history.judge:  # 判定がある場合
                markdown_output += "## 裁判官の判定：\n"
                markdown_output += f"### summary: {history.judge.summary}\n"
                markdown_output += f"### 議論終了フラグ: {history.judge.end_judge}\n"
                markdown_output += "\n"

        return markdown_output
