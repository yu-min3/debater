from pydantic import BaseModel, Field


class Article(BaseModel):
    url: str = Field(..., description="記事のURL")
    user_question: str = Field(..., description="ユーザーの質問")
    raw_data_path: str = Field(..., description="生データの保存先")
    extract_information: str = Field(..., description="抽出した情報")
