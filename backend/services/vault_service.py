"""Secrets vault business logic."""
import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from config import settings
from core.vault import encrypt_secret, decrypt_secret, CURRENT_KEY_VERSION
from schemas.vault import (
    ProviderType,
    VaultKeyCreate,
    VaultKeyListResponse,
    VaultKeyResponse,
    VaultValidateResponse,
)


class VaultService:

    @staticmethod
    async def list_secrets(user_id: str, db: Session) -> VaultKeyListResponse:
        if settings.DATABASE_TYPE == "mongo":
            from database.mongo import get_database
            from models.mongo_models import UserSecretCollection
            mongo_db = get_database()
            docs = await UserSecretCollection.find_by_user(mongo_db, user_id)
            return VaultKeyListResponse(secrets=[
                VaultKeyResponse(
                    id=str(d["_id"]),
                    provider=d["provider"],
                    label=d["label"],
                    created_at=d["created_at"],
                    updated_at=d.get("updated_at"),
                )
                for d in docs
            ])

        from models.sql_models import UserSecret
        rows = db.query(UserSecret).filter(
            UserSecret.user_id == int(user_id),
            UserSecret.is_deleted == False,
        ).all()
        return VaultKeyListResponse(secrets=[
            VaultKeyResponse(
                id=str(r.id),
                provider=r.provider,
                label=r.label,
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
            for r in rows
        ])


    @staticmethod
    async def upsert_secret(user_id: str, payload: VaultKeyCreate, db: Session) -> VaultKeyResponse:
        encrypted = encrypt_secret(user_id, payload.value)

        if settings.DATABASE_TYPE == "mongo":
            from database.mongo import get_database
            from models.mongo_models import UserSecretCollection
            mongo_db = get_database()
            doc = await UserSecretCollection.upsert(
                mongo_db, user_id, payload.provider.value,
                payload.label, encrypted, CURRENT_KEY_VERSION,
            )
            return VaultKeyResponse(
                id=str(doc["_id"]),
                provider=doc["provider"],
                label=doc["label"],
                created_at=doc["created_at"],
                updated_at=doc.get("updated_at"),
            )

        from models.sql_models import UserSecret
        row = db.query(UserSecret).filter(
            UserSecret.user_id == int(user_id),
            UserSecret.provider == payload.provider.value,
        ).first()

        if row:
            row.label = payload.label
            row.encrypted_value = encrypted
            row.key_version = CURRENT_KEY_VERSION
            row.is_deleted = False
        else:
            row = UserSecret(
                user_id=int(user_id),
                provider=payload.provider.value,
                label=payload.label,
                encrypted_value=encrypted,
                key_version=CURRENT_KEY_VERSION,
            )
            db.add(row)

        db.commit()
        db.refresh(row)
        return VaultKeyResponse(
            id=str(row.id),
            provider=row.provider,
            label=row.label,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )


    @staticmethod
    async def delete_secret(user_id: str, provider: str, db: Session) -> dict:
        if settings.DATABASE_TYPE == "mongo":
            from database.mongo import get_database
            from models.mongo_models import UserSecretCollection
            mongo_db = get_database()
            ok = await UserSecretCollection.soft_delete(mongo_db, user_id, provider)
            if not ok:
                raise HTTPException(status.HTTP_404_NOT_FOUND, f"No stored secret for provider '{provider}'")
            return {"message": f"Secret for '{provider}' removed"}

        from models.sql_models import UserSecret
        row = db.query(UserSecret).filter(
            UserSecret.user_id == int(user_id),
            UserSecret.provider == provider,
            UserSecret.is_deleted == False,
        ).first()
        if not row:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"No stored secret for provider '{provider}'")
        row.is_deleted = True
        db.commit()
        return {"message": f"Secret for '{provider}' removed"}


    @staticmethod
    async def get_decrypted_value(user_id: str, provider: str, db: Session) -> str:
        """Return the decrypted secret value. Raises 404 if not found."""
        if settings.DATABASE_TYPE == "mongo":
            from database.mongo import get_database
            from models.mongo_models import UserSecretCollection
            mongo_db = get_database()
            doc = await UserSecretCollection.find_by_provider(mongo_db, user_id, provider)
            if not doc:
                raise HTTPException(status.HTTP_404_NOT_FOUND, f"No stored secret for provider '{provider}'")
            return decrypt_secret(user_id, doc["encrypted_value"], doc.get("key_version", 1))

        from models.sql_models import UserSecret
        row = db.query(UserSecret).filter(
            UserSecret.user_id == int(user_id),
            UserSecret.provider == provider,
            UserSecret.is_deleted == False,
        ).first()
        if not row:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"No stored secret for provider '{provider}'")
        return decrypt_secret(user_id, row.encrypted_value, row.key_version)


    @staticmethod
    async def validate_secret(user_id: str, provider: ProviderType, db: Session) -> VaultValidateResponse:
        """Decrypt the stored key and test it against the provider's API."""
        value = await VaultService.get_decrypted_value(user_id, provider.value, db)

        validators = {
            ProviderType.anthropic: _validate_anthropic,
            ProviderType.openai: _validate_openai,
            ProviderType.ollama: _validate_local,
            ProviderType.lmstudio: _validate_local,
            ProviderType.obsidian_ai: _validate_obsidian_ai,
        }
        valid, message = await validators[provider](value)
        return VaultValidateResponse(provider=provider.value, valid=valid, message=message)


async def _validate_anthropic(api_key: str) -> tuple[bool, str]:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-haiku-4-5-20251001",
                    "max_tokens": 1,
                    "messages": [{"role": "user", "content": "hi"}],
                },
            )
        if r.status_code == 200:
            return True, "Anthropic API key is valid"
        if r.status_code == 401:
            return False, "Invalid Anthropic API key"
        return False, f"Anthropic returned unexpected status {r.status_code}"
    except httpx.ConnectError:
        return False, "Could not connect to Anthropic API"
    except Exception as e:
        return False, f"Validation error: {e}"


async def _validate_openai(api_key: str) -> tuple[bool, str]:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {api_key}"},
            )
        if r.status_code == 200:
            return True, "OpenAI API key is valid"
        if r.status_code == 401:
            return False, "Invalid OpenAI API key"
        return False, f"OpenAI returned unexpected status {r.status_code}"
    except httpx.ConnectError:
        return False, "Could not connect to OpenAI API"
    except Exception as e:
        return False, f"Validation error: {e}"


async def _validate_obsidian_ai(json_value: str) -> tuple[bool, str]:
    """For obsidian-ai: value is JSON {url, api_key, api_secret}. Ping /health."""
    import json as _json
    try:
        cfg = _json.loads(json_value)
        base_url = cfg.get("url", "").rstrip("/")
        api_key = cfg.get("api_key", "")
    except Exception:
        return False, "Invalid obsidian-ai config — expected JSON with url, api_key, api_secret"

    if not base_url:
        return False, "obsidian-ai base URL is not set"

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.get(f"{base_url}/health", headers={"X-API-Key": api_key})
        if r.status_code < 400:
            return True, f"Obsidian AI reachable at {base_url}"
        return False, f"Obsidian AI returned status {r.status_code}"
    except httpx.ConnectError:
        return False, f"Could not connect to Obsidian AI at {base_url}"
    except Exception as e:
        return False, f"Validation error: {e}"


async def _validate_local(base_url: str) -> tuple[bool, str]:
    """For Ollama/LMStudio: stored value is the base URL. Just ping it."""
    base_url = base_url.rstrip("/")
    for path in ["/v1/models", "/api/tags"]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(f"{base_url}{path}")
            if r.status_code == 200:
                return True, f"Server reachable at {base_url}"
        except Exception:
            continue
    return False, f"Could not reach server at {base_url}"
