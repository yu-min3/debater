from langgraph.graph import StateGraph

from src.graph.topic_provider.choose_topic import State, choose_topic, crawl_and_save

workflow = StateGraph(State)

workflow.add_node("choose_topic", choose_topic)
workflow.add_node("crawl_and_save", crawl_and_save)

workflow.set_entry_point("choose_topic")
workflow.add_edge("choose_topic", "crawl_and_save")

compiled = workflow.compile()

state = State()
compiled.invoke(state)
