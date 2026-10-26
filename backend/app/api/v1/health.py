from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    """Checks both dependencies this app cannot run without: Postgres (the
    source of truth for everything) and Redis (queue/cache for Celery —
    see app/core/config.py's note that Redis must never become a second
    source of truth, only Postgres is). A degraded Redis still reports here
    even though most read endpoints would keep working, because background
    jobs (imports, publishing, future Celery tasks) would silently stop."""
    db_ok = True
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_ok = False

    redis_ok = True
    try:
        redis_client = Redis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        await redis_client.ping()
        await redis_client.aclose()
    except Exception:
        redis_ok = False

    return {
        "status": "ok" if (db_ok and redis_ok) else "degraded",
        "database": db_ok,
        "redis": redis_ok,
    }
