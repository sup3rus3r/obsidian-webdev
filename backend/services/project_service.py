"""Project CRUD service — MongoDB only (all DATABASE_TYPE modes)."""
import asyncio
import logging
import os
import shutil
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException

from config import settings
from database.mongo import get_database
from models.mongo_models import ProjectCollection, ProjectFileCollection
from schemas.projects import ProjectCreate, ProjectImportGitHub, ProjectUpdate

logger = logging.getLogger(__name__)


async def _inject_template_bg(project_id: str, container_id: str, framework: str, github_url: Optional[str] = None) -> None:
    """Background task: run CLI scaffold commands, sync files to MongoDB, then set status running."""
    from services.container_service import inject_template
    from services.file_service import FileService

    db = get_database()
    try:
        exit_code, output = await inject_template(container_id, framework, github_url=github_url)
        if exit_code != 0:
            logger.warning(
                "Template injection non-zero exit for project %s (exit=%d): %s",
                project_id, exit_code, output[-500:],
            )
        else:
            logger.info("Template injected for project %s (%s)", project_id, framework)


        try:
            count = await FileService.sync_from_volume(project_id)
            logger.info("Synced %d files to MongoDB for project %s", count, project_id)
        except Exception:
            logger.exception("File sync error after template injection for project %s", project_id)

    except Exception:
        logger.exception("Template injection error for project %s", project_id)
    finally:
        try:
            await ProjectCollection.update(db, project_id, {
                "status": "running",
                "template_ready": True,
                "updated_at": datetime.now(timezone.utc),
            })
        except Exception:
            # Suppress errors during shutdown (e.g. MongoClient already closed)
            pass


def _to_response(doc: dict) -> dict:
    """Convert a MongoDB document to a response-safe dict."""
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    return doc


def _project_dir(project_id: str) -> str:
    return os.path.join(settings.PROJECTS_DATA_DIR, project_id)


class ProjectService:

    @staticmethod
    async def create_project(owner_id: str, payload: ProjectCreate) -> dict:
        db = get_database()
        existing = await db["projects"].find_one(
            {"owner_id": owner_id, "name": payload.name}
        )
        if existing:
            raise HTTPException(status_code=409, detail="A project with that name already exists")

        now = datetime.now(timezone.utc)
        doc = {
            "owner_id": owner_id,
            "name": payload.name,
            "description": payload.description,
            "framework": payload.framework,
            "model_provider": payload.model_provider,
            "model_id": payload.model_id,
            "status": "idle",
            "build_status": "none",
            "container_id": None,
            "host_port": None,
            "created_at": now,
            "updated_at": now,
        }
        created = await ProjectCollection.create(db, doc)

        os.makedirs(_project_dir(str(created["_id"])), exist_ok=True)

        return _to_response(created)

    @staticmethod
    async def create_imported_github(owner_id: str, payload: ProjectImportGitHub) -> dict:
        """Create a project that will be populated by git clone on first run."""
        db = get_database()
        existing = await db["projects"].find_one(
            {"owner_id": owner_id, "name": payload.name}
        )
        if existing:
            raise HTTPException(status_code=409, detail="A project with that name already exists")

        now = datetime.now(timezone.utc)
        doc = {
            "owner_id": owner_id,
            "name": payload.name,
            "description": payload.description,
            "framework": "blank",
            "model_provider": payload.model_provider,
            "model_id": payload.model_id,
            "status": "idle",
            "build_status": "none",
            "container_id": None,
            "host_port": None,
            "github_url": payload.github_url,
            "created_at": now,
            "updated_at": now,
        }
        created = await ProjectCollection.create(db, doc)
        os.makedirs(_project_dir(str(created["_id"])), exist_ok=True)
        return _to_response(created)

    @staticmethod
    async def create_imported_zip(
        owner_id: str,
        name: str,
        description: str,
        model_provider: str,
        model_id: str,
        zip_bytes: bytes,
    ) -> dict:
        """Create a project and extract the uploaded zip into its directory."""
        import zipfile
        from io import BytesIO

        db = get_database()
        existing = await db["projects"].find_one({"owner_id": owner_id, "name": name})
        if existing:
            raise HTTPException(status_code=409, detail="A project with that name already exists")

        now = datetime.now(timezone.utc)
        doc = {
            "owner_id": owner_id,
            "name": name,
            "description": description,
            "framework": "blank",
            "model_provider": model_provider,
            "model_id": model_id,
            "status": "idle",
            "build_status": "none",
            "container_id": None,
            "host_port": None,
            "template_ready": True,
            "created_at": now,
            "updated_at": now,
        }
        created = await ProjectCollection.create(db, doc)
        project_id = str(created["_id"])
        project_dir = _project_dir(project_id)
        os.makedirs(project_dir, exist_ok=True)

        _EXCLUDE_DIRS = frozenset({
            "node_modules", ".git", ".next", "__pycache__", ".venv", "venv",
            ".mypy_cache", ".pytest_cache", "dist", "build", ".turbo",
            ".cache", "coverage", ".yarn",
        })

        def _extract():
            with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
                # Detect common root prefix (e.g. repo-main/)
                names = zf.namelist()
                prefix = ""
                if names:
                    parts = names[0].split("/")
                    if len(parts) > 1 and all(n.startswith(parts[0] + "/") for n in names if n):
                        prefix = parts[0] + "/"

                for member in zf.infolist():
                    rel = member.filename
                    if prefix:
                        rel = rel[len(prefix):]
                    if not rel:
                        continue
                    # Skip excluded directories
                    parts = rel.split("/")
                    if any(p in _EXCLUDE_DIRS for p in parts[:-1]):
                        continue
                    # Skip .env files
                    filename = parts[-1]
                    if filename == ".env" or filename.endswith(".env"):
                        continue
                    dest = os.path.join(project_dir, rel)
                    if member.is_dir():
                        os.makedirs(dest, exist_ok=True)
                    else:
                        os.makedirs(os.path.dirname(dest), exist_ok=True)
                        with zf.open(member) as src, open(dest, "wb") as dst:
                            dst.write(src.read())

        await asyncio.to_thread(_extract)

        # Sync extracted files to MongoDB
        try:
            from services.file_service import FileService
            await FileService.sync_from_volume(project_id)
        except Exception:
            logger.exception("File sync error after zip import for project %s", project_id)

        return _to_response(created)

    @staticmethod
    async def list_projects(owner_id: str) -> list[dict]:
        db = get_database()
        docs = await ProjectCollection.find_by_owner(db, owner_id)
        return [_to_response(d) for d in docs]

    @staticmethod
    async def get_project(project_id: str, owner_id: str) -> dict:
        db = get_database()
        doc = await ProjectCollection.find_by_id(db, project_id)
        if not doc or doc["owner_id"] != owner_id:
            raise HTTPException(status_code=404, detail="Project not found")
        return _to_response(doc)

    @staticmethod
    async def update_project(project_id: str, owner_id: str, payload: ProjectUpdate) -> dict:
        db = get_database()
        doc = await ProjectCollection.find_by_id(db, project_id)
        if not doc or doc["owner_id"] != owner_id:
            raise HTTPException(status_code=404, detail="Project not found")

        update_data = payload.model_dump(exclude_none=True)
        if not update_data:
            return _to_response(doc)

        update_data["updated_at"] = datetime.now(timezone.utc)
        updated = await ProjectCollection.update(db, project_id, update_data)
        return _to_response(updated)

    @staticmethod
    async def run_container(project_id: str, owner_id: str) -> dict:
        """Start (or restart) the project's Docker container and return the updated project.

        For brand-new projects (no files in MongoDB), fires a background task to scaffold
        the framework template via CLI commands.  The project status is set to "preparing"
        during scaffold and transitions to "running" once done.
        """
        from services.container_service import (
            get_or_create_container,
            restore_files_from_mongo,
            start_dev_server,
        )

        db = get_database()
        doc = await ProjectCollection.find_by_id(db, project_id)
        if not doc or doc["owner_id"] != owner_id:
            raise HTTPException(status_code=404, detail="Project not found")

        framework = doc.get("framework", "blank")
        template_ready = doc.get("template_ready", False)
        github_url = doc.get("github_url")

        try:
            container_id, host_port, host_ports = await get_or_create_container(project_id, framework)
            await restore_files_from_mongo(project_id)
            await start_dev_server(container_id, framework)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Container start failed: {exc}")


        file_count = await ProjectFileCollection.count_by_project(db, project_id)
        needs_template = (framework != "blank" or github_url) and not template_ready and file_count == 0

        needs_sync = template_ready and file_count == 0

        if needs_sync:

            try:
                from services.file_service import FileService
                count = await FileService.sync_from_volume(project_id)
                if count == 0 and framework != "blank":

                    logger.info("Volume empty for project %s, re-injecting template", project_id)
                    needs_template = True
                    needs_sync = False
                else:
                    logger.info("Retroactive sync: %d files synced for project %s", count, project_id)
            except Exception:
                logger.exception("Retroactive sync failed for project %s", project_id)

        now = datetime.now(timezone.utc)
        if needs_template:
            updated = await ProjectCollection.update(db, project_id, {
                "status": "preparing",
                "container_id": container_id,
                "host_port": host_port,
                "host_ports": host_ports,
                "updated_at": now,
            })
            asyncio.create_task(
                _inject_template_bg(project_id, container_id, framework, github_url=github_url)
            )
        else:
            updated = await ProjectCollection.update(db, project_id, {
                "status": "running",
                "container_id": container_id,
                "host_port": host_port,
                "host_ports": host_ports,
                "updated_at": now,
            })

        return _to_response(updated)

    @staticmethod
    async def stop_container(project_id: str, owner_id: str) -> dict:
        """Stop the project's Docker container (files are preserved)."""
        from services.container_service import stop_container as _stop_container

        db = get_database()
        doc = await ProjectCollection.find_by_id(db, project_id)
        if not doc or doc["owner_id"] != owner_id:
            raise HTTPException(status_code=404, detail="Project not found")

        container_id = doc.get("container_id")
        if container_id:
            try:
                await _stop_container(container_id)
            except Exception:
                pass

        updated = await ProjectCollection.update(db, project_id, {
            "status": "stopped",
            "preview_url": None,
            "updated_at": datetime.now(timezone.utc),
        })
        return _to_response(updated)

    @staticmethod
    async def probe_preview_port(project_id: str, owner_id: str) -> dict:
        """Probe the container's dev server and return a directly-loadable preview URL.

        Returns {"preview_url": <url>} and caches the result in the DB.
        On Linux the URL uses the container's Docker bridge IP + dev port.
        On Windows it falls back to localhost + the Docker-mapped host port.
        """
        from services.container_service import probe_preview_url

        db = get_database()
        doc = await ProjectCollection.find_by_id(db, project_id)
        if not doc or doc["owner_id"] != owner_id:
            raise HTTPException(status_code=404, detail="Project not found")

        container_id = doc.get("container_id")
        host_ports: dict[str, int] = doc.get("host_ports") or {}

        if not container_id:
            return {"preview_url": None}

        url = await probe_preview_url(container_id, host_ports)
        if url and url != doc.get("preview_url"):
            await ProjectCollection.update(db, project_id, {"preview_url": url})
        return {"preview_url": url}

    @staticmethod
    async def delete_project(project_id: str, owner_id: str) -> None:
        db = get_database()
        doc = await ProjectCollection.find_by_id(db, project_id)
        if not doc or doc["owner_id"] != owner_id:
            raise HTTPException(status_code=404, detail="Project not found")

        container_id = doc.get("container_id")
        if container_id:
            try:
                from services.container_service import stop_container, remove_container
                await stop_container(container_id)
                await remove_container(container_id, force=True)
            except Exception:
                pass

        await ProjectFileCollection.delete_all(db, project_id)

        project_dir = _project_dir(project_id)
        if os.path.exists(project_dir):
            shutil.rmtree(project_dir, ignore_errors=True)

        try:
            from services.embedding_service import delete_project_index
            await delete_project_index(project_id)
        except Exception:
            pass

        try:
            await db["agent_sessions"].delete_many({"project_id": project_id})
        except Exception:
            pass

        deleted = await ProjectCollection.delete(db, project_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Project not found")
