"""Unit tests for the dedicated credential table and the legacy migration."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from travel_planner.db.models import Base, User, UserCredential
from travel_planner.services import auth


async def _session() -> async_sessionmaker:  # type: ignore[type-arg]
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return async_sessionmaker(engine, expire_on_commit=False)


async def test_register_writes_the_credential_table_not_preferences() -> None:
    maker = await _session()
    async with maker() as session:
        user = await auth.register_user(
            session, email="New@Example.com", password="correct-horse-battery"
        )
        await session.commit()

        # The hash lives in the dedicated credential row.
        cred = (
            await session.execute(
                select(UserCredential).where(UserCredential.user_id == user.id)
            )
        ).scalars().one()
        assert auth.verify_password("correct-horse-battery", cred.password_hash)

        # The preferences payload carries no credential material.
        assert "password" not in (user.preferences or {})


async def test_authenticate_uses_the_credential_table() -> None:
    maker = await _session()
    async with maker() as session:
        await auth.register_user(
            session, email="a@example.com", password="correct-horse-battery"
        )
        await session.commit()

    async with maker() as session:
        user = await auth.authenticate_user(
            session, email="a@example.com", password="correct-horse-battery"
        )
        assert user.email == "a@example.com"


async def test_legacy_preferences_hash_is_lazily_migrated() -> None:
    """A phase 6 account (hash in the preferences JSON) still logs in."""
    maker = await _session()
    async with maker() as session:
        session.add(
            User(
                email="legacy@example.com",
                preferences={"password": auth.hash_password("correct-horse-battery")},
            )
        )
        await session.commit()

    async with maker() as session:
        user = await auth.authenticate_user(
            session, email="legacy@example.com", password="correct-horse-battery"
        )
        await session.commit()

        # Migrated: the credential row exists, the legacy copy is gone.
        cred = (
            await session.execute(
                select(UserCredential).where(UserCredential.user_id == user.id)
            )
        ).scalars().one()
        assert auth.verify_password("correct-horse-battery", cred.password_hash)
        assert "password" not in (user.preferences or {})


async def test_legacy_hash_with_wrong_password_is_rejected() -> None:
    maker = await _session()
    async with maker() as session:
        session.add(
            User(
                email="legacy2@example.com",
                preferences={"password": auth.hash_password("correct-horse-battery")},
            )
        )
        await session.commit()

    async with maker() as session:
        try:
            await auth.authenticate_user(
                session, email="legacy2@example.com", password="nope-wrong"
            )
        except auth.AuthError:
            pass
        else:
            raise AssertionError("wrong password must raise AuthError")
