import logging

import sentry_sdk

from app.core.config import settings

logger = logging.getLogger("app.monitoring")


def init_sentry() -> None:
    """Real sentry-sdk integration. Safe by default: with no SENTRY_DSN
    configured, this is a complete no-op — sentry_sdk.init() is never
    called, so nothing is sent anywhere, no network call is made, and no
    account is required to run this project. Set SENTRY_DSN in .env (a
    real Sentry project's DSN, free tier is fine) to turn it on."""
    if not settings.SENTRY_DSN:
        logger.info("SENTRY_DSN not configured — error monitoring is disabled")
        return

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENV,
        traces_sample_rate=0.1,
        send_default_pii=False,  # never send user emails/IPs by default
    )
    logger.info("Sentry error monitoring enabled for environment=%s", settings.ENV)
