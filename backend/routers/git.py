"""Git integration router.

All operations run inside the project's Docker container.
The project must be running (container started) before calling these endpoints.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.rate_limiter import limiter, user_limit
from core.security import TokenData, get_current_user
from database.mongo import get_database
from database.sql import get_db
from models.mongo_models import ProjectCollection

router = APIRouter(prefix="/git", tags=["git"])


# --- request schemas ---

class CommitRequest(BaseModel):
    message: str
    stage_all: bool = True


class PushRequest(BaseModel):
    remote: str = "origin"
    branch: Optional[str] = None


class PullRequest(BaseModel):
    remote: str = "origin"
    branch: Optional[str] = None


class CheckoutRequest(BaseModel):
    branch: str
    create: bool = False


class SetRemoteRequest(BaseModel):
    url: str
    name: str = "origin"


class InitRequest(BaseModel):
    pass


class CloneRequest(BaseModel):
    url: str


# --- helpers ---

async def _get_container_id(project_id: str, owner_id: str) -> str:
    """Resolve container_id for a project, verify ownership, ensure container is running."""
    db = get_database()
    doc = await ProjectCollection.find_by_id(db, project_id)
    if not doc or doc["owner_id"] != owner_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    container_id = doc.get("container_id")
    if not container_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Project container is not running. Start the project first.",
        )
    return container_id


# --- endpoints ---

@router.get("/{project_id}/status")
@limiter.limit(user_limit())
async def git_status(
    project_id: str,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return git status for the project workspace."""
    from services.git_service import git_status as _git_status
    container_id = await _get_container_id(project_id, current_user.user_id)
    return await _git_status(container_id)


@router.get("/{project_id}/log")
@limiter.limit(user_limit())
async def git_log(
    project_id: str,
    request: Request,
    limit: int = 20,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return recent commit history."""
    from services.git_service import git_log as _git_log
    container_id = await _get_container_id(project_id, current_user.user_id)
    return await _git_log(container_id, limit=min(limit, 100))


@router.get("/{project_id}/branches")
@limiter.limit(user_limit())
async def git_branches(
    project_id: str,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List local and remote branches."""
    from services.git_service import git_branches as _git_branches
    container_id = await _get_container_id(project_id, current_user.user_id)
    return await _git_branches(container_id)


@router.get("/{project_id}/diff")
@limiter.limit(user_limit())
async def git_diff(
    project_id: str,
    request: Request,
    staged: bool = False,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return diff output."""
    from services.git_service import git_diff as _git_diff
    container_id = await _get_container_id(project_id, current_user.user_id)
    diff = await _git_diff(container_id, staged=staged)
    return {"diff": diff}


@router.get("/{project_id}/remotes")
@limiter.limit(user_limit())
async def git_remotes(
    project_id: str,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List configured git remotes."""
    from services.git_service import git_remote_info as _git_remote_info
    container_id = await _get_container_id(project_id, current_user.user_id)
    return await _git_remote_info(container_id)


@router.post("/{project_id}/pull")
@limiter.limit("30/minute")
async def git_pull(
    project_id: str,
    payload: PullRequest,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Pull latest changes from remote. Uses SSH key (injected) or PAT (HTTPS) automatically."""
    from services.git_service import git_pull as _git_pull, git_status as _git_status
    from services.vault_service import VaultService
    container_id = await _get_container_id(project_id, current_user.user_id)
    # Look up remote URL to find matching PAT
    status = await _git_status(container_id)
    pat = await VaultService.get_git_pat_for_url(current_user.user_id, status.get("remote") or "", db)
    result = await _git_pull(container_id, remote=payload.remote, branch=payload.branch, pat=pat)
    return {"output": result.output}


@router.post("/{project_id}/push")
@limiter.limit("20/minute")
async def git_push(
    project_id: str,
    payload: PushRequest,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Push current branch to remote. Uses SSH key (injected) or PAT (HTTPS) automatically."""
    from services.git_service import git_push as _git_push, git_status as _git_status
    from services.vault_service import VaultService
    container_id = await _get_container_id(project_id, current_user.user_id)
    status = await _git_status(container_id)
    pat = await VaultService.get_git_pat_for_url(current_user.user_id, status.get("remote") or "", db)
    result = await _git_push(container_id, remote=payload.remote, branch=payload.branch, pat=pat)
    return {"output": result.output}


@router.post("/{project_id}/commit")
@limiter.limit("60/minute")
async def git_commit(
    project_id: str,
    payload: CommitRequest,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Stage all changes and create a commit."""
    from services.git_service import git_commit as _git_commit
    container_id = await _get_container_id(project_id, current_user.user_id)
    result = await _git_commit(container_id, message=payload.message, stage_all=payload.stage_all)
    return {"output": result.output}


@router.post("/{project_id}/checkout")
@limiter.limit(user_limit())
async def git_checkout(
    project_id: str,
    payload: CheckoutRequest,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Switch branch or create a new one."""
    from services.git_service import git_checkout as _git_checkout
    container_id = await _get_container_id(project_id, current_user.user_id)
    result = await _git_checkout(container_id, branch=payload.branch, create=payload.create)
    return {"output": result.output}


@router.post("/{project_id}/remote")
@limiter.limit(user_limit())
async def git_set_remote(
    project_id: str,
    payload: SetRemoteRequest,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add or update a git remote (e.g. set origin to a new SSH URL)."""
    from services.git_service import git_set_remote as _git_set_remote
    container_id = await _get_container_id(project_id, current_user.user_id)
    result = await _git_set_remote(container_id, url=payload.url, name=payload.name)
    return {"output": result.output, "success": result.success}


@router.post("/{project_id}/init")
@limiter.limit("10/minute")
async def git_init(
    project_id: str,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Initialize a git repository in the workspace (git init + initial commit)."""
    from services.git_service import git_init as _git_init
    container_id = await _get_container_id(project_id, current_user.user_id)
    result = await _git_init(container_id)
    return {"output": result.output, "success": result.success}


@router.post("/{project_id}/clone")
@limiter.limit("10/minute")
async def git_clone(
    project_id: str,
    payload: CloneRequest,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Clone a remote repository into the workspace.

    For HTTPS private repos: save a GitHub/GitLab PAT in Settings → API Keys first.
    For SSH private repos: generate an SSH key in the Git panel SSH tab first.
    """
    from services.git_service import git_clone as _git_clone
    from services.vault_service import VaultService
    container_id = await _get_container_id(project_id, current_user.user_id)
    pat = await VaultService.get_git_pat_for_url(current_user.user_id, payload.url, db)
    result = await _git_clone(container_id, url=payload.url, pat=pat)
    return {"output": result.output, "success": result.success}
