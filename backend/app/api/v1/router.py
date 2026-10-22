from fastapi import APIRouter

from app.api.v1.assets import router as assets_router
from app.api.v1.auth import router as auth_router
from app.api.v1.health import router as health_router
from app.api.v1.imports import router as imports_router
from app.api.v1.collection_jobs import router as collection_jobs_router
from app.api.v1.ai_config import (
    models_router as ai_models_router,
    policies_router as ai_policies_router,
    providers_router as ai_providers_router,
    usage_router as ai_usage_router,
)
from app.api.v1.products import router as products_router
from app.api.v1.publications import router as publications_router
from app.api.v1.reviews import router as reviews_router
from app.api.v1.site_products import router as site_products_router
from app.api.v1.sites import router as sites_router
from app.api.v1.suppliers import router as suppliers_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(products_router)
api_router.include_router(assets_router)
api_router.include_router(imports_router)
api_router.include_router(sites_router)
api_router.include_router(site_products_router)
api_router.include_router(publications_router)
api_router.include_router(suppliers_router)
api_router.include_router(collection_jobs_router)
api_router.include_router(ai_providers_router)
api_router.include_router(ai_models_router)
api_router.include_router(ai_policies_router)
api_router.include_router(ai_usage_router)
api_router.include_router(reviews_router)

# Phase 6+ will add: collection-jobs execution (per-supplier scrapers),
# image-processing-jobs, jobs (unified task monitor), team/members,
# audit-logs query endpoints.
