from datetime import datetime
from pprint import pprint

from firecrawl import FirecrawlApp

# ライブラリのインポート
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import PromptTemplate
from langgraph.types import Send
from pydantic import BaseModel, Field
from retry import retry

from src.llm.gemini import gemini_model as model
from src.model.article import Article
from src.model.state.over_all import OverAllState
from src.model.state.search import CrawlParallelState
from src.repository.article import FireStoreArticleRepository
from src.repository.article_raw_data import CloudStorageArticleRawRepository
from src.repository.google_search import GoogleSearchRepository


@retry(tries=3)
def make_search_words(state: OverAllState):
    class SearchWord(BaseModel):
        google_search_words: list[list[str]] = Field(
            description="google検索用の単語リスト"
        )

    output_parser = PydanticOutputParser(pydantic_object=SearchWord)

    # プロンプト
    MAX_SEARCH_WORDS_NUM = 3
    format_reflection = ""

    prompt_template = PromptTemplate(
        template="あなたは以下議題に対して、{role_name},{role_description} の立場で情報を集めるエージェントです。\
        ##　議題\n\
        {agenda}\n\
        google検索を行い、検索のための単語を入力してください。\
        google_search_wordsに文字列リストを入力してください。\
        例えば、日本の首都はどこになりますか？という質問に対して、[[日本,首都],[日本,首都,どこ]]などのように、\
        google検索で有用な結果が返ってきそうな検索単語を出力します。\
        リストは最大{max_search_words_num}個までです。\
        以下の過去の振り返りを考慮すること\n{reflections}\n\
        \n{format_instructions}\n",
        input_variables=[],
        partial_variables={
            "role_name": state.prepare_state.reporter_role.name,
            "role_description": state.prepare_state.reporter_role.description,
            "agenda": state.prepare_state.agenda,
            "max_search_words_num": MAX_SEARCH_WORDS_NUM,
            "format_instructions": output_parser.get_format_instructions(),
            "reflections": format_reflection,
        },
    )

    prompt = prompt_template.format_prompt()

    # モデルの出力
    model_output = model.invoke(prompt)
    output = output_parser.parse(model_output)
    state.search_state.search_words = output.google_search_words

    print("make_search_words finish")
    pprint(output.google_search_words)
    # reflection用の記録も追加
    return {
        "search_state": state.search_state,
        "current_node": "make_search_words",
    }


def get_search_urls(state: OverAllState):
    MAX_SEARCH_NUM = 2
    repository = GoogleSearchRepository()
    queries = state.search_state.search_words

    search_urls = []
    for query in queries:
        str_query = " ".join(query)
        res = repository.search(query=str_query, num=MAX_SEARCH_NUM)
        temp_urls = [r["link"] for r in res]
        search_urls.extend(temp_urls)

    search_urls = list(set(search_urls))
    state.search_state.search_urls = search_urls

    # 既にあるURLはalready_crawled_urlsに追加
    # json形式でdata_baseを読み込む
    article_repository = FireStoreArticleRepository()
    already_crawled_urls = [
        url for url in search_urls if article_repository.check_url_exists(url)
    ]
    search_urls = [url for url in search_urls if url not in already_crawled_urls]

    state.search_state.already_crawled_urls = already_crawled_urls
    state.search_state.search_urls = search_urls

    print("get_search_urls finish")
    print(search_urls)

    return {"search_state": state.search_state, "current_node": "get_search_urls"}


def routing_parallel_crawl(state: OverAllState):
    return [
        Send(
            "crawl_and_save",
            {
                "url": f"{url}",
                "user_input": state.user_input,
                "agenda": state.prepare_state.agenda,
            },
        )
        for url in state.search_state.search_urls
    ]


def crawl_and_save(raw_state: dict):
    state = CrawlParallelState(**raw_state)
    app = FirecrawlApp()
    try:
        print(f"Start crawling {state.url}")
        result = app.crawl_url(
            state.url,
            params={"limit": 5, "scrapeOptions": {"formats": ["markdown"]}},
            poll_interval=5,
        )

        full_text = result["data"][0]["markdown"]
        extract_information = _extract_article_body(
            full_text=full_text, user_question=state.user_input, agenda=state.agenda
        )

        article_raw_data_repository = CloudStorageArticleRawRepository()
        save_file_path = f"{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
        article_raw_data_repository.save_dict_to_json(
            dict_data=result, file_name=save_file_path
        )

        article = Article(
            url=state.url,
            user_question=state.user_input,
            raw_data_path=save_file_path,
            extract_information=extract_information,
        )

        article_repository = FireStoreArticleRepository()
        article_repository.save(url=state.url, article=article)

        print(f"Finish crawling {state.url}")

    except Exception as e:
        if "429" in str(e):
            print(f"429エラーが発生しました。飛ばします。 {raw_state["url"]}")
            # TODO: retry処理の実装
            return None
        print(f"Error crawling {state.url}: {e}")
        return None

    else:
        return {"crawled_url": [state.url]}


@retry(tries=3, exceptions=(Exception,))  # リトライ対象を明確化
def _extract_article_body(full_text: str, user_question: str, agenda: str):
    # プロンプト
    prompt_template = PromptTemplate(
        template="あなたはスクレイピングした情報から、関連する本文だけを抽出するエージェントです。\
        {scrapying_result}に対して、広告などを削除し、記事の本文だけを抽出して下さい。 \
        この記事は、以下質問に対し、以下議題で議論するために集めたものです。\
        ## 質問\n\
        {user_question}\n\
        ## 議題\n\
        {agenda}\n\
        新しい情報などを加えてはいけませんし、要約してもいけません。\
        出力は余計なものをつけず、本文の抽出だけを返して下さい。挨拶や補足も要りません。",
        input_variables=[],
        partial_variables={
            "scrapying_result": full_text,
            "user_question": user_question,
            "agenda": agenda,
        },
    )

    prompt = prompt_template.format_prompt()

    try:
        # モデルの出力
        model_output = model.invoke(prompt)

    except Exception as e:
        print(f"Error extracting article body: {e}")
        raise e

    return model_output


# def reflection_create_search_words(state: CrawlerState):
#     # google_search_technique.txtから文字列を取得
#     with open("google_search_technique.txt") as f:
#         google_search_technique = f.read()
#     reflection_instructions = google_search_technique
#     latest_reflection = state.reflections[-1]

#     reflection_result = reflection(
#         latest_reflection.task, latest_reflection.result, reflection_instructions
#     )
#     state.reflections[-1] = reflection_result
#     if len(state.reflections) > state.max_reflection_num:
#         needs_retry = False
#     else:
#         needs_retry = reflection_result.needs_retry

#     print("reflection_create_search_words finish")
#     print("needs_retry", needs_retry)

#     return {"reflections": state.reflections, "needs_retry": needs_retry}
