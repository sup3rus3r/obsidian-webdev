"""Project management router."""
import base64
import io

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response, UploadFile

from core.rate_limiter import limiter, user_limit
from core.security import TokenData, get_current_user
from schemas.files import FileListItem, FileListResponse, FileWriteRequest, ProjectFileResponse
from schemas.projects import (
    ProjectCreate,
    ProjectImportGitHub,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdate,
)
from services.file_service import FileService
from services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse, status_code=201)
@limiter.limit(user_limit())
async def create_project(
    payload: ProjectCreate,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
):
    """Create a new project. Name must be unique per user."""
    return await ProjectService.create_project(current_user.user_id, payload)


@router.post("/import/github", response_model=ProjectResponse, status_code=201)
@limiter.limit(user_limit())
async def import_from_github(
    payload: ProjectImportGitHub,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
):
    """Import a project from a public GitHub repository URL.

    The repository is cloned into the container on first run.
    """
    return await ProjectService.create_imported_github(current_user.user_id, payload)


_MAX_ZIP_MB = 100


@router.post("/import/zip", response_model=ProjectResponse, status_code=201)
@limiter.limit(user_limit())
async def import_from_zip(
    request: Request,
    file: UploadFile,
    name: str = Form(...),
    description: str = Form(""),
    model_provider: str = Form("anthropic"),
    model_id: str = Form("claude-sonnet-4-6"),
    current_user: TokenData = Depends(get_current_user),
):
    """Import a project from an uploaded ZIP file.

    node_modules, .git, .env files and other build artifacts are excluded.
    Files are extracted to the project volume and synced to MongoDB immediately.
    """
    if file.content_type not in ("application/zip", "application/x-zip-compressed", "application/octet-stream"):
        # be lenient — browsers send different MIME types for zips
        if not (file.filename or "").endswith(".zip"):
            raise HTTPException(status_code=415, detail="Only .zip files are accepted")

    data = await file.read()
    if len(data) > _MAX_ZIP_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File too large (max {_MAX_ZIP_MB} MB)")

    name = name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Project name must not be empty")
    if len(name) > 100:
        raise HTTPException(status_code=422, detail="Project name must be 100 characters or fewer")
    model_id = model_id.strip()
    if not model_id:
        raise HTTPException(status_code=422, detail="model_id must not be empty")

    return await ProjectService.create_imported_zip(
        owner_id=current_user.user_id,
        name=name,
        description=description,
        model_provider=model_provider,
        model_id=model_id,
        zip_bytes=data,
    )


@router.get("", response_model=ProjectListResponse)
@limiter.limit(user_limit())
async def list_projects(
    request: Request,
    current_user: TokenData = Depends(get_current_user),
):
    """List all projects owned by the current user."""
    docs = await ProjectService.list_projects(current_user.user_id)
    return {"projects": docs}


@router.get("/{project_id}", response_model=ProjectResponse)
@limiter.limit(user_limit())
async def get_project(
    project_id: str,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
):
    """Get project details."""
    return await ProjectService.get_project(project_id, current_user.user_id)


@router.put("/{project_id}", response_model=ProjectResponse)
@limiter.limit(user_limit())
async def update_project(
    project_id: str,
    payload: ProjectUpdate,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
):
    """Update project metadata (name, description, model settings)."""
    return await ProjectService.update_project(project_id, current_user.user_id, payload)


@router.delete("/{project_id}", status_code=204)
@limiter.limit(user_limit())
async def delete_project(
    project_id: str,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
):
    """Delete a project and all associated files."""
    await ProjectService.delete_project(project_id, current_user.user_id)


@router.get("/{project_id}/files", response_model=FileListResponse)
@limiter.limit(user_limit())
async def list_files(
    project_id: str,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
):
    """List all files in a project (metadata only, no content)."""
    items = await FileService.list_files(project_id, current_user.user_id)
    return {"files": items}


@router.get("/{project_id}/files/{path:path}", response_model=ProjectFileResponse)
@limiter.limit(user_limit())
async def get_file(
    project_id: str,
    path: str,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
):
    """Get a single file's content."""
    return await FileService.get_file(project_id, path, current_user.user_id)


@router.put("/{project_id}/files/{path:path}", response_model=ProjectFileResponse)
@limiter.limit(user_limit())
async def write_file(
    project_id: str,
    path: str,
    payload: FileWriteRequest,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
):
    """Create or overwrite a file. Dual-written to MongoDB and host volume."""
    return await FileService.write_file(project_id, path, current_user.user_id, payload)


@router.delete("/{project_id}/files/{path:path}", status_code=204)
@limiter.limit(user_limit())
async def delete_file(
    project_id: str,
    path: str,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
):
    """Delete a file from MongoDB and the host volume."""
    await FileService.delete_file(project_id, path, current_user.user_id)


@router.post("/{project_id}/run", response_model=ProjectResponse)
@limiter.limit(user_limit())
async def run_project(
    project_id: str,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
):
    """Start (or restart) the project's Docker container.

    Creates the container on first run.  Restarts it if stopped.  MongoDB
    files are synced to the volume so the container always has the latest code.
    """
    return await ProjectService.run_container(project_id, current_user.user_id)


@router.post("/{project_id}/stop", response_model=ProjectResponse)
@limiter.limit(user_limit())
async def stop_project(
    project_id: str,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
):
    """Stop the project's Docker container (preserves all files)."""
    return await ProjectService.stop_container(project_id, current_user.user_id)


@router.get("/{project_id}/probe-preview")
@limiter.limit("60/minute")
async def probe_preview(
    project_id: str,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
):
    """TCP-probe all mapped container ports and return the one the dev server is using.

    Also updates project.host_port in the DB when a different port is found,
    so the preview auto-corrects without any user action.
    """
    return await ProjectService.probe_preview_port(project_id, current_user.user_id)


_ALLOWED_MIME = {
    "application/pdf",
    "image/png", "image/jpeg", "image/gif", "image/webp",
    "text/plain", "text/markdown", "application/json",
}
_MAX_UPLOAD_MB = 10


@router.post("/{project_id}/parse-attachment")
@limiter.limit("30/minute")
async def parse_attachment(
    project_id: str,
    file: UploadFile,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
):
    """Parse an uploaded file (PDF/image/text) and return extractable content.

    Returns:
      { "type": "text"|"image", "content": "...", "filename": "..." }

    PDFs        → extracted text via pypdf
    Images      → base64 data URL (for vision models)
    Text/JSON   → raw text content
    """
    await ProjectService.get_project(project_id, current_user.user_id)

    if file.content_type not in _ALLOWED_MIME:
        raise HTTPException(status_code=415, detail=f"Unsupported file type: {file.content_type}")

    data = await file.read()
    if len(data) > _MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File too large (max {_MAX_UPLOAD_MB} MB)")

    filename = file.filename or "attachment"
    ct = file.content_type or ""

    if ct == "application/pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(data))
            text = "\n".join(
                page.extract_text() or "" for page in reader.pages
            ).strip()
            if not text:
                raise HTTPException(status_code=422, detail="No extractable text found in PDF")
            return {"type": "text", "content": text, "filename": filename}
        except ImportError:
            raise HTTPException(status_code=500, detail="pypdf not installed on server")

    if ct.startswith("image/"):
        b64 = base64.b64encode(data).decode()
        data_url = f"data:{ct};base64,{b64}"
        return {"type": "image", "content": data_url, "filename": filename}

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=422, detail="File is not valid UTF-8 text")
    return {"type": "text", "content": text, "filename": filename}


@router.post("/{project_id}/export")
@limiter.limit("10/minute")
async def export_project(
    project_id: str,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
):
    """Download all project files as a zip archive."""
    zip_bytes = await FileService.export_zip(project_id, current_user.user_id)
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="project-{project_id}.zip"'
        },
    )
