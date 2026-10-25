import json
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncConnection

from tests.integration.conftest import CreateUser, act_as, scalar

EXPECTED_TABLES = {
    "ai_calls", "audit_log", "calendar_events", "captures", "consents", "contacts", "drafts",
    "entitlements", "events", "goal_contacts", "goals", "imports", "interactions", "memories",
    "packs", "payments", "profiles", "push_subscriptions", "style_profiles", "suggestions",
    "triggers", "wa_link_codes", "wa_messages",
}  # fmt: skip


async def test_every_public_table_has_rls(conn: AsyncConnection) -> None:
    rows = await conn.execute(
        text(
            "select c.relname, c.relrowsecurity from pg_class c "
            "join pg_namespace n on n.oid = c.relnamespace "
            "where n.nspname = 'public' and c.relkind in ('r', 'p')"
        )
    )
    tables = {name: rls for name, rls in rows.all()}

    assert set(tables) == EXPECTED_TABLES
    assert [name for name, rls in tables.items() if not rls] == []


async def test_anon_has_no_table_privileges(conn: AsyncConnection) -> None:
    rows = await conn.execute(
        text(
            "select c.relname from pg_class c join pg_namespace n on n.oid = c.relnamespace "
            "where n.nspname = 'public' and c.relkind in ('r', 'p') and has_table_privilege("
            "'anon', c.oid, 'select, insert, update, delete, truncate, references, trigger')"
        )
    )
    assert rows.scalars().all() == []


async def test_seed_loads_four_packs_and_calendar(
    conn: AsyncConnection, career_sprint_config: dict[str, Any]
) -> None:
    packs = (await conn.execute(text("select id, status from packs order by sort_order"))).all()
    config = await scalar(conn, "select config from packs where id = 'career_sprint'")

    assert [tuple(p) for p in packs] == [
        ("career_sprint", "active"),
        ("freelance_clients", "coming_soon"),
        ("fundraising", "coming_soon"),
        ("partners_hires_vendors", "coming_soon"),
    ]
    assert config == career_sprint_config
    assert await scalar(conn, "select count(*) from calendar_events") >= 2


async def test_authenticated_can_edit_own_profile_only(
    conn: AsyncConnection, create_user: CreateUser
) -> None:
    me, other = await create_user(), await create_user()
    await act_as(conn, me)

    mine = await conn.execute(
        text("update profiles set display_name = 'Rohan' where user_id = :id"), {"id": me}
    )
    theirs = await conn.execute(
        text("update profiles set display_name = 'X' where user_id = :id"), {"id": other}
    )

    assert mine.rowcount == 1
    assert theirs.rowcount == 0


@pytest.mark.parametrize(
    "column",
    ["wa_phone_e164", "wa_opt_in_at", "wa_opt_out_at", "wa_last_inbound_at", "price_cohort", "utm"],
)
async def test_authenticated_cannot_write_server_managed_profile_columns(
    conn: AsyncConnection, create_user: CreateUser, column: str
) -> None:
    me = await create_user()
    await act_as(conn, me)

    with pytest.raises(DBAPIError, match="permission denied"):
        async with conn.begin_nested():
            await conn.execute(
                text(f"update profiles set {column} = null where user_id = :id"),  # noqa: S608
                {"id": me},
            )


async def test_second_pack_vocabulary_is_accepted_by_the_db(
    conn: AsyncConnection, create_user: CreateUser, freelance_test_config: dict[str, Any]
) -> None:
    """ADR-0008: nothing in the schema is specific to Career Sprint."""
    user = await create_user()
    await conn.execute(
        text("insert into packs (id, name, status, config) values (:id, :name, 'active', :cfg)"),
        {
            "id": freelance_test_config["id"],
            "name": freelance_test_config["name"],
            "cfg": json.dumps(freelance_test_config),
        },
    )
    goal = await scalar(
        conn,
        "insert into goals (user_id, pack_id, starts_on) values (:u, 'freelance_test', "
        "'2026-10-25') returning id",
        u=user,
    )
    contact = await scalar(
        conn,
        "insert into contacts (user_id, full_name) values (:u, 'Test Client') returning id",
        u=user,
    )
    params = {"u": user, "g": goal, "c": contact}
    await conn.execute(
        text(
            "insert into goal_contacts (goal_id, contact_id, user_id, state, outcome) "
            "values (:g, :c, :u, 'won', 'client_won')"
        ),
        params,
    )
    await conn.execute(
        text(
            "insert into suggestions (user_id, goal_id, contact_id, for_date, score, stage) "
            "values (:u, :g, :c, '2026-10-26', 0.8, 'pitch')"
        ),
        params,
    )
    await conn.execute(
        text(
            "insert into interactions (user_id, contact_id, goal_id, type, outcome) "
            "values (:u, :c, :g, 'outcome', 'client_won')"
        ),
        params,
    )
    await conn.execute(
        text(
            "insert into interactions (user_id, contact_id, goal_id, type, stage) "
            "values (:u, :c, :g, 'sent', 'pitch')"
        ),
        params,
    )


@pytest.mark.parametrize(
    "sql",
    [
        "insert into interactions (user_id, contact_id, type) values (:u, :c, 'referred')",
        "insert into interactions (user_id, contact_id, type) values (:u, :c, 'outcome')",
        "insert into interactions (user_id, contact_id, type, outcome) "
        "values (:u, :c, 'sent', 'referred')",
    ],
)
async def test_db_enforces_generic_interaction_types(
    conn: AsyncConnection, create_user: CreateUser, sql: str
) -> None:
    user = await create_user()
    contact = await scalar(
        conn, "insert into contacts (user_id, full_name) values (:u, 'A') returning id", u=user
    )

    with pytest.raises(DBAPIError, match="check"):
        async with conn.begin_nested():
            await conn.execute(text(sql), {"u": user, "c": contact})


async def test_goal_contact_state_is_generic(
    conn: AsyncConnection, create_user: CreateUser
) -> None:
    user = await create_user()
    goal = await scalar(
        conn,
        "insert into goals (user_id, pack_id, starts_on) values (:u, 'career_sprint', "
        "'2026-10-25') returning id",
        u=user,
    )
    contact = await scalar(
        conn, "insert into contacts (user_id, full_name) values (:u, 'A') returning id", u=user
    )

    with pytest.raises(DBAPIError, match="check"):
        async with conn.begin_nested():
            await conn.execute(
                text(
                    "insert into goal_contacts (goal_id, contact_id, user_id, state) "
                    "values (:g, :c, :u, 'referred')"
                ),
                {"g": goal, "c": contact, "u": user},
            )


async def test_goal_start_date_has_no_db_default(
    conn: AsyncConnection, create_user: CreateUser
) -> None:
    user = await create_user()

    with pytest.raises(DBAPIError, match="starts_on"):
        async with conn.begin_nested():
            await conn.execute(
                text("insert into goals (user_id, pack_id) values (:u, 'career_sprint')"),
                {"u": user},
            )


async def test_payments_survive_account_deletion(
    conn: AsyncConnection, create_user: CreateUser
) -> None:
    user = await create_user()
    payment = await scalar(
        conn,
        "insert into payments (user_id, product, amount_paise) values (:u, 'sprint', 79900) "
        "returning id",
        u=user,
    )

    await conn.execute(text("delete from auth.users where id = :u"), {"u": user})

    owner = await scalar(conn, "select user_id from payments where id = :p", p=payment)
    assert owner is None
    assert await scalar(conn, "select count(*) from profiles where user_id = :u", u=user) == 0
