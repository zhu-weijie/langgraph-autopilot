from langgraph.graph import StateGraph, END
from .state import AppState
from .tools import read_github_issue, clone_repo, list_repository_files


def create_agent_graph():
    workflow = StateGraph(AppState)

    workflow.add_node("read_issue", read_github_issue)
    workflow.add_node("clone_repo", clone_repo)
    workflow.add_node("list_files", list_repository_files)

    workflow.set_entry_point("read_issue")
    workflow.add_edge("read_issue", "clone_repo")
    workflow.add_edge("clone_repo", "list_files")
    workflow.add_edge("list_files", END)

    return workflow.compile()
