# ライブラリのインポート
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import PromptTemplate
from retry import retry

from src.llm.gemini import vertex_gemini_model as model
from src.model.state.debater import (
    DebateHistory,
    DebaterResponse,
    JudgeResponse,
    OpponentResponse,
)
from src.model.state.over_all import OverAllState
from src.repository.article import FireStoreArticleRepository


def make_reference_articles(state: OverAllState):
    reference_urls = (
        state.search_state.already_crawled_urls + state.search_state.crawled_urls
    )
    reference_articles = []
    article_repository = FireStoreArticleRepository()
    for url in reference_urls:
        article = article_repository.load(url)
        if article.extract_information is not None:
            reference_text = article.extract_information
        else:
            reference_text = article.raw_text
        reference_articles.append(
            (
                url,
                reference_text,
            )
        )

    state.debater_state.reference_articles = reference_articles
    return {
        "debater_state": state.debater_state,
        "current_node": "make_reference_articles",
    }


@retry(tries=3)
def report(state: OverAllState):
    output_parser = PydanticOutputParser(pydantic_object=DebaterResponse)
    # プロンプト
    prompt_template = PromptTemplate(
        template="""あなたは以下議題に対して、{role_name},{role_description} の立場で議論するエージェントです。
            以下は参考情報です。URL,記事本文のペアで与えられます。URLから推察される発行元の信頼度も考慮して下さい。
            あなたの意見をまとめてレポートして下さい。参考情報をもとに意見を述べる方が望ましいです。
            reasonsについて、参考にしたevidenceのURLをそれぞれの理由の最後に必ず言及して下さい.

            ## 議題
            {agenda}

            ## 参考情報
            {articles}

            ## 反対意見がある場合
            あなたは過去に反対意見を持つ人にreportを提出しました。反対者の立場は{opponent_role_name},{opponent_description}です。
            反論は以下の通り返ってきています。reportがあなたの意見, opponentがそれに対する反対意見, judgeがその議論を客観的に評価した結果です。
            複数回議論を繰り返している可能性があり、2つ以上存在する場合は、連続してそれを考慮して議論が繰り返されています。
            反対意見に対する反証も次のレポートには含んでください。

            ##過去の議論履歴
            {report_history}

            \n{format_instructions}\n""",
        input_variables=[],
        partial_variables={
            "agenda": state.prepare_state.agenda,
            "articles": state.debater_state.reference_articles,
            "role_name": state.prepare_state.reporter_role.name,
            "role_description": state.prepare_state.reporter_role.description,
            "opponent_role_name": state.prepare_state.opponent_role.name,
            "opponent_description": state.prepare_state.opponent_role.description,
            "report_history": state.debater_state.report_history,
            "format_instructions": output_parser.get_format_instructions(),
        },
    )

    prompt = prompt_template.format_prompt()
    model_output = model.invoke(prompt)
    output = output_parser.parse(model_output)

    state.debater_state.report_history.append(DebateHistory(report=output))

    return {
        "debater_state": state.debater_state,
        "current_node": "report",
    }


@retry(tries=3)
def opponent(state: OverAllState):
    output_parser = PydanticOutputParser(pydantic_object=OpponentResponse)

    # プロンプト
    prompt_template = PromptTemplate(
        template="""あなたは以下議題に対して、{opponent_role_name},{opponent_role_description} の立場で議論を行うエージェントです。
            議論相手の立場は{role_name},{role_description}です。
            議論相手のレポート内容をしっかり読み、それを参照しながら反論を行ってください。
            opponent_reasonsにおいては、議論相手の内容に言及するとより望ましいです。
            URLについて言及する場合は、必ず理由の最後に言及して下さい。途中でURLを挿入してはいけません。

            ## 議題
            {agenda}

            ## 議論相手のレポート
            {report}

            ## 参考情報
            {articles}

            ## 議論履歴がある場合
            あなたは過去に議論をいくつか行なっている場合があります。
            以下がその履歴です。[議論相手のreport, それに対するあなたの反論]の順で履歴が並んでいます。
            履歴の中に議論相手のreportしかない場合、それに対する反論のターンです。

            ##過去の議論履歴
            {report_history}

            \n{format_instructions}\n""",
        input_variables=[],
        partial_variables={
            "articles": state.debater_state.reference_articles,
            "agenda": state.prepare_state.agenda,
            "role_name": state.prepare_state.reporter_role.name,
            "role_description": state.prepare_state.reporter_role.description,
            "opponent_role_name": state.prepare_state.opponent_role.name,
            "opponent_role_description": state.prepare_state.opponent_role.description,
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

    return {"debater_state": state.debater_state, "current_node": "judge"}
