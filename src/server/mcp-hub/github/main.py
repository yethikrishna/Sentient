import os
import asyncio
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

from fastmcp import FastMCP, Context
from fastmcp.prompts.prompt import Message

from . import auth, prompts, utils

load_dotenv()

mcp = FastMCP(
    name="GitHubServer",
    instructions="This server provides tools to interact with the GitHub API.",
)

# --- Tool Helper ---
async def _execute_tool(ctx: Context, func, *args, **kwargs) -> Dict[str, Any]:
    """Helper to handle auth and execution for all tools."""
    try:
        user_id = auth.get_user_id_from_context(ctx)
        token = await auth.get_github_token(user_id)
        github = auth.authenticate_github(token)
        
        # Use asyncio.to_thread to run synchronous PyGithub calls
        result = await asyncio.to_thread(func, github, *args, **kwargs)
        
        # Simplify the complex PyGithub objects into JSON-friendly dicts
        simplified_result = utils._simplify(result)
        
        return {"status": "success", "result": simplified_result}
    except Exception as e:
        return {"status": "failure", "error": str(e)}

# --- Tool Implementations ---
def _search_repos_sync(github, query: str):
    return list(github.search_repositories(query=query)[:10])

def _get_my_repos_sync(github):
    return list(github.get_user().get_repos())

def _get_repo_details_sync(github, repo_name: str):
    return github.get_repo(repo_name)

def _get_repo_issues_sync(github, repo_name: str, state: str):
    repo = github.get_repo(repo_name)
    return list(repo.get_issues(state=state))

def _create_repo_issue_sync(github, repo_name: str, title: str, body: str):
    repo = github.get_repo(repo_name)
    return repo.create_issue(title=title, body=body)

def _get_repo_contents_sync(github, repo_name: str, path: str):
    repo = github.get_repo(repo_name)
    contents = repo.get_contents(path)
    if isinstance(contents, list): # It's a directory
        return [utils._simplify_content_file(item) for item in contents]
    else: # It's a single file
        return {"name": contents.name, "path": contents.path, "content": contents.decoded_content.decode('utf-8')}

# --- Tool Definitions ---
@mcp.tool
async def search_repositories(ctx: Context, query: str) -> Dict:
    """Searches for repositories on GitHub. Uses GitHub's search syntax."""
    return await _execute_tool(ctx, _search_repos_sync, query)

@mcp.tool
async def get_my_repositories(ctx: Context) -> Dict:
    """Lists repositories for the authenticated user."""
    return await _execute_tool(ctx, _get_my_repos_sync)

@mcp.tool
async def get_repository_details(ctx: Context, repo_name: str) -> Dict:
    """Gets detailed information for a specific repository. Use format 'owner/repo'."""
    return await _execute_tool(ctx, _get_repo_details_sync, repo_name)

@mcp.tool
async def get_repository_issues(ctx: Context, repo_name: str, state: str = 'open') -> Dict:
    """Lists issues for a repository. State can be 'open', 'closed', or 'all'."""
    return await _execute_tool(ctx, _get_repo_issues_sync, repo_name, state)

@mcp.tool
async def create_repository_issue(ctx: Context, repo_name: str, title: str, body: Optional[str] = None) -> Dict:
    """Creates a new issue in a repository."""
    return await _execute_tool(ctx, _create_repo_issue_sync, repo_name, title, body)

@mcp.tool
async def get_repository_file_content(ctx: Context, repo_name: str, path: str) -> Dict:
    """Gets the content of a file or lists the contents of a directory in a repository."""
    return await _execute_tool(ctx, _get_repo_contents_sync, repo_name, path)

# --- Server Execution ---
if __name__ == "__main__":
    host = os.getenv("MCP_SERVER_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_SERVER_PORT", 9010))
    
    print(f"Starting GitHub MCP Server on http://{host}:{port}")
    mcp.run(transport="sse", host=host, port=port)