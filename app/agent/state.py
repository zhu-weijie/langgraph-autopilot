from typing import TypedDict, Optional


class AppState(TypedDict):
    issue_url: str
    issue_title: Optional[str]
    issue_body: Optional[str]
    repo_full_name: Optional[str]
    repo_local_path: Optional[str]
    repo_file_list: Optional[str]
    error: Optional[str]
