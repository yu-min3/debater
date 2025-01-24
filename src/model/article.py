from pydantic import BaseModel, Field


class Article(BaseModel):
    url: str = Field(..., description="記事のURL")
    user_question: str = Field(..., description="ユーザーの質問")
    raw_data_path: str = Field(..., description="生データの保存先")
    raw_text:str = Field(..., description="生データ")
    extract_information: str | None = Field(None, description="抽出した情報")
