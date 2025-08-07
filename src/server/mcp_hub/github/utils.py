from github.Repository import Repository
from github.Issue import Issue
from github.PullRequest import PullRequest
from github.NamedUser import NamedUser
from github.ContentFile import ContentFile
from github.Commit import Commit
from github.GitRelease import GitRelease
from github.Label import Label
from github.GitRef import GitRef
from github.GitTreeElement import GitTreeElement
from github.Invitation import Invitation
from github.Project import Project
from github.ProjectColumn import ProjectColumn
from github.ProjectCard import ProjectCard
from github.Workflow import Workflow
from github.WorkflowRun import WorkflowRun
from github.StatsContributor import StatsContributor
from github.StatsCommitActivity import StatsCommitActivity

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
        return _simplify_user(obj)
    if isinstance(obj, ContentFile):
        return _simplify_content_file(obj)
    if isinstance(obj, Commit):
        return _simplify_commit(obj)
    if isinstance(obj, GitRelease):
        return _simplify_release(obj)
    if isinstance(obj, Label):
        return _simplify_label(obj)
    if isinstance(obj, Invitation):
        return _simplify_invitation(obj)
    if isinstance(obj, Project):
        return _simplify_project(obj)
    if isinstance(obj, ProjectColumn):
        return _simplify_project_column(obj)
    if isinstance(obj, ProjectCard):
        return _simplify_project_card(obj)
    if isinstance(obj, Workflow):
        return _simplify_workflow(obj)
    if isinstance(obj, WorkflowRun):
        return _simplify_workflow_run(obj)
    if isinstance(obj, StatsContributor):
        return _simplify_contributor_stats(obj)
    if isinstance(obj, StatsCommitActivity):
        return _simplify_commit_activity(obj)
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
        "private": repo.private
    }

def _simplify_pr(pr: PullRequest) -> dict:
    """Converts a PyGithub PullRequest object to a simpler dictionary."""
    return {
        "number": pr.number,
        "title": pr.title,
        "state": pr.state,
        "url": pr.html_url,
        "user": pr.user.login,
        "head": pr.head.ref,
        "base": pr.base.ref,
        "created_at": pr.created_at.isoformat() if pr.created_at else None,
        "body": pr.body,
    }

def _simplify_user(user: NamedUser) -> dict:
    return {"login": user.login, "name": user.name, "url": user.html_url}

def _simplify_content_file(content: ContentFile) -> dict:
    """Converts a PyGithub ContentFile object to a simpler dictionary."""
    return {
        "type": content.type,
        "name": content.name,
        "path": content.path,
        "size": content.size,
        "url": content.html_url,
        "sha": content.sha,
    }

def _simplify_commit(commit: Commit) -> dict:
    """Converts a PyGithub Commit object to a simpler dictionary."""
    return {
        "sha": commit.sha,
        "message": commit.commit.message,
        "author": commit.commit.author.name,
        "date": commit.commit.author.date.isoformat(),
        "url": commit.html_url
    }

def _simplify_release(release: GitRelease) -> dict:
    return {
        "tag": release.tag_name,
        "name": release.title,
        "draft": release.draft,
        "prerelease": release.prerelease,
        "url": release.html_url
    }

def _simplify_label(label: Label) -> dict:
    return {"name": label.name, "color": label.color, "description": label.description}

def _simplify_invitation(invitation: Invitation) -> dict:
    return {
        "id": invitation.id,
        "invitee": _simplify_user(invitation.invitee) if invitation.invitee else None,
        "inviter": _simplify_user(invitation.inviter) if invitation.inviter else None,
        "repository": _simplify_repo(invitation.repository) if invitation.repository else None,
        "permissions": invitation.permissions,
    }

def _simplify_project(project: Project) -> dict:
    return {"id": project.id, "name": project.name, "body": project.body, "url": project.html_url}

def _simplify_project_column(column: ProjectColumn) -> dict:
    return {"id": column.id, "name": column.name}

def _simplify_project_card(card: ProjectCard) -> dict:
    return {"id": card.id, "note": card.note, "content_url": card.content_url}

def _simplify_workflow(workflow: Workflow) -> dict:
    return {"id": workflow.id, "name": workflow.name, "state": workflow.state, "path": workflow.path}

def _simplify_workflow_run(run: WorkflowRun) -> dict:
    return {
        "id": run.id,
        "name": run.name,
        "status": run.status,
        "conclusion": run.conclusion,
        "head_branch": run.head_branch,
        "created_at": run.created_at.isoformat()
    }

def _simplify_contributor_stats(stats: StatsContributor) -> dict:
    return {
        "author": _simplify_user(stats.author),
        "total": stats.total,
        "weeks": [{"additions": w.a, "deletions": w.d, "commits": w.c} for w in stats.weeks]
    }

def _simplify_commit_activity(activity: StatsCommitActivity) -> dict:
    return {"week": activity.week.isoformat(), "total": activity.total, "days": activity.days}

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
        "body": issue.body
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