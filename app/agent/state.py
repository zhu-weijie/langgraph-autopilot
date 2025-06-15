from typing import TypedDict, Optional


class AppState(TypedDict):
    issue_url: str
    issue_title: Optional[str]
    issue_body: Optional[str]
    error: Optional[str]
