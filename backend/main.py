import asyncio
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded

from config import settings
from core.rate_limiter import limiter, rate_limit_exceeded_handler
from routers import agent as agent_router
from routers import auth as auth_router
from routers import containers as containers_router
from routers import projects as projects_router
from routers import workspace as workspace_router
from routers import settings as settings_router
from routers import vault as vault_router
from websocket import agent_ws, terminal_ws


@asynccontextmanager
async def lifespan(app: FastAPI):
    from database.mongo import close_mongo_connection, connect_to_mongo, get_database
    from models.mongo_models import (
        AgentMessageCollection,
        AgentSessionCollection,
        APIClientCollection,
        ProjectCollection,
        ProjectConversationCollection,
        ProjectExportCollection,
        ProjectFileCollection,
        ProjectFileSummaryCollection,
        UserCollection,
        UserPreferencesCollection,
        UserSecretCollection,
    )

    if settings.DATABASE_TYPE == "sqlite":
        from database.sql import Base, engine
        Base.metadata.create_all(bind=engine)

    await connect_to_mongo()
    db = get_database()

    if settings.DATABASE_TYPE == "mongo":
        await UserCollection.create_indexes(db)
        await APIClientCollection.create_indexes(db)
        await UserSecretCollection.create_indexes(db)

    await UserPreferencesCollection.create_indexes(db)
    await ProjectCollection.create_indexes(db)
    await ProjectFileCollection.create_indexes(db)
    await ProjectFileSummaryCollection.create_indexes(db)
    await ProjectConversationCollection.create_indexes(db)
    await AgentSessionCollection.create_indexes(db)
    await AgentMessageCollection.create_indexes(db)
    await ProjectExportCollection.create_indexes(db)

    from services.container_service import container_cleanup_task
    cleanup_task = asyncio.create_task(container_cleanup_task())
    app.state.cleanup_task = cleanup_task

    yield

    cleanup_task.cancel()
    await close_mongo_connection()


app = FastAPI(
    title="Obsidian WebDev",
    description="AI-powered platform builder API",
    version="0.1.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(vault_router.router)
app.include_router(projects_router.router)
app.include_router(containers_router.router)
app.include_router(workspace_router.router)
app.include_router(settings_router.router)
app.include_router(agent_router.router)

app.include_router(agent_ws.router)
app.include_router(terminal_ws.router)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8100, reload=True)
