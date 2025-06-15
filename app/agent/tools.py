import os
import subprocess
import tempfile
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
        repo_full_name = f"{owner}/{repo_name}"
        repo = g.get_repo(repo_full_name)
        issue = repo.get_issue(number=int(issue_number))
        return {
            "issue_title": issue.title,
            "issue_body": issue.body,
            "repo_full_name": repo_full_name,
        }
    except (GithubException, ValueError, IndexError) as e:
        return {"error": f"Failed to read issue: {e}"}


def clone_repo(state: dict) -> dict:
    print("---CLONING REPOSITORY---")
    repo_full_name = state.get("repo_full_name")
    if not repo_full_name:
        return {"error": "Repository name not found in state."}

    job_id_for_path = repo_full_name.replace("/", "-")
    temp_dir = tempfile.mkdtemp(prefix=f"job-{job_id_for_path}-")

    repo_url = f"https://github.com/{repo_full_name}.git"
    print(f"Cloning {repo_url} into {temp_dir}")

    try:
        subprocess.run(
            ["git", "clone", repo_url, temp_dir],
            check=True,
            capture_output=True,
            text=True,
        )
        return {"repo_local_path": temp_dir}
    except subprocess.CalledProcessError as e:
        print(f"Git clone failed with error: {e.stderr}")
        return {"error": f"Git clone failed: {e.stderr}"}


def list_repository_files(state: dict) -> dict:
    print("---LISTING REPOSITORY FILES---")
    repo_path = state.get("repo_local_path")
    if not repo_path:
        return {"error": "Repository path not found in state."}

    ignore_dirs = {
        ".git",
        "__pycache__",
        ".idea",
        "node_modules",
        "venv",
        ".venv",
        ".ruff_cache",
    }
    ignore_files = {".DS_Store"}

    file_list = []
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]

        for file in files:
            if file not in ignore_files:
                full_path = os.path.join(root, file)
                relative_path = os.path.relpath(full_path, repo_path)
                file_list.append(relative_path)

    return {"repo_file_list": "\n".join(file_list)}
