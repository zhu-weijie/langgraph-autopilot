from langgraph.graph import StateGraph, END
from .state import AppState
from .tools import (
    read_github_issue,
    prepare_repo,
    list_repository_files,
    identify_file_to_change,
    read_file_content,
    generate_code,
)


def create_agent_graph():
    workflow = StateGraph(AppState)

    workflow.add_node("read_issue", read_github_issue)
    workflow.add_node("prepare_repo", prepare_repo)
    workflow.add_node("list_files", list_repository_files)
    workflow.add_node("identify_file", identify_file_to_change)
    workflow.add_node("read_file", read_file_content)
    workflow.add_node("generate_code", generate_code)

    workflow.set_entry_point("read_issue")
    workflow.add_edge("read_issue", "prepare_repo")
    workflow.add_edge("prepare_repo", "list_files")
    workflow.add_edge("list_files", "identify_file")
    workflow.add_edge("identify_file", "read_file")
    workflow.add_edge("read_file", "generate_code")
    workflow.add_edge("generate_code", END)

    return workflow.compile()
