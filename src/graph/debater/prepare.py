# ライブラリのインポート
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import PromptTemplate

from src.llm.gemini import vertex_gemini_model as model
from src.model.state.over_all import OverAllState
from src.model.state.prepare import PrepareState


def prepare(state: OverAllState):
    output_parser = PydanticOutputParser(pydantic_object=PrepareState)

    prompt_template = PromptTemplate(
        template="""
        これから質問者が広く、深い洞察を得るために、議論を始めます。
        2人で議論を行い、それぞれ違う立場に立ち、交互に検証、反証を行い、最終的に第三者がまとめます。
        深い洞察が得られるような、agendaと2人の立場を設定して下さい。
        agendaは抽象的や俯瞰的なものにせず、質問そのものに対し満足の得られる答えが得られることが重要です。
        立場の名前は端的に分かりやすいようつけて下さい。
        質問は以下の通りです。

        ## 質問
        # {user_input}

        \n{format_instructions}""",
        input_variables=["question"],
        partial_variables={
            "user_input": state.user_input,
            "format_instructions": output_parser.get_format_instructions(),
        },
    )

    user_input = state.user_input
    prompt = prompt_template.format_prompt(user_input=user_input)

    # モデルの出力
    model_output = model.invoke(prompt)
    output = output_parser.parse(model_output)

    return {"prepare_state": output, "current_node": "prepare"}
