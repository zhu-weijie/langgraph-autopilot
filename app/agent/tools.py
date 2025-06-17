import os
import subprocess
from github import Github, GithubException
from urllib.parse import urlparse
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

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


def identify_file_to_change(state: dict) -> dict:
    print("---IDENTIFYING FILE TO CHANGE---")
    llm = ChatOpenAI(model="gpt-4o", temperature=0, api_key=os.getenv("OPENAI_API_KEY"))

    prompt_template = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are an expert software engineer. Your task is to analyze a GitHub issue and a list of repository files to determine which single file is the most likely candidate to be modified to resolve the issue. "
                "Respond with only the file path and nothing else. Do not add any explanation, commentary, or markdown formatting.",
            ),
            (
                "user",
                "Here is the GitHub issue:\n"
                "**Title:** {issue_title}\n"
                "**Body:** {issue_body}\n\n"
                "Here is the list of all files in the repository:\n"
                "{file_list}\n\n"
                "Based on the issue and the file list, which single file should be modified? Return only the path to that file.",
            ),
        ]
    )

    chain = prompt_template | llm

    print("Invoking LLM to identify file...")
    response = chain.invoke(
        {
            "issue_title": state["issue_title"],
            "issue_body": state["issue_body"],
            "file_list": state["repo_file_list"],
        }
    )

    file_path = response.content.strip()
    print(f"LLM identified file: {file_path}")

    return {"file_to_change": file_path}


def read_file_content(state: dict) -> dict:
    print("---READING FILE CONTENT---")
    repo_path = state["repo_local_path"]
    file_path = state["file_to_change"]

    if not file_path or not isinstance(file_path, str):
        return {"error": f"Invalid file path provided: {file_path}"}

    full_path = os.path.join(repo_path, file_path)

    try:
        with open(full_path, "r") as f:
            content = f.read()
        print(f"Successfully read file: {file_path}")
        return {"original_file_content": content}
    except FileNotFoundError:
        error_message = f"File not found at path: {full_path}"
        print(error_message)
        return {"error": error_message}
    except Exception as e:
        error_message = f"An error occurred while reading the file: {e}"
        print(error_message)
        return {"error": error_message}


def generate_code(state: dict) -> dict:
    print("---GENERATING NEW FILE CONTENT---")
    llm = ChatOpenAI(model="gpt-4o", temperature=0, api_key=os.getenv("OPENAI_API_KEY"))

    prompt_template = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are an expert software engineer. Your task is to rewrite the provided file to resolve the given GitHub issue.\n"
                "You MUST return the ENTIRE, complete, new version of the file. Do NOT just provide a diff, a patch, or a code snippet.\n"
                "Do NOT include any explanations, commentary, or markdown code fences like ```python ... ```. Your output should be ready to be written directly to a file.",
            ),
            (
                "user",
                "Please rewrite the file '{file_to_change}' to address the following issue.\n\n"
                "**Issue Title:** {issue_title}\n"
                "**Issue Body:**\n{issue_body}\n\n"
                "**Original File Content:**\n"
                "```\n"
                "{original_file_content}\n"
                "```\n\n"
                "Now, provide the complete and updated content for the file '{file_to_change}':",
            ),
        ]
    )

    chain = prompt_template | llm

    print("Invoking LLM to generate new code...")
    response = chain.invoke(
        {
            "issue_title": state["issue_title"],
            "issue_body": state["issue_body"],
            "file_to_change": state["file_to_change"],
            "original_file_content": state["original_file_content"],
        }
    )

    new_content = response.content.strip()
    print("LLM generated new content successfully.")

    return {"new_file_content": new_content}
