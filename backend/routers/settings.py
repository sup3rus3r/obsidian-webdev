"""User settings router — agent preferences."""
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from core.rate_limiter import limiter, user_limit
from core.security import TokenData, get_current_user
from database.mongo import get_database

router = APIRouter(prefix="/settings", tags=["settings"])


class PreferencesUpdate(BaseModel):
    permission_mode:   Literal["ask", "auto"] | None = None
    compact_threshold: Annotated[float | None, Field(ge=0.50, le=0.95)] = None
    max_bash_lines:    Annotated[int | None,   Field(ge=50, le=2000)]  = None
    max_file_lines:    Annotated[int | None,   Field(ge=50, le=2000)]  = None
    max_web_chars:     Annotated[int | None,   Field(ge=5000, le=100_000)] = None


@router.get("/preferences")
@limiter.limit(user_limit())
async def get_preferences(
    request: Request,
    current_user: TokenData = Depends(get_current_user),
):
    from models.mongo_models import UserPreferencesCollection
    db = get_database()
    return await UserPreferencesCollection.get_or_default(db, current_user.user_id)


@router.put("/preferences")
@limiter.limit(user_limit())
async def update_preferences(
    payload: PreferencesUpdate,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
):
    from models.mongo_models import UserPreferencesCollection
    db = get_database()
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    if updates:
        await UserPreferencesCollection.upsert(db, current_user.user_id, updates)
    return await UserPreferencesCollection.get_or_default(db, current_user.user_id)
