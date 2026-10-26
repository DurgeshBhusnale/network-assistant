"""Database tasks against the configured DATABASE_URL (the cloud dev project, ADR-0009).

    uv run python -m app.dbtasks push   # apply new migrations (supabase db push), then the seed
    uv run python -m app.dbtasks seed   # regenerate supabase/seed.sql and apply it (idempotent)

Never resets the database. Migrations are forward-only.
"""

import argparse
import asyncio
import shutil
import subprocess
import sys

import asyncpg

from app.core.config import REPO_ROOT, get_settings
from app.db_seed import SEED_PATH, render_seed


def _libpq_url() -> str:
    """DATABASE_URL without the SQLAlchemy driver suffix, for the Supabase CLI and asyncpg."""
    return get_settings().database_url.replace("postgresql+asyncpg://", "postgresql://", 1)


def push_migrations() -> None:
    supabase = shutil.which("supabase")
    if supabase is None:
        raise SystemExit("Supabase CLI not found on PATH (see docs/DEV-SETUP.md)")
    subprocess.run(  # noqa: S603 - fixed argv, no shell
        [supabase, "db", "push", "--db-url", _libpq_url(), "--workdir", str(REPO_ROOT)],
        check=True,
    )


async def apply_seed() -> None:
    sql = render_seed()
    SEED_PATH.write_bytes(sql.encode("utf-8"))
    conn = await asyncpg.connect(_libpq_url())
    try:
        await conn.execute(sql)
    finally:
        await conn.close()
    print("seed applied")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task", choices=["push", "seed"])
    args = parser.parse_args(argv)
    if args.task == "push":
        push_migrations()
    asyncio.run(apply_seed())
    return 0


if __name__ == "__main__":
    sys.exit(main())
