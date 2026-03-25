"""Git integration service.

All git commands run inside the project's Docker container via exec_run.
The container must have git installed (base image) and an SSH key injected
via inject_ssh_key (container_service) for push/pull on private repos.

Operations:
  - status       : working tree status (porcelain v1)
  - log          : recent commit history
  - branches     : list local + remote branches
  - pull         : fetch + merge from remote
  - push         : push current branch to remote
  - commit       : stage all changes and create a commit
  - checkout     : switch or create a branch
  - diff         : show unstaged or staged diff
  - remote_info  : show configured remotes
  - set_remote   : add/update origin remote URL
"""
import asyncio
import logging
from dataclasses import dataclass
from typing import Optional

from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


@dataclass
class GitResult:
    success: bool
    output: str
    exit_code: int


def _inject_pat_into_url(url: str, pat: str) -> str:
    """Return an HTTPS URL with the PAT embedded: https://token@host/path."""
    if not pat or not url.startswith("https://"):
        return url
    # Strip any existing credentials first
    clean = url.replace("https://", "")
    if "@" in clean:
        clean = clean.split("@", 1)[1]
    return f"https://oauth2:{pat}@{clean}"


async def _exec(container_id: str, cmd: str) -> GitResult:
    """Run a shell command inside the container and return the result."""
    from services.container_service import get_docker_client

    def _run():
        client = get_docker_client()
        container = client.containers.get(container_id)
        exit_code, output = container.exec_run(
            cmd=["bash", "-c", cmd],
            workdir="/workspace",
            environment={"GIT_TERMINAL_PROMPT": "0"},
            stream=False,
            demux=False,
        )
        text = output.decode("utf-8", errors="replace") if output else ""
        return exit_code, text

    exit_code, text = await asyncio.to_thread(_run)
    return GitResult(success=exit_code == 0, output=text.strip(), exit_code=exit_code)


def _require_git(result: GitResult, operation: str) -> GitResult:
    """Raise HTTP 400 if the git command failed."""
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"git {operation} failed: {result.output}",
        )
    return result


async def git_status(container_id: str) -> dict:
    """Return working tree status."""
    result = await _exec(container_id, "git status --porcelain=v1 && echo '---' && git status -b --short")
    is_repo = await _exec(container_id, "git rev-parse --is-inside-work-tree 2>/dev/null")
    if not is_repo.success:
        return {"initialized": False, "files": [], "branch": None, "clean": True}

    branch_result = await _exec(container_id, "git branch --show-current")
    remote_result = await _exec(container_id, "git remote get-url origin 2>/dev/null || echo ''")
    ahead_behind = await _exec(
        container_id,
        "git rev-list --left-right --count HEAD...@{upstream} 2>/dev/null || echo '0\t0'"
    )

    files = []
    for line in result.output.splitlines():
        if len(line) >= 2 and line[0] != '-':
            xy = line[:2]
            path = line[3:].strip()
            if path:
                files.append({"status": xy, "path": path})

    ahead, behind = 0, 0
    if ahead_behind.success and "\t" in ahead_behind.output:
        parts = ahead_behind.output.strip().split("\t")
        if len(parts) == 2:
            try:
                ahead, behind = int(parts[0]), int(parts[1])
            except ValueError:
                pass

    return {
        "initialized": True,
        "branch": branch_result.output.strip(),
        "remote": remote_result.output.strip() or None,
        "files": files,
        "clean": len(files) == 0,
        "ahead": ahead,
        "behind": behind,
    }


async def git_log(container_id: str, limit: int = 20) -> list[dict]:
    """Return recent commit history."""
    result = await _exec(
        container_id,
        f"git log --oneline --format='%H|%h|%s|%an|%ae|%ar' -{limit} 2>/dev/null"
    )
    if not result.success or not result.output:
        return []

    commits = []
    for line in result.output.splitlines():
        parts = line.split("|", 5)
        if len(parts) == 6:
            commits.append({
                "hash": parts[0],
                "short_hash": parts[1],
                "message": parts[2],
                "author": parts[3],
                "email": parts[4],
                "ago": parts[5],
            })
    return commits


async def git_branches(container_id: str) -> dict:
    """List local and remote branches."""
    local = await _exec(container_id, "git branch --format='%(refname:short)' 2>/dev/null")
    remote = await _exec(container_id, "git branch -r --format='%(refname:short)' 2>/dev/null")
    current = await _exec(container_id, "git branch --show-current 2>/dev/null")

    return {
        "current": current.output.strip(),
        "local": [b.strip() for b in local.output.splitlines() if b.strip()],
        "remote": [b.strip() for b in remote.output.splitlines() if b.strip()],
    }


async def git_pull(container_id: str, remote: str = "origin", branch: Optional[str] = None, pat: Optional[str] = None) -> GitResult:
    """Pull from remote. Uses SSH key (injected) or PAT (HTTPS) for auth."""
    branch_arg = branch or ""
    if pat:
        # Get remote URL and inject PAT
        url_result = await _exec(container_id, f"git remote get-url {remote} 2>/dev/null")
        if url_result.success and url_result.output.startswith("https://"):
            auth_url = _inject_pat_into_url(url_result.output.strip(), pat)
            safe_url = auth_url.replace("'", "")
            result = await _exec(container_id, f"git pull '{safe_url}' {branch_arg} --ff-only 2>&1")
            return _require_git(result, "pull")
    result = await _exec(container_id, f"git pull {remote} {branch_arg} --ff-only 2>&1")
    return _require_git(result, "pull")


async def git_push(container_id: str, remote: str = "origin", branch: Optional[str] = None, force: bool = False, pat: Optional[str] = None) -> GitResult:
    """Push to remote."""
    if force:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Force push is disabled for safety.",
        )
    branch_cmd = branch or "HEAD"
    if pat:
        url_result = await _exec(container_id, f"git remote get-url {remote} 2>/dev/null")
        if url_result.success and url_result.output.startswith("https://"):
            auth_url = _inject_pat_into_url(url_result.output.strip(), pat)
            safe_url = auth_url.replace("'", "")
            result = await _exec(container_id, f"git push '{safe_url}' {branch_cmd} 2>&1")
            return _require_git(result, "push")
    result = await _exec(container_id, f"git push {remote} {branch_cmd} 2>&1")
    return _require_git(result, "push")


async def git_commit(container_id: str, message: str, stage_all: bool = True) -> GitResult:
    """Stage and commit changes."""
    if not message.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Commit message must not be empty.")

    safe_msg = message.replace("'", "'\\''")
    stage_cmd = "git add -A && " if stage_all else ""
    result = await _exec(
        container_id,
        f"{stage_cmd}git commit -m '{safe_msg}' 2>&1"
    )
    return _require_git(result, "commit")


async def git_checkout(container_id: str, branch: str, create: bool = False) -> GitResult:
    """Switch to an existing branch or create a new one."""
    flag = "-b" if create else ""
    safe_branch = branch.replace("'", "").replace(";", "").replace("&", "").replace("|", "")
    result = await _exec(container_id, f"git checkout {flag} '{safe_branch}' 2>&1")
    return _require_git(result, "checkout")


async def git_diff(container_id: str, staged: bool = False) -> str:
    """Return diff output (unstaged by default, staged if staged=True)."""
    flag = "--cached" if staged else ""
    result = await _exec(container_id, f"git diff {flag} 2>/dev/null")
    return result.output


async def git_remote_info(container_id: str) -> list[dict]:
    """Return configured remotes."""
    result = await _exec(container_id, "git remote -v 2>/dev/null")
    remotes: dict[str, dict] = {}
    for line in result.output.splitlines():
        parts = line.split()
        if len(parts) >= 2:
            name = parts[0]
            url = parts[1]
            if name not in remotes:
                remotes[name] = {"name": name, "url": url}
    return list(remotes.values())


async def git_set_remote(container_id: str, url: str, name: str = "origin") -> GitResult:
    """Add or update a remote."""
    safe_name = name.replace("'", "").replace(";", "")
    safe_url = url.replace("'", "").replace(";", "")
    # Try update first, fall back to add
    result = await _exec(
        container_id,
        f"git remote set-url '{safe_name}' '{safe_url}' 2>/dev/null || git remote add '{safe_name}' '{safe_url}'"
    )
    return result


async def git_init(container_id: str) -> GitResult:
    """Initialize a git repository in /workspace."""
    result = await _exec(container_id, "git init && git add -A && git commit -m 'Initial commit' 2>&1")
    return result


async def git_clone(container_id: str, url: str, pat: Optional[str] = None) -> GitResult:
    """Clone a remote repository into /workspace.

    The workspace must be empty. Supports:
    - SSH URLs (git@…): SSH key must already be injected via inject_ssh_key
    - HTTPS URLs: pass `pat` for private repos
    """
    is_ssh = url.startswith("git@") or url.startswith("ssh://")
    if pat and not is_ssh:
        clone_url = _inject_pat_into_url(url, pat)
    else:
        clone_url = url
    safe_url = clone_url.replace("'", "")
    ssh_env = "GIT_SSH_COMMAND='ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null' " if is_ssh else ""
    result = await _exec(
        container_id,
        f"{ssh_env}git clone --depth 1 '{safe_url}' . 2>&1"
    )
    return _require_git(result, "clone")
