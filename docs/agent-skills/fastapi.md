# FastAPI Skill — Obsidian WebDev Agent

You are working on a **FastAPI project** inside `/workspace`. Follow these rules exactly.

---

## Environment

- Python **3.12+** — use modern syntax (`X | None`, `match`, etc.)
- FastAPI **0.100+** — check `pyproject.toml` to confirm version
- Pydantic **v2** — NOT v1. Validators, models, and config syntax differ significantly
- SQLAlchemy **2.0** — mapped_column, Mapped[], declarative ORM only
- Package manager: **uv** only (`uv add <pkg>`, `uv sync`) — **never use pip directly**
- Dev server already running via tmux — **never run uvicorn manually again**
- Port: **8000** inside container

---

## File structure rules

```
/workspace
  main.py                  ← FastAPI app entry, lifespan, middleware, router registration
  config.py                ← Settings via pydantic-settings (BaseSettings)
  routers/                 ← One file per resource (auth.py, users.py, items.py)
  services/                ← Business logic — no HTTP concerns here
  models/                  ← SQLAlchemy ORM models
  schemas/                 ← Pydantic request/response schemas
  database/                ← DB engine, session factory, migrations
  migrations/              ← Alembic migration files (versions/)
  core/                    ← Cross-cutting: security, rate limiter, utilities
```

- Routers handle HTTP only — call services for logic
- Services call models/DB — no FastAPI imports in services
- Schemas are the only thing crossing the HTTP boundary
- Never put raw SQL in routers

---

## FastAPI patterns

### App entry + lifespan
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    yield
    # shutdown

app = FastAPI(lifespan=lifespan)
```

### Router
```python
# routers/items.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database.sql import get_db
from schemas.items import ItemCreate, ItemResponse
from services.item_service import ItemService

router = APIRouter(prefix="/items", tags=["items"])

@router.get("/", response_model=list[ItemResponse])
async def list_items(db: Session = Depends(get_db)):
    return await ItemService.list_all(db)

@router.post("/", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
async def create_item(payload: ItemCreate, db: Session = Depends(get_db)):
    return await ItemService.create(payload, db)

@router.get("/{item_id}", response_model=ItemResponse)
async def get_item(item_id: int, db: Session = Depends(get_db)):
    item = await ItemService.get_by_id(item_id, db)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return item
```

### Pydantic v2 schemas
```python
# schemas/items.py
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, field_validator

class ItemCreate(BaseModel):
    name: str
    description: Optional[str] = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("name must not be empty")
        return v.strip()

class ItemResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}
```

### SQLAlchemy v2 models
```python
# models/sql_models.py
from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from database.sql import Base

class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
```

### Settings (pydantic-settings v2)
```python
# config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./app.db"
    SECRET_KEY: str = "changeme"

    model_config = {"env_file": ".env", "extra": "ignore"}

settings = Settings()
```

### Async service pattern
```python
# services/item_service.py
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from models.sql_models import Item
from schemas.items import ItemCreate

class ItemService:
    @staticmethod
    async def list_all(db: Session) -> list[Item]:
        return db.query(Item).all()

    @staticmethod
    async def create(payload: ItemCreate, db: Session) -> Item:
        row = Item(name=payload.name, description=payload.description)
        db.add(row)
        db.commit()
        db.refresh(row)
        return row

    @staticmethod
    async def get_by_id(item_id: int, db: Session) -> Item | None:
        return db.query(Item).filter(Item.id == item_id).first()
```

---

## Dependency management

```bash
uv add fastapi sqlalchemy pydantic-settings   # add packages
uv sync                                        # install from pyproject.toml
uv run python -c "import pkg"                 # verify install
```

Never use `pip install`. Never modify `requirements.txt` — use `pyproject.toml`.

---

## Alembic migrations

When you add or change a model:
```bash
uv run alembic revision --autogenerate -m "add_items_table"
uv run alembic upgrade head
```

Always check the generated migration file in `migrations/versions/` before applying — autogenerate is not always correct.

---

## What NOT to do

- Never use `pip install` — use `uv add`
- Never use Pydantic v1 syntax (`validator`, `class Config`) — use v2 (`field_validator`, `model_config`)
- Never use SQLAlchemy 1.x patterns (`Column`, `relationship` without `Mapped`) — use v2 `Mapped[type]`
- Never put business logic in routers — it goes in services
- Never import FastAPI types into service files
- Never run `uvicorn` manually — dev server is already running
- Never use `async with Session` if you're using sync SQLAlchemy — be consistent (check existing code)
- Never use `@validator` — use `@field_validator` with `@classmethod`

---

## Verifying changes

```bash
uv run python -c "from main import app; print('OK')"   # import check
# Check logs in tmux:
bash -c "tmux capture-pane -p -t 0 2>/dev/null | tail -20"
```

---

## Context7 — ALWAYS fetch docs before writing code

Use `web_fetch` to get current FastAPI, SQLAlchemy, and Pydantic documentation.

### FastAPI docs via Context7

```
GET https://context7.com/api/v1/tiangolo/fastapi/docs?tokens=8000&topic=<TOPIC>
```

| What you are building | Topic |
|---|---|
| New router / endpoint | `routing-bigger-applications` |
| Request body / schemas | `request-body` |
| Query params / path params | `query-params-path-params` |
| Dependency injection | `dependencies-depends` |
| Authentication / JWT | `security-oauth2-jwt` |
| Background tasks | `background-tasks` |
| Middleware | `middleware` |
| File upload | `request-files` |
| WebSockets | `websockets` |
| Testing | `testing` |
| Lifespan events | `lifespan-events` |

**Call example:**
```
web_fetch("https://context7.com/api/v1/tiangolo/fastapi/docs?tokens=8000&topic=dependencies-depends")
```

### SQLAlchemy v2 docs via Context7

```
GET https://context7.com/api/v1/sqlalchemy/sqlalchemy/docs?tokens=7000&topic=<TOPIC>
```

| What you need | Topic |
|---|---|
| ORM models setup | `orm-declarative-mapping` |
| Querying (select, filter) | `orm-querying-select` |
| Relationships | `orm-relationships` |
| Async SQLAlchemy | `orm-asyncio` |
| Migrations with Alembic | `alembic-migrations` |

### Pydantic v2 docs via Context7

```
GET https://context7.com/api/v1/pydantic/pydantic/docs?tokens=6000&topic=<TOPIC>
```

Topics: `models`, `validators`, `settings-management`, `serialization`, `computed-fields`, `model-config`

---

## Git integration

SSH key is pre-injected:
```bash
git status
git add -A && git commit -m "feat: add items endpoint"
git push origin main
```
