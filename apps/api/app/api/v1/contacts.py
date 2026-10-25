"""People and memories (FR-CON-4/8/9, FR-PER-*, FR-MEM-1)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Query, Response
from sqlalchemy import select

from app.api.v1.deps import ClockDep
from app.core.auth import CurrentUser
from app.core.db import Engine, user_session
from app.core.errors import AppError, ErrorCode
from app.domain.models import Contact, Memory
from app.domain.schemas import (
    ContactCreate,
    ContactList,
    ContactSummary,
    ContactUpdate,
    MemoryCreate,
    MemoryOut,
    PersonOut,
)
from app.imports.normalise import clean_text, split_name
from app.services import contacts as svc

router = APIRouter(tags=["people"])


@router.get("/contacts", response_model=ContactList)
async def list_contacts(
    user: CurrentUser,
    engine: Engine,
    q: Annotated[str | None, Query(max_length=100)] = None,
    cursor: Annotated[str | None, Query(max_length=500)] = None,
) -> ContactList:
    async with user_session(engine, user) as session:
        return await svc.list_contacts(session, user.id, q, cursor)


@router.post("/contacts", response_model=ContactSummary, status_code=201)
async def create_contact(body: ContactCreate, user: CurrentUser, engine: Engine) -> ContactSummary:
    name = split_name(body.full_name)
    if name is None:
        raise AppError(ErrorCode.VALIDATION_ERROR, "Check this field: full_name", 422)
    phones = svc.normalised_phones([body.phone] if body.phone else [])
    emails = svc.normalised_emails([body.email] if body.email else [])
    linkedin = svc.normalised_linkedin(body.linkedin_url)
    async with user_session(engine, user) as session:
        existing = await svc.find_duplicate(session, user.id, phones, emails, linkedin)
        if existing is not None:
            raise svc.duplicate_error(existing)
        company = clean_text(body.company)
        contact = Contact(
            user_id=user.id,
            full_name=name[0],
            first_name=name[1],
            last_name=name[2],
            phones=phones,
            emails=emails,
            linkedin_url=linkedin,
            company=company,
            company_norm=svc.company_norm(company),
            title=clean_text(body.title),
            city=clean_text(body.city),
            how_known=clean_text(body.how_known),
            birthday=body.birthday,
            sources=["manual"],
        )
        session.add(contact)
        await session.flush()
        await session.refresh(contact)
        return svc.summary(contact)


@router.get("/contacts/{contact_id}", response_model=PersonOut)
async def get_person(contact_id: uuid.UUID, user: CurrentUser, engine: Engine) -> PersonOut:
    async with user_session(engine, user) as session:
        return await svc.person(session, user.id, contact_id)


@router.patch("/contacts/{contact_id}", response_model=PersonOut)
async def update_contact(
    contact_id: uuid.UUID, body: ContactUpdate, user: CurrentUser, engine: Engine
) -> PersonOut:
    changes = body.model_dump(exclude_unset=True)
    async with user_session(engine, user) as session:
        contact = await svc.get_contact(session, user.id, contact_id)
        if "full_name" in changes:
            name = split_name(changes["full_name"])
            if name is None:
                raise AppError(ErrorCode.VALIDATION_ERROR, "Check this field: full_name", 422)
            contact.full_name, contact.first_name, contact.last_name = name
        phones = svc.normalised_phones(changes["phones"] or []) if "phones" in changes else None
        emails = svc.normalised_emails(changes["emails"] or []) if "emails" in changes else None
        linkedin = (
            svc.normalised_linkedin(changes["linkedin_url"]) if "linkedin_url" in changes else None
        )
        duplicate = await svc.find_duplicate(
            session, user.id, phones or [], emails or [], linkedin, exclude=contact.id
        )
        if duplicate is not None:
            raise svc.duplicate_error(duplicate)
        if phones is not None:
            contact.phones = phones
        if emails is not None:
            contact.emails = emails
        if "linkedin_url" in changes:
            contact.linkedin_url = linkedin
        if "company" in changes:
            contact.company = clean_text(changes["company"])
            contact.company_norm = svc.company_norm(contact.company)
        for field in ("title", "city", "how_known"):
            if field in changes:
                setattr(contact, field, clean_text(changes[field]))
        if "birthday" in changes:
            contact.birthday = changes["birthday"]
        await session.flush()
        return await svc.person(session, user.id, contact.id)


@router.delete("/contacts/{contact_id}", status_code=204)
async def delete_contact(
    contact_id: uuid.UUID, user: CurrentUser, engine: Engine, clock: ClockDep
) -> Response:
    async with user_session(engine, user) as session:
        await svc.delete_contact(session, user.id, contact_id, clock.now())
    return Response(status_code=204)


@router.post("/contacts/{contact_id}/memories", response_model=MemoryOut, status_code=201)
async def add_memory(
    contact_id: uuid.UUID, body: MemoryCreate, user: CurrentUser, engine: Engine
) -> MemoryOut:
    text = body.text.strip()
    if not text:
        raise AppError(ErrorCode.VALIDATION_ERROR, "Check this field: text", 422)
    async with user_session(engine, user) as session:
        contact = await svc.get_contact(session, user.id, contact_id)
        memory = Memory(user_id=user.id, contact_id=contact.id, text=text, source="note")
        session.add(memory)
        await session.flush()
        await session.refresh(memory)
        return MemoryOut(
            id=memory.id, text=memory.text, source="note", created_at=memory.created_at
        )


@router.delete("/memories/{memory_id}", status_code=204)
async def delete_memory(memory_id: uuid.UUID, user: CurrentUser, engine: Engine) -> Response:
    async with user_session(engine, user) as session:
        memory = await session.scalar(
            select(Memory).where(Memory.id == memory_id, Memory.user_id == user.id)
        )
        if memory is None:
            raise AppError(ErrorCode.NOT_FOUND, "Note not found.", 404)
        await session.delete(memory)
    return Response(status_code=204)
