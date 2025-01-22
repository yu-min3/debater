# ライブラリのインポート
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import PromptTemplate
from retry import retry

from src.llm.gemini import gemini_model as model
from src.model.state.debater import (
    OPPONENT_CONCULSION_CANDIDATES,
    REPORTER_CONCLUSION_CANDIDATES,
    DebateHistory,
    DebaterResponse,
    JudgeResponse,
    OpponentResponse,
)
from src.model.state.over_all import OverAllState
from src.repository.article import FireStoreArticleRepository


def make_reference_articles(state: OverAllState):
    reference_urls = state.search_state.already_crawled_urls + state.crawled_url
    reference_articles = []
    article_repository = FireStoreArticleRepository()
    for url in reference_urls:
        article = article_repository.load(url)
        reference_articles.append(
            (
                url,
                article.extract_information,
            )
        )

    state.debater_state.reference_articles = reference_articles
    print("make_reference_articles finish")
    print("reference_urls", reference_urls)
    return {
        "debater_state": state.debater_state,
        "current_node": "make_reference_articles",
    }


@retry(tries=3)
def answer(state: OverAllState):
    output_parser = PydanticOutputParser(pydantic_object=DebaterResponse)
    # プロンプト
    prompt_template = PromptTemplate(
        template="あなたは以下議題に対して、{role_name},{role_description} の立場で議論するエージェントです。\
            ##　議題\n{agenda}\n\\\
            以下は参考情報です。URL,記事本文のペアで与えられます。URLから推察される発行元の信頼度も考慮して下さい。\n\
            ## 情報\n{articles}\n\
            あなたの意見をまとめてレポートして下さい。\
            conclusionに関しては、必ず以下の中から選択してください。選択肢を[]内,区切りで用意しました。\n \
            \n{conclusion_options}\n\
            evidenceに関しては、summaryを作るにあたり参考にした記事のみを記載してください。\n\
            \\##反対意見がある場合\n\
            あなたは過去に反対意見を持つ人にreportを提出しました。反対者の立場は{opponent_role_name},{opponent_description}です。\
            反論は以下の通り返ってきています。reportがあなたの意見, opponentがそれに対する反対意見, judgeがその議論を客観的に評価した結果です。\
            複数回議論を繰り返している可能性があり、2つ以上存在する場合は、連続してそれを考慮して議論が繰り返されています。/\
            \n##過去の議論履歴\n{report_history}\n\
            反対意見に対する反証も次のレポートには含んでください。\
            \n{format_instructions}\n",
        input_variables=[],
        partial_variables={
            "agenda": state.prepare_state.agenda,
            "articles": state.debater_state.reference_articles,
            "role_name": state.prepare_state.reporter_role.name,
            "role_description": state.prepare_state.reporter_role.description,
            "opponent_role_name": state.prepare_state.opponent_role.name,
            "opponent_description": state.prepare_state.opponent_role.description,
            "conclusion_options": ", ".join(REPORTER_CONCLUSION_CANDIDATES),
            "report_history": state.debater_state.report_history,
            "format_instructions": output_parser.get_format_instructions(),
        },
    )

    prompt = prompt_template.format_prompt(
        agenda=state.prepare_state.agenda,
        articles=state.debater_state.reference_articles,
    )
    model_output = model.invoke(prompt)
    output = output_parser.parse(model_output)

    state.debater_state.report_history.append(DebateHistory(report=output))

    print("sucessfully answered")

    return {
        "debater_state": state.debater_state,
        "current_node": "answer",
    }


@retry(tries=3)
def opponent(state: OverAllState):
    output_parser = PydanticOutputParser(pydantic_object=OpponentResponse)

    # プロンプト
    prompt_template = PromptTemplate(
        template="あなたは以下議題に対して、{opponent_role_name},{opponent_role_description} の立場で議論を行うエージェントです。\
            議論相手の立場は{role_name},{role_description}です。\
            ## 議題\n{agenda}\n\\\
            ## 議論相手のレポート:\n{report}\n\
            以下は参考情報です。\n\
            ## 情報:\n{articles}\n\
            conclusionに関しては、必ず以下の中から選択してください。選択肢を[]内,区切りで用意しました。\n \
            \n{conclusion_options}\n\
            あなたは過去に議論をいくつか行なっている場合があります。\
            以下がその履歴です。[議論相手のreport, それに対するあなたの反論]の順で履歴が並んでいます。\
            履歴の中に議論相手のreportしかない場合、それに対する反論のターンです。\
            \n##過去の議論履歴\n{report_history}\n\
            \n{format_instructions}\n",
        input_variables=[],
        partial_variables={
            "articles": state.debater_state.reference_articles,
            "agenda": state.prepare_state.agenda,
            "role_name": state.prepare_state.reporter_role.name,
            "role_description": state.prepare_state.reporter_role.description,
            "opponent_role_name": state.prepare_state.opponent_role.name,
            "opponent_role_description": state.prepare_state.opponent_role.description,
            "conclusion_options": ", ".join(OPPONENT_CONCULSION_CANDIDATES),
            "report": state.debater_state.report_history[-1].report,
            "report_history": state.debater_state.report_history,
            "format_instructions": output_parser.get_format_instructions(),
        },
    )

    prompt = prompt_template.format_prompt()
    model_output = model.invoke(prompt)
    output = output_parser.parse(model_output)

    debate_history = DebateHistory(
        report=state.debater_state.report_history[-1].report, opponent=output
    )
    state.debater_state.report_history[-1] = debate_history
    print("sucessfully opponent")

    return {
        "debater_state": state.debater_state,
        "current_node": "opponent",
    }


@retry(tries=3)
def judge(state: OverAllState):
    output_parser = PydanticOutputParser(pydantic_object=JudgeResponse)
    prompt_template = PromptTemplate(
        template="あなたは以下議題に対して、十分な議論がなされたか判断するエージェントです。\
            ##　議題\n{agenda}\n\\\
            議論の経緯は以下の通りです。\
            \n##過去の議論履歴\n{report_history}\n\
            {role_name}の人が十分説得力があるレポートを提出できたか判断し、議論を終えても良いかどうかを判断してください。\
            以下点に留意して判断してください。\
            1. のっぺりした情報だけでなく、しっかりとした主張や反証を通じて自分の考えが表現できていること。\
            \n{format_instructions}\n",
        input_variables=[],
        partial_variables={
            "agenda": state.prepare_state.agenda,
            "role_name": state.prepare_state.reporter_role.name,
            "report_history": state.debater_state.report_history,
            "format_instructions": output_parser.get_format_instructions(),
        },
    )

    prompt = prompt_template.format_prompt()
    model_output = model.invoke(prompt)
    output = output_parser.parse(model_output)

    state.debater_state.report_history[-1].judge = output

    if len(state.debater_state.report_history) > state.debater_state.max_debate_num:
        state.debater_state.end_judge = True
    else:
        state.debater_state.end_judge = output.end_judge
    print("sucessfully judged")
    print("end_judge", state.debater_state.end_judge)

    return {"debater_state": state.debater_state, "current_node": "judge"}
