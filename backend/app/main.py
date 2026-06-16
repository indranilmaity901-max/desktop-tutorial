from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.admin.routes import router as admin_router
from app.agents.routes import router as agent_router
from app.auth.routes import router as auth_router
from app.config import get_settings
from app.events.routes import router as events_router
from app.manager.routes import router as manager_router
from app.realtime.websocket import router as live_router


settings = get_settings()
app = FastAPI(title="WPACS V2 API", version="2.0.0")

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.get("/api/v1/health")
@app.get("/api/v2/health")
def health():
    return {"status": "ok", "database": "configured" if settings.database_url else "not_configured"}


app.include_router(auth_router)
app.include_router(agent_router)
app.include_router(manager_router)
app.include_router(admin_router)
app.include_router(events_router)
app.include_router(live_router)
