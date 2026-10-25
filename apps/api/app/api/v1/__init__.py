from fastapi import APIRouter

from app.api.v1 import (
    admin,
    billing,
    captures,
    contacts,
    drafts,
    goals,
    health,
    imports,
    loop,
    me,
    notifications,
    packs,
    privacy,
    whatsapp,
)

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
router.include_router(captures.router)
router.include_router(whatsapp.router)
router.include_router(billing.router)
router.include_router(notifications.router)
router.include_router(admin.router)
