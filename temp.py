import asyncio
import logging
import os

import chainlit as cl
from langchain_core.messages import HumanMessage
from langgraph.graph.state import CompiledStateGraph

from src.graph.compiled_graph import get_debater_graph
from src.model.state.over_all import (
    DebaterState,
    OverAllState,
    PrepareState,
    SearchState,
)


@cl.on_chat_start
async def on_chat_start():
    # セッションが開始したら、エージェントを作成してセッションに保存
    app = get_debater_graph()
    cl.user_session.set("app", app)

    # メッセージの履歴を保存するためのリストをセッションに保存
    cl.user_session.set("inputs", {"messages": []})

    init_message = "ようこそ！\n\
        これはあなたが持つ疑問に対し、複数人で議論を行うチャットボットシステムです！\n\
        気になる議題を入力してみて下さい！"
    await cl.Message(content=init_message).send()

    await cl.Message(content="これは1行目です。  \n\nこれは2行目です。").send()
    await cl.Message(content="\
        # 大見出し\
        ## 小見出し\
        ").send()



@cl.on_message
async def on_message(msg: cl.Message):
    # メッセージを受け取ったら、セッションからエージェントとメッセージの履歴を取得
    app: CompiledStateGraph = cl.user_session.get("app")

    init_state = OverAllState(
        user_input=msg.content,
        current_node="",
        prepare_state=PrepareState(),
        search_state=SearchState(),
        debater_state=DebaterState(),
    )

    for state in app.stream(input=init_state, stream_mode="values"):
        state = OverAllState(**state)

        match state.current_node:
            case "prepare":

                await cl.Message(
                    content=_make_prepare_message(state.prepare_state),
                ).send()

            case "make_search_words":
                await cl.Message(content=_make_search_words_message(state.search_state), author="make_search_words").send()

            case "get_search_urls":
                message = "参考記事を調査します。。。少々お待ちくださいm(_ _)m"
                await cl.Message(content=message).send()

            case "make_reference_articles":
                urls = "\n".join([url for url, _ in state.debater_state.reference_articles])
                message = f"記事を調査しました！参考記事は以下の通りです\n{urls}]"
                await cl.Message(content=message).send()

            case "report":
                await cl.Message(content=_make_report_message(state)).send()

            case "opponent":
                await cl.Message(content=_make_opponent_message(state)).send()

            case "judge":
                await cl.Message(content=_make_judge_message(state)).send()


def _make_prepare_message(prepare_state: PrepareState):
    agenda_title = _make_title("議題")
    reporeter_title = _make_title(f"主張者：{prepare_state.reporter_role.name}")
    opponent_title = _make_title(f"反論者：{prepare_state.opponent_role.name}")

    message = f"\
        ## 議題{agenda_title}\n\
        {prepare_state.agenda}]\n \n\
        {reporeter_title}\n\
        {prepare_state.reporter_role.description}\n \n\
        {opponent_title}\n\
        {prepare_state.opponent_role.description}\n \n\
        "
    return message

def _make_search_words_message(search_state: SearchState):
    search_word_title = _make_title("検索ワード")
    search_words = "\n".join(
        [
            f"{num+1}: {", ".join(word)}"
            for num, word in enumerate(search_state.search_words)
        ]
    )
    message = f"{search_word_title}\n{search_words}]"
    return message

def _make_report_message(state: OverAllState):
    report_title = _make_title(f"{state.prepare_state.reporter_role.name}のレポート")
    conclusion_title = _make_title("結論")
    summary_title = _make_title("概要")
    evidence_title = _make_title("参考記事")

    report = state.debater_state.report_history[-1].report
    format_evidence = "\n".join(
        [f"{num+1}: {url}" for num, (url, _) in enumerate(report.evidence)]
    )

    message = f"\
        {report_title}\n\
        {conclusion_title}\n{report.conclusion}\n\
        {summary_title}\n{report.summary}\n\
        {evidence_title}\n{format_evidence}"
    return message

def _make_opponent_message(state:OverAllState):
    opponent_title = _make_title(f"{state.prepare_state.opponent_role.name}の反対意見")
    conclusion_title = _make_title("結論")
    reason_title = _make_title("理由")
    summary_title = _make_title("概要")

    opponent = state.debater_state.report_history[-1].opponent

    message = f"\
        {opponent_title} \n\
        {conclusion_title} \n{opponent.conclusion}\n\
        {reason_title}\n{opponent.opposite_reasons}\n\
        {summary_title}\n{opponent.summary}"
    return message

def _make_judge_message(state:OverAllState):
    judge_title = _make_title("ジャッジ")
    conclusion_title = _make_title("結論")
    summary_title = _make_title("概要")

    judge_report = state.debater_state.report_history[-1].judge

    if judge_report.end_judge:
        conclusion = "議論を終了します"
    elif state.debater_state.end_judge:
        conclusion = "まだ検証し足りないことがありますが、これ以上議論を深めることは難しいと判断し、議論を終了します"
    else:
        conclusion = "もう少し議論が必要です。続けます"

    message = f"\
        {judge_title}\n\
        {conclusion_title}\n{conclusion}\n\
        {summary_title}\n{judge_report.summary}"

    return message

@cl.password_auth_callback
def auth_callback(username: str, password: str):
    # Fetch the user matching username from your database
    # and compare the hashed password with the value stored in the database
    user_name = os.environ.get("CHAINLIT_USER_NAME", "")
    user_password = os.environ.get("CHAINLIT_USER_PASSWORD", "")
    if (username, password) == (user_name, user_password):
        return cl.User(identifier=user_name, metadata={"role": "admin"})
    return None
