"""JWT auth, password hashing, and FastAPI security dependencies."""
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config import settings
from database.sql import get_db


class TokenData(BaseModel):
    user_id: str
    username: str
    role: str
    token_type: str = "user"


class APIClientData(BaseModel):
    client_id: str
    client_name: str
    token_type: str = "api_client"


bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
api_secret_header = APIKeyHeader(name="X-API-Secret", auto_error=False)


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def generate_client_credentials() -> tuple[str, str]:
    client_id = f"cli_{secrets.token_hex(16)}"
    client_secret = secrets.token_hex(32)
    return client_id, client_secret


def hash_client_secret(secret: str) -> str:
    return bcrypt.hashpw(secret.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_client_secret(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def _decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> TokenData:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = _decode_token(credentials.credentials)
    if payload.get("token_type") != "user":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type for this endpoint",
        )
    return TokenData(
        user_id=payload["user_id"],
        username=payload["username"],
        role=payload.get("role", "guest"),
        token_type="user",
    )


async def _get_api_client(
    request: Request,
    api_key: Optional[str],
    api_secret: Optional[str],
    db: Session,
) -> APIClientData:
    if not api_key or not api_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API credentials required (X-API-Key and X-API-Secret headers)",
        )

    if settings.DATABASE_TYPE == "mongo":
        from database.mongo import get_database
        from models.mongo_models import APIClientCollection
        mongo_db = get_database()
        client = await APIClientCollection.find_by_client_id(mongo_db, api_key)
        if not client:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API credentials")
        hashed_secret = client["hashed_secret"]
        client_name = client["name"]
        client_id = client["client_id"]
        is_active = client.get("is_active", True)
    else:
        from models.sql_models import APIClient
        client = db.query(APIClient).filter(
            APIClient.client_id == api_key,
            APIClient.is_active == True,
        ).first()
        if not client:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API credentials")
        hashed_secret = client.hashed_secret
        client_name = client.name
        client_id = client.client_id
        is_active = client.is_active

    if not is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API client is disabled")
    if not verify_client_secret(api_secret, hashed_secret):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API credentials")

    return APIClientData(client_id=client_id, client_name=client_name)


async def get_current_user_or_api_client(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    api_key: Optional[str] = Depends(api_key_header),
    api_secret: Optional[str] = Depends(api_secret_header),
    db: Session = Depends(get_db),
) -> TokenData | APIClientData:
    if credentials:
        try:
            return await get_current_user(credentials)
        except HTTPException:
            pass
    if api_key and api_secret:
        try:
            return await _get_api_client(request, api_key, api_secret, db)
        except HTTPException:
            pass
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Provide a Bearer token or X-API-Key / X-API-Secret headers.",
    )
