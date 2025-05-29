from fastapi import APIRouter

from app.api.endpoints import ingest, query

router = APIRouter()
router.include_router(ingest.router)
router.include_router(query.router)
