from typing import Annotated

from pydantic import BaseModel, Field


def add_url(a: list, b: str | None) -> list:
    if b is not None:
        a.append(b)
        return a
    return a


class SearchState(BaseModel):
    search_words: list[list[str]] = Field(
        default=[], description="The search words that the agent has used."
    )
    search_urls: list[str] = Field(
        default=[], description="The search urls that the agent has used."
    )
    crawled_urls: Annotated[list[str], add_url] = Field(
        default=[], description="The urls that the agent has crawled."
    )
    already_crawled_urls: Annotated[list[str], add_url] = Field(
        default=[], description="The urls that the agent has already crawled."
    )
    raw_crawl_results: list[tuple[str, str,str]] = Field(
        default=[], description="URLとクロールしたテキスト。"
    )


# 並列ノード間でのみ値を受け渡すState
class CrawlParallelState(BaseModel):
    url: str
    user_input: str
    agenda: str

# 並列ノード間でのみ値を受け渡すState
class ExtractParallelState(BaseModel):
    url: str
    user_input: str
    agenda: str
    raw_text:str
    raw_data_path:str
