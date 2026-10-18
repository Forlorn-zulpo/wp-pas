from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.health import router as health_router
from app.api.v1.products import router as products_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(products_router)

# Phase 3+ will add: assets upload, imports, suppliers, collection-jobs,
# ai/providers, ai/models, ai/task-policies, image-processing-jobs, reviews,
# sites, site-products, publication-previews, publications, jobs,
# team/members, audit-logs query endpoints.
