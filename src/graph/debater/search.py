from datetime import datetime
from pprint import pprint

# ライブラリのインポート
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import PromptTemplate
from pydantic import BaseModel, Field
from retry import retry

from src.llm.gemini import gemini_model as model
from src.model.article import Article
from src.model.state.over_all import OverAllState
from src.repository.article import FireStoreArticleRepository
from src.repository.article_raw_data import CloudStorageArticleRawRepository
from src.repository.crawl import TavilyCrawlRepository
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


def crawl_and_save(state: OverAllState):
    repository = TavilyCrawlRepository()
    results = repository.extract(state.search_state.search_urls)

    for result in results:
        url = result[0]
        raw_text = result[1]
        full_data = result[2]

        article_raw_data_repository = CloudStorageArticleRawRepository()
        save_file_path = f"{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
        article_raw_data_repository.save_dict_to_json(
            dict_data=full_data, file_name=save_file_path
        )

        article = Article(
            url=url,
            user_question=state.user_input,
            raw_data_path=save_file_path,
            raw_text=raw_text,
            extract_information=None,
        )

        article_repository = FireStoreArticleRepository()
        article_repository.save(url=url, article=article)

        state.search_state.crawled_urls.append(url)

        print(f"Finish crawl and raw-data save {url}")

    return {"search_state": state.search_state, "current_node": "crawl_and_save"}
