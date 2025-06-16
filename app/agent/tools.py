import os
import subprocess
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


def prepare_repo(state: dict) -> dict:
    print("---PREPARING REPOSITORY---")
    repo_full_name = state.get("repo_full_name")
    if not repo_full_name:
        return {"error": "Repository name not found in state."}

    repos_dir = "/code/repos"
    repo_dir_name = repo_full_name.replace("/", "__")
    repo_path = os.path.join(repos_dir, repo_dir_name)

    if os.path.exists(repo_path):
        print(f"Repository already exists at {repo_path}. Pulling latest changes.")
        try:
            subprocess.run(
                ["git", "pull"],
                cwd=repo_path,
                check=True,
                capture_output=True,
                text=True,
            )
            print("Successfully pulled latest changes.")
        except subprocess.CalledProcessError as e:
            error_message = f"Git pull failed: {e.stderr}"
            print(error_message)
            return {"error": error_message}
    else:
        print(f"Repository not found. Cloning into {repo_path}.")
        repo_url = f"https://github.com/{repo_full_name}.git"
        try:
            os.makedirs(repos_dir, exist_ok=True)
            subprocess.run(
                ["git", "clone", repo_url, repo_path],
                check=True,
                capture_output=True,
                text=True,
            )
            print("Successfully cloned repository.")
        except subprocess.CalledProcessError as e:
            error_message = f"Git clone failed: {e.stderr}"
            print(error_message)
            return {"error": error_message}

    return {"repo_local_path": repo_path}


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
    file_list_str = "\n".join(file_list)
    print(f"Found {len(file_list)} files.")
    return {"repo_file_list": file_list_str}
