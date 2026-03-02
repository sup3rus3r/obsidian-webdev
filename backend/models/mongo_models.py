"""MongoDB collection helpers.

Each class exposes only classmethods that operate on a Motor database handle.
No Pydantic models here — callers work with plain dicts (Motor returns dicts).
"""
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId


class UserCollection:
    collection_name = "users"

    @classmethod
    async def create_indexes(cls, db) -> None:
        col = db[cls.collection_name]
        await col.create_index("username", unique=True)
        await col.create_index("email", unique=True)

    @classmethod
    async def find_by_username(cls, db, username: str) -> Optional[dict]:
        return await db[cls.collection_name].find_one({"username": username})

    @classmethod
    async def find_by_email(cls, db, email: str) -> Optional[dict]:
        return await db[cls.collection_name].find_one({"email": email})

    @classmethod
    async def find_by_id(cls, db, user_id: str) -> Optional[dict]:
        return await db[cls.collection_name].find_one({"_id": ObjectId(user_id)})

    @classmethod
    async def create(cls, db, user_data: dict) -> dict:
        col = db[cls.collection_name]
        result = await col.insert_one(user_data)
        user_data["_id"] = result.inserted_id
        return user_data

    @classmethod
    async def update_role(cls, db, user_id: str, new_role: str) -> Optional[dict]:
        return await db[cls.collection_name].find_one_and_update(
            {"_id": ObjectId(user_id)},
            {"$set": {"role": new_role}},
            return_document=True,
        )


class APIClientCollection:
    collection_name = "api_clients"

    @classmethod
    async def create_indexes(cls, db) -> None:
        await db[cls.collection_name].create_index("client_id", unique=True)

    @classmethod
    async def find_by_client_id(cls, db, client_id: str) -> Optional[dict]:
        return await db[cls.collection_name].find_one(
            {"client_id": client_id, "is_active": True}
        )

    @classmethod
    async def find_by_user(cls, db, user_id: str) -> list[dict]:
        cursor = db[cls.collection_name].find({"created_by": user_id})
        return await cursor.to_list(length=100)

    @classmethod
    async def create(cls, db, client_data: dict) -> dict:
        col = db[cls.collection_name]
        result = await col.insert_one(client_data)
        client_data["_id"] = result.inserted_id
        return client_data

    @classmethod
    async def deactivate(cls, db, client_id: str, user_id: str) -> bool:
        result = await db[cls.collection_name].update_one(
            {"client_id": client_id, "created_by": user_id},
            {"$set": {"is_active": False}},
        )
        return result.modified_count > 0


class ProjectCollection:
    """AI-built projects (MongoDB-only, regardless of DATABASE_TYPE)."""

    collection_name = "projects"

    @classmethod
    async def create_indexes(cls, db) -> None:
        col = db[cls.collection_name]
        await col.create_index("owner_id")
        await col.create_index([("owner_id", 1), ("name", 1)], unique=True)

    @classmethod
    async def find_by_owner(cls, db, owner_id: str) -> list[dict]:
        cursor = db[cls.collection_name].find({"owner_id": owner_id})
        return await cursor.to_list(length=100)

    @classmethod
    async def find_by_id(cls, db, project_id: str) -> Optional[dict]:
        return await db[cls.collection_name].find_one({"_id": ObjectId(project_id)})

    @classmethod
    async def create(cls, db, project_data: dict) -> dict:
        col = db[cls.collection_name]
        result = await col.insert_one(project_data)
        project_data["_id"] = result.inserted_id
        return project_data

    @classmethod
    async def update(cls, db, project_id: str, update_data: dict) -> Optional[dict]:
        return await db[cls.collection_name].find_one_and_update(
            {"_id": ObjectId(project_id)},
            {"$set": update_data},
            return_document=True,
        )

    @classmethod
    async def delete(cls, db, project_id: str) -> bool:
        result = await db[cls.collection_name].delete_one({"_id": ObjectId(project_id)})
        return result.deleted_count > 0


class ProjectFileCollection:
    """Source-of-truth file store for AI-generated project files.

    Files are dual-written here (MongoDB) AND to the container volume mount.
    MongoDB is the canonical version; the container volume is the working copy.
    """

    collection_name = "project_files"

    @classmethod
    async def create_indexes(cls, db) -> None:
        col = db[cls.collection_name]
        await col.create_index("project_id")
        await col.create_index([("project_id", 1), ("path", 1)], unique=True)

    @classmethod
    async def find_by_project(cls, db, project_id: str) -> list[dict]:
        cursor = db[cls.collection_name].find({"project_id": project_id})
        return await cursor.to_list(length=1000)

    @classmethod
    async def find_by_path(cls, db, project_id: str, path: str) -> Optional[dict]:
        return await db[cls.collection_name].find_one(
            {"project_id": project_id, "path": path}
        )

    @classmethod
    async def upsert(
        cls,
        db,
        project_id: str,
        path: str,
        content: str,
        metadata: Optional[dict] = None,
    ) -> dict:
        """Create or replace a file. `path` must be POSIX-style (forward slashes)."""
        now = datetime.now(timezone.utc)
        doc = {
            "project_id": project_id,
            "path": path,
            "content": content,
            "updated_at": now,
            **(metadata or {}),
        }
        return await db[cls.collection_name].find_one_and_update(
            {"project_id": project_id, "path": path},
            {"$set": doc, "$setOnInsert": {"created_at": now}},
            upsert=True,
            return_document=True,
        )

    @classmethod
    async def delete(cls, db, project_id: str, path: str) -> bool:
        result = await db[cls.collection_name].delete_one(
            {"project_id": project_id, "path": path}
        )
        return result.deleted_count > 0

    @classmethod
    async def count_by_project(cls, db, project_id: str) -> int:
        return await db[cls.collection_name].count_documents({"project_id": project_id})

    @classmethod
    async def delete_all(cls, db, project_id: str) -> int:
        result = await db[cls.collection_name].delete_many({"project_id": project_id})
        return result.deleted_count


class UserSecretCollection:
    """Fernet-encrypted user API keys. One active secret per (user_id, provider)."""

    collection_name = "user_secrets"

    @classmethod
    async def create_indexes(cls, db) -> None:
        col = db[cls.collection_name]
        await col.create_index("user_id")
        await col.create_index(
            [("user_id", 1), ("provider", 1)],
            unique=True,
            partialFilterExpression={"is_deleted": False},
        )

    @classmethod
    async def find_by_user(cls, db, user_id: str) -> list[dict]:
        cursor = db[cls.collection_name].find({"user_id": user_id, "is_deleted": False})
        return await cursor.to_list(length=100)

    @classmethod
    async def find_by_provider(cls, db, user_id: str, provider: str) -> Optional[dict]:
        return await db[cls.collection_name].find_one(
            {"user_id": user_id, "provider": provider, "is_deleted": False}
        )

    @classmethod
    async def upsert(cls, db, user_id: str, provider: str, label: str, encrypted_value: str, key_version: int = 1) -> dict:
        now = datetime.now(timezone.utc)
        return await db[cls.collection_name].find_one_and_update(
            {"user_id": user_id, "provider": provider},
            {
                "$set": {
                    "label": label,
                    "encrypted_value": encrypted_value,
                    "key_version": key_version,
                    "is_deleted": False,
                    "updated_at": now,
                },
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
            return_document=True,
        )

    @classmethod
    async def soft_delete(cls, db, user_id: str, provider: str) -> bool:
        result = await db[cls.collection_name].update_one(
            {"user_id": user_id, "provider": provider, "is_deleted": False},
            {"$set": {"is_deleted": True, "updated_at": datetime.now(timezone.utc)}},
        )
        return result.modified_count > 0


class AgentSessionCollection:
    """Agent build sessions. One session per active WebSocket connection."""

    collection_name = "agent_sessions"

    @classmethod
    async def create_indexes(cls, db) -> None:
        col = db[cls.collection_name]
        await col.create_index("project_id")
        await col.create_index("user_id")
        await col.create_index("thread_id", unique=True, sparse=True)

    @classmethod
    async def create(cls, db, session_data: dict) -> dict:
        col = db[cls.collection_name]
        result = await col.insert_one(session_data)
        session_data["_id"] = result.inserted_id
        return session_data

    @classmethod
    async def find_by_id(cls, db, session_id: str) -> Optional[dict]:
        return await db[cls.collection_name].find_one({"_id": ObjectId(session_id)})

    @classmethod
    async def find_by_project(cls, db, project_id: str, limit: int = 20) -> list[dict]:
        cursor = db[cls.collection_name].find(
            {"project_id": project_id}
        ).sort("created_at", -1).limit(limit)
        return await cursor.to_list(length=limit)

    @classmethod
    async def find_active(cls, db, project_id: str) -> Optional[dict]:
        return await db[cls.collection_name].find_one(
            {"project_id": project_id, "status": {"$in": ["running", "paused"]}}
        )

    @classmethod
    async def update_status(cls, db, session_id: str, status: str, extra: Optional[dict] = None) -> Optional[dict]:
        update = {"$set": {"status": status, "updated_at": datetime.now(timezone.utc), **(extra or {})}}
        return await db[cls.collection_name].find_one_and_update(
            {"_id": ObjectId(session_id)},
            update,
            return_document=True,
        )


class AgentMessageCollection:
    """Per-session agent event log — used to reconstruct chat history and replay builds."""

    collection_name = "agent_messages"

    @classmethod
    async def create_indexes(cls, db) -> None:
        col = db[cls.collection_name]
        await col.create_index("session_id")
        await col.create_index([("session_id", 1), ("timestamp", 1)])

    @classmethod
    async def append(cls, db, session_id: str, msg_type: str, content: dict, agent_name: Optional[str] = None) -> dict:
        doc = {
            "session_id": session_id,
            "type": msg_type,
            "agent_name": agent_name,
            "content": content,
            "timestamp": datetime.now(timezone.utc),
        }
        col = db[cls.collection_name]
        result = await col.insert_one(doc)
        doc["_id"] = result.inserted_id
        return doc

    @classmethod
    async def find_by_session(cls, db, session_id: str, limit: int = 200) -> list[dict]:
        cursor = db[cls.collection_name].find(
            {"session_id": session_id}
        ).sort("timestamp", 1).limit(limit)
        return await cursor.to_list(length=limit)

    @classmethod
    async def delete_by_session(cls, db, session_id: str) -> int:
        result = await db[cls.collection_name].delete_many({"session_id": session_id})
        return result.deleted_count


class UserPreferencesCollection:
    """Per-user agent behaviour preferences."""

    collection_name = "user_preferences"

    DEFAULTS: dict = {
        "permission_mode":   "ask",
        "compact_threshold": 0.80,
        "max_bash_lines":    400,
        "max_file_lines":    500,
        "max_web_chars":     20_000,
    }

    @classmethod
    async def create_indexes(cls, db) -> None:
        await db[cls.collection_name].create_index([("user_id", 1)], unique=True)

    @classmethod
    async def get_or_default(cls, db, user_id: str) -> dict:
        doc = await db[cls.collection_name].find_one({"user_id": user_id})
        prefs = {**cls.DEFAULTS}
        if doc:
            for k in cls.DEFAULTS:
                if k in doc:
                    prefs[k] = doc[k]
        return prefs

    @classmethod
    async def upsert(cls, db, user_id: str, prefs: dict) -> None:
        await db[cls.collection_name].update_one(
            {"user_id": user_id},
            {"$set": {**prefs, "user_id": user_id}},
            upsert=True,
        )


class ProjectConversationCollection:
    """Persists the LLM message history and chat display messages per project.

    One document per project — upserted after every agent turn so that
    conversation context survives WebSocket reconnects and backend restarts.
    """

    collection_name = "project_conversations"

    @classmethod
    async def create_indexes(cls, db) -> None:
        await db[cls.collection_name].create_index("project_id", unique=True)

    @classmethod
    async def upsert(cls, db, project_id: str, messages: list, display: list) -> None:
        now = datetime.now(timezone.utc)
        await db[cls.collection_name].update_one(
            {"project_id": project_id},
            {"$set": {"messages": messages, "display": display, "updated_at": now}},
            upsert=True,
        )

    @classmethod
    async def find_by_project(cls, db, project_id: str) -> Optional[dict]:
        return await db[cls.collection_name].find_one({"project_id": project_id})

    @classmethod
    async def clear(cls, db, project_id: str) -> None:
        await db[cls.collection_name].delete_one({"project_id": project_id})


class ProjectFileSummaryCollection:
    """One-line AI-generated summaries per file, updated after each write.

    Used by the agent's list_files_brief tool so it can understand the codebase
    structure without opening every file.
    """

    collection_name = "project_file_summaries"

    @classmethod
    async def create_indexes(cls, db) -> None:
        col = db[cls.collection_name]
        await col.create_index([("project_id", 1), ("path", 1)], unique=True)

    @classmethod
    async def upsert(cls, db, project_id: str, path: str, summary: str) -> None:
        now = datetime.now(timezone.utc)
        await db[cls.collection_name].update_one(
            {"project_id": project_id, "path": path},
            {"$set": {"summary": summary, "updated_at": now}},
            upsert=True,
        )

    @classmethod
    async def find_by_project(cls, db, project_id: str) -> list[dict]:
        cursor = db[cls.collection_name].find({"project_id": project_id})
        return await cursor.to_list(length=1000)

    @classmethod
    async def delete_by_project(cls, db, project_id: str) -> int:
        result = await db[cls.collection_name].delete_many({"project_id": project_id})
        return result.deleted_count


class ProjectExportCollection:
    """Snapshots of exported project zips (stored in GridFS)."""

    collection_name = "project_exports"

    @classmethod
    async def create_indexes(cls, db) -> None:
        col = db[cls.collection_name]
        await col.create_index("project_id")

    @classmethod
    async def create(cls, db, export_data: dict) -> dict:
        col = db[cls.collection_name]
        result = await col.insert_one(export_data)
        export_data["_id"] = result.inserted_id
        return export_data

    @classmethod
    async def find_by_project(cls, db, project_id: str) -> list[dict]:
        cursor = db[cls.collection_name].find(
            {"project_id": project_id}
        ).sort("created_at", -1)
        return await cursor.to_list(length=20)
