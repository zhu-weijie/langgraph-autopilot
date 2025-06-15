from langgraph.graph import StateGraph, END
from .state import AppState
from .tools import read_github_issue


def create_agent_graph():
    workflow = StateGraph(AppState)
    workflow.add_node("read_issue", read_github_issue)
    workflow.set_entry_point("read_issue")
    workflow.add_edge("read_issue", END)
    return workflow.compile()
