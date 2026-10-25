from fastapi import APIRouter

from app.api.v1 import contacts, drafts, goals, health, imports, loop, me, packs, privacy

router = APIRouter(prefix="/v1")
router.include_router(health.router)
router.include_router(me.router)
router.include_router(packs.router)
router.include_router(goals.router)
router.include_router(privacy.router)
router.include_router(contacts.router)
router.include_router(imports.router)
router.include_router(drafts.router)
router.include_router(loop.router)
