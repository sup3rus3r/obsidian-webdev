"""Project file CRUD service — host volume (source of truth for listing) + MongoDB (cache)."""
import os
import zipfile
from datetime import datetime, timezone
from io import BytesIO

import aiofiles
from fastapi import HTTPException

from config import settings
from database.mongo import get_database
from models.mongo_models import ProjectCollection, ProjectFileCollection
from schemas.files import FileWriteRequest


_SKIP_DIRS = frozenset({
    "node_modules", ".git", ".next", "__pycache__", ".venv", "venv",
    ".mypy_cache", ".pytest_cache", "dist", "build", ".turbo",
    ".cache", "coverage", ".coverage", ".yarn",
})

# File extensions that are binary — stored on the volume only, not in MongoDB.
_BINARY_EXTS = frozenset({
    ".ico", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif",
    ".woff", ".woff2", ".ttf", ".otf", ".eot",
    ".mp4", ".webm", ".mp3", ".wav",
    ".pdf", ".zip", ".gz", ".tar",
    ".bin", ".exe", ".dll", ".so",
})


_MAX_LIST_SIZE = 5 * 1024 * 1024


def _scan_volume(project_dir: str) -> list[str]:
    """Walk the host volume and return relative paths of text source files.

    Excludes binary files (images, fonts, etc.) — those live on the volume only.
    Includes dotfiles like .eslintrc.json, .gitignore, .env.
    """
    results: list[str] = []
    if not os.path.isdir(project_dir):
        return results
    for dirpath, dirnames, filenames in os.walk(project_dir):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS and not d.startswith(".")]
        for fname in filenames:
            _, ext = os.path.splitext(fname.lower())
            if ext in _BINARY_EXTS:
                continue
            abs_path = os.path.join(dirpath, fname)
            try:
                if os.path.getsize(abs_path) > _MAX_LIST_SIZE:
                    continue
            except OSError:
                continue
            rel = os.path.relpath(abs_path, project_dir)
            results.append(rel)
    return sorted(results)


_EXT_TO_LANG: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".jsx": "jsx",
    ".html": "html",
    ".css": "css",
    ".scss": "scss",
    ".json": "json",
    ".md": "markdown",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".sh": "bash",
    ".env": "dotenv",
    ".toml": "toml",
    ".txt": "text",
    ".sql": "sql",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".cpp": "cpp",
    ".c": "c",
    ".rb": "ruby",
    ".dockerfile": "dockerfile",
}


def _detect_language(path: str) -> str:
    name = os.path.basename(path).lower()
    if name == "dockerfile":
        return "dockerfile"
    _, ext = os.path.splitext(name)
    return _EXT_TO_LANG.get(ext, "text")


def _project_dir(project_id: str) -> str:
    return os.path.join(settings.PROJECTS_DATA_DIR, project_id)


def _safe_path(path: str) -> str:
    """Normalise and strip leading slash; raises if traversal detected."""
    normalised = os.path.normpath(path).lstrip("/")
    if normalised.startswith(".."):
        raise HTTPException(status_code=400, detail="Invalid file path")
    return normalised


def _volume_path(project_id: str, safe_rel: str) -> str:
    return os.path.join(_project_dir(project_id), safe_rel)


def _to_response(doc: dict) -> dict:
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    doc["language"] = _detect_language(doc.get("path", ""))
    doc.setdefault("summary", None)
    return doc


def _to_list_item(doc: dict) -> dict:
    d = _to_response(doc)
    d.pop("content", None)
    return d


async def _assert_project_owner(db, project_id: str, owner_id: str) -> None:
    doc = await ProjectCollection.find_by_id(db, project_id)
    if not doc or doc["owner_id"] != owner_id:
        raise HTTPException(status_code=404, detail="Project not found")


class FileService:

    @staticmethod
    async def list_files(project_id: str, owner_id: str) -> list[dict]:
        db = get_database()
        await _assert_project_owner(db, project_id, owner_id)
        docs = await ProjectFileCollection.find_by_project(db, project_id)
        if not docs:


            await FileService.sync_from_volume(project_id)
            docs = await ProjectFileCollection.find_by_project(db, project_id)
        return [_to_list_item(d) for d in docs]

    @staticmethod
    async def sync_from_volume(project_id: str) -> int:
        """Scan the host volume and upsert all source files into MongoDB.

        Called after template injection and on container start when MongoDB has
        no file records but files already exist on disk.
        Returns the number of files synced.
        """
        project_dir = _project_dir(project_id)
        paths = _scan_volume(project_dir)
        if not paths:
            return 0
        db = get_database()
        count = 0
        for rel in paths:
            abs_path = os.path.join(project_dir, rel)
            try:
                async with aiofiles.open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                    content = await f.read()
                await ProjectFileCollection.upsert(db, project_id, rel, content)
                count += 1
            except OSError:
                pass
        return count

    @staticmethod
    async def get_file(project_id: str, path: str, owner_id: str) -> dict:
        db = get_database()
        await _assert_project_owner(db, project_id, owner_id)
        safe = _safe_path(path)


        doc = await ProjectFileCollection.find_by_path(db, project_id, safe)
        if doc:
            return _to_response(doc)


        vol = _volume_path(project_id, safe)
        if not os.path.isfile(vol):
            raise HTTPException(status_code=404, detail="File not found")
        try:
            async with aiofiles.open(vol, "r", encoding="utf-8", errors="replace") as f:
                content = await f.read()
        except OSError as exc:
            raise HTTPException(status_code=500, detail=f"Could not read file: {exc}") from exc
        return {
            "id": None,
            "project_id": project_id,
            "path": safe,
            "content": content,
            "language": _detect_language(safe),
            "summary": None,
        }

    @staticmethod
    async def write_file(
        project_id: str,
        path: str,
        owner_id: str,
        payload: FileWriteRequest,
    ) -> dict:
        db = get_database()
        await _assert_project_owner(db, project_id, owner_id)
        safe = _safe_path(path)

        doc = await ProjectFileCollection.upsert(db, project_id, safe, payload.content)

        vol = _volume_path(project_id, safe)
        os.makedirs(os.path.dirname(vol), exist_ok=True)
        async with aiofiles.open(vol, "w", encoding="utf-8") as f:
            await f.write(payload.content)

        return _to_response(doc)

    @staticmethod
    async def delete_file(project_id: str, path: str, owner_id: str) -> None:
        db = get_database()
        await _assert_project_owner(db, project_id, owner_id)
        safe = _safe_path(path)

        deleted = await ProjectFileCollection.delete(db, project_id, safe)
        if not deleted:
            raise HTTPException(status_code=404, detail="File not found")

        vol = _volume_path(project_id, safe)
        if os.path.exists(vol):
            os.remove(vol)

    @staticmethod
    async def export_zip(project_id: str, owner_id: str) -> bytes:
        """Zip all project files from the host volume."""
        db = get_database()
        await _assert_project_owner(db, project_id, owner_id)
        project_dir = _project_dir(project_id)
        paths = _scan_volume(project_dir)

        buf = BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for rel in paths:
                abs_path = os.path.join(project_dir, rel)
                try:
                    async with aiofiles.open(abs_path, "rb") as f:
                        data = await f.read()
                    zf.writestr(rel, data)
                except OSError:
                    pass
        buf.seek(0)
        return buf.read()
