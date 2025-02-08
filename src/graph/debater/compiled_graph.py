from langgraph.graph import END, StateGraph

from src.graph.debater.debater import judge, make_reference_articles, opponent, report
from src.graph.debater.prepare import prepare
from src.graph.debater.search import (
    crawl_and_save,
    get_search_urls,
    make_search_words,
)
from src.model.state.over_all import (
    OverAllState,
)


def get_debater_graph():
    workflow = StateGraph(OverAllState)

    workflow.add_node("prepare", prepare)
    workflow.add_node("make_search_words", make_search_words)
    workflow.add_node("get_search_urls", get_search_urls)
    workflow.add_node("crawl_and_save", crawl_and_save)
    workflow.add_node("make_reference_articles", make_reference_articles)
    workflow.add_node("report", report)
    workflow.add_node("opponent", opponent)
    workflow.add_node("judge", judge)

    workflow.set_entry_point("prepare")
    workflow.add_edge("prepare", "make_search_words")
    workflow.add_edge("make_search_words", "get_search_urls")
    workflow.add_edge("get_search_urls", "crawl_and_save")
    workflow.add_edge("crawl_and_save", "make_reference_articles")
    workflow.add_edge("make_reference_articles", "report")
    workflow.add_edge("report", "opponent")
    workflow.add_edge("opponent", "judge")
    workflow.add_conditional_edges(
        "judge",
        lambda state: state.debater_state.end_judge,
        {True: END, False: "report"},
    )

    compiled = workflow.compile()

    return compiled
