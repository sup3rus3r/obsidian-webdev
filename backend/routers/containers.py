"""Container lifecycle router."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request

from core.rate_limiter import limiter, user_limit
from core.security import TokenData, get_current_user
from database.mongo import get_database
from models.mongo_models import ProjectCollection
from schemas.containers import (
    ContainerStartResponse,
    ContainerStatusResponse,
    ExecRequest,
    ExecResponse,
)
from services.container_service import (
    FRAMEWORK_CONFIG,
    exec_command,
    get_container_port,
    get_or_create_container,
    remove_container,
    restore_files_from_mongo,
    stop_container,
)

router = APIRouter(prefix="/containers", tags=["containers"])


async def _get_owned_project(project_id: str, owner_id: str) -> dict:
    db = get_database()
    doc = await ProjectCollection.find_by_id(db, project_id)
    if not doc or doc["owner_id"] != owner_id:
        raise HTTPException(status_code=404, detail="Project not found")
    return doc


@router.post("/{project_id}/start", response_model=ContainerStartResponse)
@limiter.limit(user_limit())
async def start_container(
    project_id: str,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
):
    """Get or create a container for the project.

    - If a stopped container already exists it is restarted (fast, no re-provision).
    - If no container exists, a fresh one is created and MongoDB files are synced
      to the volume.
    """
    project = await _get_owned_project(project_id, current_user.user_id)
    framework = project.get("framework", "blank")
    had_container = bool(project.get("container_id"))

    container_id, host_port = await get_or_create_container(project_id, framework)

    files_restored = 0
    if not had_container:
        files_restored = await restore_files_from_mongo(project_id)

    db = get_database()
    now = datetime.now(timezone.utc)
    await ProjectCollection.update(
        db,
        project_id,
        {
            "container_id": container_id,
            "host_port": host_port,
            "status": "running",
            "updated_at": now,
        },
    )

    return ContainerStartResponse(
        project_id=project_id,
        container_id=container_id,
        host_port=host_port,
        status="running",
        files_restored=files_restored,
    )


@router.post("/{project_id}/stop", response_model=ContainerStatusResponse)
@limiter.limit(user_limit())
async def stop_project_container(
    project_id: str,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
):
    """Stop a running container (does NOT remove it). Files are preserved."""
    project = await _get_owned_project(project_id, current_user.user_id)
    container_id = project.get("container_id")

    if not container_id:
        raise HTTPException(status_code=409, detail="No active container for this project")

    await stop_container(container_id)

    db = get_database()
    await ProjectCollection.update(
        db,
        project_id,
        {"status": "stopped", "updated_at": datetime.now(timezone.utc)},
    )

    return ContainerStatusResponse(
        project_id=project_id,
        container_id=container_id,
        host_port=project.get("host_port"),
        status="stopped",
    )


@router.get("/{project_id}/port")
@limiter.limit(user_limit())
async def get_port(
    project_id: str,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
):
    """Return the current host port mapping for the project's dev server."""
    project = await _get_owned_project(project_id, current_user.user_id)
    framework = project.get("framework", "blank")
    port = await get_container_port(project_id, framework)
    return {"project_id": project_id, "host_port": port}


@router.delete("/{project_id}", status_code=204)
@limiter.limit(user_limit())
async def remove_project_container(
    project_id: str,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
):
    """Force-remove the container entirely. Files in MongoDB are preserved."""
    project = await _get_owned_project(project_id, current_user.user_id)
    container_id = project.get("container_id")

    if container_id:
        await remove_container(container_id, force=True)

    db = get_database()
    await ProjectCollection.update(
        db,
        project_id,
        {
            "container_id": None,
            "host_port": None,
            "status": "stopped",
            "updated_at": datetime.now(timezone.utc),
        },
    )


@router.post("/{project_id}/exec", response_model=ExecResponse)
@limiter.limit("30/minute")
async def exec_in_container(
    project_id: str,
    payload: ExecRequest,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
):
    """Run a shell command in the project container and return stdout/stderr.

    Restricted to admin users. The agent uses this internally; direct use is
    for debugging / manual operations.
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")

    project = await _get_owned_project(project_id, current_user.user_id)
    container_id = project.get("container_id")

    if not container_id:
        raise HTTPException(status_code=409, detail="No active container for this project")

    exit_code, output = await exec_command(container_id, payload.cmd, payload.workdir)
    return ExecResponse(exit_code=exit_code, output=output)
