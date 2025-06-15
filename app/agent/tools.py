import os
from github import Github, GithubException
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()


def read_github_issue(state: dict) -> dict:
    print("---READING GITHUB ISSUE---")
    try:
        g = Github(os.getenv("GITHUB_TOKEN"))
        parsed_url = urlparse(state["issue_url"])
        path_parts = parsed_url.path.strip("/").split("/")
        owner, repo_name, _, issue_number = path_parts[:4]
        repo = g.get_repo(f"{owner}/{repo_name}")
        issue = repo.get_issue(number=int(issue_number))
        return {"issue_title": issue.title, "issue_body": issue.body}
    except (GithubException, ValueError, IndexError) as e:
        return {"error": f"Failed to read issue: {e}"}
