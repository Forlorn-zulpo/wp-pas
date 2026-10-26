from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

import app.models  # noqa: F401  (registers every mapped model before first use)
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging_config import configure_logging
from app.core.monitoring import init_sentry

configure_logging()
init_sentry()

app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)
app.include_router(api_router)

# Exposes GET /metrics in Prometheus text format: request counts, latency
# histograms per route, in-progress requests. Works with zero external
# accounts — point any local Prometheus instance's scrape config at this
# path and it works immediately; no API key, no SaaS signup.
Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)


@app.get("/")
async def root():
    return {"service": settings.APP_NAME, "env": settings.ENV}
