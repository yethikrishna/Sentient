from github.Repository import Repository
from github.Issue import Issue
from github.PullRequest import PullRequest
from github.NamedUser import NamedUser

def _simplify(obj):
    """Generic simplifier for PyGithub objects."""
    if isinstance(obj, list):
        return [_simplify(item) for item in obj]
    if isinstance(obj, Repository):
        return _simplify_repo(obj)
    if isinstance(obj, Issue):
        return _simplify_issue(obj)
    if isinstance(obj, PullRequest):
        return _simplify_pr(obj)
    if isinstance(obj, NamedUser):
        return {"login": obj.login, "name": obj.name, "url": obj.html_url}
    # Add other types as needed
    return str(obj)

def _simplify_repo(repo: Repository) -> dict:
    """Converts a PyGithub Repository object to a simpler dictionary."""
    return {
        "id": repo.id,
        "name": repo.name,
        "full_name": repo.full_name,
        "description": repo.description,
        "url": repo.html_url,
        "stars": repo.stargazers_count,
        "forks": repo.forks_count,
        "language": repo.language,
        "private": repo.private,
    }

def _simplify_issue(issue: Issue) -> dict:
    """Converts a PyGithub Issue object to a simpler dictionary."""
    return {
        "number": issue.number,
        "title": issue.title,
        "state": issue.state,
        "url": issue.html_url,
        "user": issue.user.login,
        "assignee": issue.assignee.login if issue.assignee else None,
        "labels": [label.name for label in issue.labels],
        "created_at": issue.created_at.isoformat(),
        "body": issue.body,
    }

def _simplify_pr(pr: PullRequest) -> dict:
    """Converts a PyGithub PullRequest object to a simpler dictionary."""
    return {
        "number": pr.number,
        "title": pr.title,
        "state": pr.state,
        "url": pr.html_url,
        "user": pr.user.login,
        "mergable": pr.mergeable,
        "created_at": pr.created_at.isoformat(),
        "body": pr.body,
    }

def _simplify_content_file(content) -> dict:
    """Converts a PyGithub ContentFile object to a simpler dictionary."""
    return {
        "type": content.type,
        "name": content.name,
        "path": content.path,
        "size": content.size,
        "url": content.html_url,
        "sha": content.sha,
    }