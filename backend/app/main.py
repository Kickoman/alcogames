from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .config import settings
from .llm_settings import get_llm_settings
from .logging_setup import RequestLogMiddleware, get_logger, setup_logging
from .routers import admin, games, llm

setup_logging()
log = get_logger(stream="internal")

if not settings.ADMIN_TOKEN:
    raise RuntimeError(
        "ADMIN_TOKEN environment variable is not set. Refusing to start without "
        "an admin token configured (set it in your .env file)."
    )

app = FastAPI(title="Alcogames")
app.add_middleware(RequestLogMiddleware)

_llm = get_llm_settings()
log.info(
    "startup",
    provider=_llm.provider,
    llm_ready=_llm.ready(),
    llm_model=_llm.active_model(),
    data_dir=str(settings.DATA_DIR),
)

app.include_router(games.router)
app.include_router(admin.router)
app.include_router(llm.router)

# Mounted last: API routes above take precedence, everything else falls
# through to the static frontend (index.html served for "/").
app.mount("/", StaticFiles(directory=settings.FRONTEND_DIR, html=True), name="frontend")
