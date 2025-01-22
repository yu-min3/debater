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

# 定期的にPingを送信するための間隔（秒）
PING_INTERVAL = 25  # 30秒

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


# websocket接続を維持するためのPingを送信するタスク
async def ping_pong_task():
    """WebSocket接続を維持するためにPingを定期的に送信"""
    while True:
        await asyncio.sleep(PING_INTERVAL)
        try:
            # ChainlitのWebSocket APIにPingを送信
            # await cl.ws.ping()  # ChainlitのWebSocketインターフェースを使ったPing送信
            # await time.sleep(2)
            print("ping!")
        except Exception as e:
            logger.error(f"Error while sending Ping: {e}")


@cl.on_chat_start
async def on_chat_start():
    asyncio.create_task(ping_pong_task())
    # セッションが開始したら、エージェントを作成してセッションに保存
    app = get_debater_graph()
    cl.user_session.set("app", app)

    # メッセージの履歴を保存するためのリストをセッションに保存
    cl.user_session.set("inputs", {"messages": []})

    init_message = "ようこそ！\n\
        これはあなたが持つ疑問に対し、複数人で議論を行うチャットボットシステムです！\n\
        気になる議題を入力してみて下さい！"
    await cl.Message(content=init_message).send()


@cl.on_message
async def on_message(msg: cl.Message):
    # メッセージを受け取ったら、セッションからエージェントとメッセージの履歴を取得
    app: CompiledStateGraph = cl.user_session.get("app")
    inputs = cl.user_session.get("inputs")
    # ユーザーのメッセージを履歴に追加
    inputs["messages"].append(HumanMessage(content=msg.content))

    init_state = OverAllState(
        user_input=msg.content,
        current_node="",
        prepare_state=PrepareState(),
        search_state=SearchState(),
        debater_state=DebaterState(),
        crawled_url=[],
    )
    # forループをブロッキングしないため、非同期関数を作成
    async_stream = cl.make_async(app.stream)
    # 非同期関数を呼び出し、結果をイテレーション
    stream = await async_stream(input=init_state, stream_mode="values")

    for state in stream:
        state = OverAllState(**state)
        logger.debug(f"current_node: {state.current_node}")

        match state.current_node:
            case "prepare":
                message = f"議題は以下の通りです\n\
                        {state.prepare_state.agenda}]\n\
                        以下の2人が議論を行います\n\
                        ## 主張を行う人：{state.prepare_state.reporter_role.name}\n{state.prepare_state.reporter_role.description}\n\
                        ## 反論する人{state.prepare_state.opponent_role.name}\n{state.prepare_state.opponent_role.description}\n\
                        これらの議論をもとに、第三者がまとめます"
                await cl.Message(
                    content=message,
                    author="prepare",
                ).send()
            case "make_search_words":
                format_search_words = "\n".join(
                    [
                        f"{num+1}:{word}"
                        for num, word in enumerate(state.search_state.search_words)
                    ]
                )
                message = f"検索ワードは以下の通りです\n{format_search_words}]"
                await cl.Message(content=message, author="make_search_words").send()
            case "get_search_urls":
                message = "検索を開始します。。。少々お待ちくださいm(_ _)m"
                await cl.Message(content=message).send()
            case "make_reference_articles":
                urls = [url for url, _ in state.debater_state.reference_articles]
                message = f"記事が調査できました！参考記事は以下の通りです\n{urls}]"
                await cl.Message(content=message).send()

            case "answer":
                report_role = state.prepare_state.reporter_role.name
                report_description = state.prepare_state.reporter_role.description
                conclusion = state.debater_state.report_history[-1].report.conclusion
                evidence = state.debater_state.report_history[-1].report.evidence
                summary = state.debater_state.report_history[-1].report.summary

                message = f"\
                    主張者の回答：\n\
                    私は{report_role}です。立場の説明は以下の通りです。\n{report_description}\n\
                    ####結論####\n{conclusion}です。\n\
                    ####概要####\n{summary}\n\
                    ####参考にした記事####\n{evidence}"
                await cl.Message(content=message).send()

            case "opponent":
                opponent_role = state.prepare_state.opponent_role.name
                opponent_description = state.prepare_state.opponent_role.description
                opponent_report = state.debater_state.report_history[-1].opponent

                opponent_summary = opponent_report.summary
                opponent_conclusion = opponent_report.conclusion
                opponen_reasons = opponent_report.opposite_reasons
                format_opponent_reasons = "\n".join(
                    [f"{num+1}:{reason}" for num, reason in enumerate(opponen_reasons)]
                )
                message = f"\
                    反対意見\n\
                    私は{opponent_role}として、{opponent_description}から反論します。\n\
                    ####結論####\n{opponent_conclusion}\n\
                    ####理由####\n{format_opponent_reasons}\n\
                    ####要約####\n{opponent_summary}"

                await cl.Message(content=message).send()

            case "judge":
                judge_report = state.debater_state.report_history[-1].judge
                judge_summary = judge_report.summary
                end_judge = judge_report.end_judge

                if end_judge:
                    final_message = "議論を終了します"
                elif state.debater_state.end_judge:
                    final_message = "まだ検証し足りないことがありますが、これ以上議論を深めることは難しいと判断し、議論を終了します"
                else:
                    final_message = "議論を続けます"

                message = f"私は裁判官です。\n\
                    ####結論####\n{judge_summary}\n\
                    ####続けるか####\n{final_message}"
                await cl.Message(content=message).send()


@cl.password_auth_callback
def auth_callback(username: str, password: str):
    # Fetch the user matching username from your database
    # and compare the hashed password with the value stored in the database
    user_name = os.environ.get("CHAINLIT_USER_NAME", "")
    user_password = os.environ.get("CHAINLIT_USER_PASSWORD", "")
    if (username, password) == (user_name, user_password):
        return cl.User(identifier=user_name, metadata={"role": "admin"})
    return None
