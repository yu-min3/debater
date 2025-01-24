# ライブラリのインポート
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import PromptTemplate
from retry import retry

from model.state_t import SelfReflection, State
from src.llm.gemini import gemini_model as model


@retry(tries=3, exceptions=(Exception,))  # リトライ対象を明確化
def reflection(state: State) -> SelfReflection:
    if (
        state.self_reflection_state.current_task_id
        not in state.self_reflection_state.reflections
    ):
        state.self_reflection_state.reflections[
            state.self_reflection_state.current_task_id
        ] = []
    output_parser = PydanticOutputParser(pydantic_object=SelfReflection)

    prompt_template = PromptTemplate(
        template="与えられたタスクの内容:\n{task}\n\n\
            タスクを実行した結果:\n{result}\n\n\
            あなたは高度な推論能力を持つAIエージェントです。上記のタスクを実行した結果を分析し、このタスクに対するあなたの取り組みが適切だったかどうかを内省してください。\n\
            以下の項目に沿って、リフレクションの内容を出力してください。\n\n\
            リフレクション:\n\
            このタスクに取り組んだ際のあなたの思考プロセスや方法を振り返ってください。何か改善できる点はありましたか?\n\
            次に同様のタスクに取り組む際に、より良い結果を出すための教訓を2〜3文程度で簡潔に述べてください。\n\n\
            振り返りにあたり、以下指示を参考にしてください。\n{reflection_instructions}\n\n\
            判定:\n\
            - 結果の適切性: タスクの実行結果は適切だったと思いますか?あなたの判断を真偽値で示してください。\n\
            - 判定の自信度: 上記の判断に対するあなたの自信の度合いを0から1までの小数で示してください。\n\
            - 判定の理由: タスクの実行結果の適切性とそれに対する自信度について、判断に至った理由を簡潔に列挙してください。\n\n\
            出力は必ず日本語で行ってください。\n\n\
            Tips: Make sure to answer in the correct format.\
            \n{format_instructions}\n",
        input_variables=[],
        partial_variables={
            "task": state.self_reflection_state.current_task_id,
            "result": state.self_reflection_state.current_result,
            "reflection_instructions": state.self_reflection_state.reflection_instruction,
            "format_instructions": output_parser.get_format_instructions(),
        },
    )

    prompt = prompt_template.format_prompt()

    try:
        # モデルの出力
        model_output = model.invoke(prompt)
        # 念の為taskとresultを入れ直す
        output = output_parser.parse(model_output)
        state.self_reflection_state.reflections[
            state.self_reflection_state.current_task_id
        ].append(output)

        return {"self_reflection_state": state.self_reflection_state}
    except Exception as e:
        print(f"Error: {e}")
        raise e


def format_reflections(
    task: str, result: str, reflections: list[SelfReflection] | None
) -> str:
    return (
        "\n\n".join(
            f"<ref_{i}><task>{task}</task><reflection>{r.reflection}</reflection></ref_{i}>"
            for i, r in enumerate(reflections)
        )
        if reflections
        else "No relevant past reflections."
    )
