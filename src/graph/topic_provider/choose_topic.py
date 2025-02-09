from datetime import datetime

import feedparser

# ライブラリのインポート
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import PromptTemplate
from pydantic import BaseModel, Field
from retry import retry

from src.llm.gemini import vertex_gemini_model as model
from src.model.article import Article
from src.repository.article import FireStoreArticleRepository
from src.repository.article_raw_data import CloudStorageArticleRawRepository
from src.repository.crawl import FireCrawlRepository


class Topic(BaseModel):
    title: str
    url: str


class State(BaseModel):
    choosed_topic: list[Topic] = Field(default=[], description="選択されたトピック")
    successed_topic: list[Topic] = Field(
        default=[], description="検索に成功したトピック"
    )


def fetch_google_news_titles() -> list[Topic]:
    ress_feed = "https://news.google.com/rss?hl=ja&gl=JP&ceid=JP:ja"
    news_feed = feedparser.parse(ress_feed)
    return [
        Topic(title=entry["title"], url=entry["link"]) for entry in news_feed.entries
    ]


def choose_topic(state: State):
    topics = fetch_google_news_titles()

    class DebateTopic(BaseModel):
        debate_topics: list[Topic] = Field(
            description="議論が高いと思われるトピックのタイトルとURLのリスト"
        )

    output_parser = PydanticOutputParser(pydantic_object=DebateTopic)
    topic_num = 5

    prompt_template = PromptTemplate(
        template="""あなたは議論の価値が高そうなトピックを選択するエージェントです。
        以下のトピックの中から、議論の価値が高そうなものを{topic_num}個選択してください。

        ## トピック
        {topics}

        {format_instructions}
        """,
        input_variables=[],
        partial_variables={
            "topic_num": topic_num,
            "topics": topics,
            "format_instructions": output_parser.get_format_instructions(),
        },
    )

    prompt = prompt_template.format_prompt()

    # モデルの出力
    model_output = model.invoke(prompt)
    output = output_parser.parse(model_output)
    state.choosed_topic = output.debate_topics

    return {"choosed_topic": state.choosed_topic}


def crawl_and_save(state: State):
    urls = [topic.url for topic in state.choosed_topic]

    crawl_repository = FireCrawlRepository()
    results = crawl_repository.extract(urls)

    successed_topic = []
    for result in results:
        url = result[0]
        full_text = result[1]
        raw_data = result[2]

        titles = [topic.title for topic in state.choosed_topic if topic.url == url]
        if len(titles) != 1:
            continue

        title = titles[0]
        extract_information = _extract_article_body(full_text=full_text, title=title)

        article_raw_data_repository = CloudStorageArticleRawRepository()
        save_file_path = f"{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
        article_raw_data_repository.save_dict_to_json(
            dict_data=raw_data, file_name=save_file_path
        )

        article = Article(
            url=url,
            user_question="",
            raw_data_path=save_file_path,
            raw_text=full_text,
            extract_information=extract_information,
        )

        article_repository = FireStoreArticleRepository()
        article_repository.save(url=url, article=article)
        successed_topic.append((url, title))

    return {"successed_topic": successed_topic}


@retry(tries=3, exceptions=(Exception,))  # リトライ対象を明確化
def _extract_article_body(full_text: str, title: str):
    # プロンプト
    prompt_template = PromptTemplate(
        template="""
        あなたはスクレイピングした情報からタイトルに関連する本文だけを抽出するエージェントです。
        {scrapying_result}に対して、広告などを削除し、記事の本文だけを抽出して下さい。
        この記事は、以下質問に対し、以下議題で議論するために集めたものです。

        ## タイトル
        {title}

        新しい情報などを加えてはいけませんし、要約してもいけません。
        出力は余計なものをつけず、本文の抽出だけを返して下さい。挨拶や補足も要りません。""",
        input_variables=[],
        partial_variables={
            "scrapying_result": full_text,
            "title": title,
        },
    )

    prompt = prompt_template.format_prompt()

    try:
        # モデルの出力
        model_output = model.invoke(prompt)

    except Exception as e:
        raise e

    return model_output
