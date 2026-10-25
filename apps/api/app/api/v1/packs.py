"""GET /v1/packs — pack picker (FR-GOAL-1). Everything shown comes from packs.config."""

from fastapi import APIRouter
from sqlalchemy import select

from app.core.auth import CurrentUser
from app.core.db import Engine, user_session
from app.domain.models import Pack
from app.domain.schemas import PackOut

router = APIRouter(tags=["packs"])


def pack_out(pack: Pack) -> PackOut:
    config = pack.config
    copy_text = dict(config.get("copy", {}))
    return PackOut(
        id=pack.id,
        name=pack.name,
        status=pack.status,
        sort_order=pack.sort_order,
        picker_label=copy_text.get("picker_label", pack.name),
        tagline=config.get("tagline"),
        duration_days=config.get("duration_days"),
        goal_schema=config.get("goal_schema"),
        stages=list(config.get("stages", [])),
        copy_text=copy_text,
    )


@router.get("/packs", response_model=list[PackOut])
async def list_packs(user: CurrentUser, engine: Engine) -> list[PackOut]:
    async with user_session(engine, user) as session:
        packs = await session.scalars(
            select(Pack).where(Pack.status != "retired").order_by(Pack.sort_order, Pack.id)
        )
        return [pack_out(p) for p in packs]
