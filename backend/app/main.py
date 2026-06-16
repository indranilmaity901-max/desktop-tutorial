from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.admin.routes import router as admin_router
from app.agents.routes import router as agent_router
from app.auth.routes import router as auth_router
from app.config import get_settings
from app.database import apply_migrations, ping_database, verify_schema
from app.events.routes import router as events_router
from app.manager.routes import router as manager_router
from app.realtime.websocket import router as live_router
from app.services.seed import seed_from_environment


settings = get_settings()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("wpacs.v2")
app = FastAPI(title="WPACS V2 API", version="2.0.0")
startup_state = {
    "database": "not_checked",
    "migrations": [],
    "schema": {},
    "seeded": {},
}

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
    schema = startup_state.get("schema") or {}
    healthy = startup_state.get("database") == "ok" and not schema.get("missing_tables")
    return {
        "status": "ok" if healthy else "error",
        "database": startup_state.get("database"),
        "schema": schema,
    }


@app.on_event("startup")
def startup_check():
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is required")
    logger.info("Checking PostgreSQL connectivity")
    ping_database()
    startup_state["database"] = "ok"
    if settings.auto_migrate:
        logger.info("Applying database migrations")
        startup_state["migrations"] = apply_migrations()
    schema = verify_schema()
    startup_state["schema"] = schema
    if schema["missing_tables"]:
        raise RuntimeError(f"Missing required database tables: {', '.join(schema['missing_tables'])}")
    startup_state["seeded"] = seed_from_environment()
    logger.info("WPACS V2 startup complete")


app.include_router(auth_router)
app.include_router(agent_router)
app.include_router(manager_router)
app.include_router(admin_router)
app.include_router(events_router)
app.include_router(live_router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled API error on %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={"success": False, "data": {}, "message": "Internal server error", "errors": []},
    )
