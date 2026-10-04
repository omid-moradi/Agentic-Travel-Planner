"""Authentication: email accounts, JWT access tokens, roles.

Deliberate choices for this phase:

* **PBKDF2** (stdlib) for password hashing - no native dependency, 240k
  iterations, per-user salt. Argon2/bcrypt can replace it behind the same
  function later.
* **JWT HS256** via PyJWT with an expiry claim; the secret comes from env.
* **Guest trial**: without an account the caller is anonymous and gets one
  free plan (the master prompt's guest trial).
* The bootstrap admin is the first account created with ``ADMIN_BOOTSTRAP_EMAIL``
  - a pragmatic escape hatch before an invite flow exists.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from travel_planner.config.settings import Settings, get_settings
from travel_planner.db.models import User, UserCredential

logger = logging.getLogger(__name__)

_PBKDF2_ITERATIONS = 240_000


class AuthError(Exception):
    """Raised for every authentication or authorization failure."""


# ----------------------------------------------------------------- passwords
def hash_password(password: str) -> str:
    """PBKDF2-SHA256 with a random 16-byte salt, encoded as ``salt$hash``."""
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), _PBKDF2_ITERATIONS
    ).hex()
    return f"{salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    """Constant-time comparison of a candidate password against the stored form."""
    try:
        salt, expected = stored.split("$", 1)
    except ValueError:
        return False
    candidate = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), _PBKDF2_ITERATIONS
    ).hex()
    return secrets.compare_digest(candidate, expected)


# ---------------------------------------------------------------------- jwt
def create_access_token(user_id: str, *, settings: Settings | None = None) -> str:
    cfg = settings or get_settings()
    now = datetime.now(UTC)
    claims = {
        "sub": user_id,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=cfg.access_token_expiry_minutes)).timestamp()),
    }
    return jwt.encode(claims, cfg.jwt_secret.get_secret_value(), algorithm=cfg.jwt_algorithm)


def decode_access_token(token: str, *, settings: Settings | None = None) -> str:
    """Return the user id from a valid, unexpired token or raise AuthError."""
    cfg = settings or get_settings()
    try:
        claims: dict[str, Any] = jwt.decode(
            token, cfg.jwt_secret.get_secret_value(), algorithms=[cfg.jwt_algorithm]
        )
    except jwt.PyJWTError as exc:
        msg = "invalid or expired token"
        raise AuthError(msg) from exc
    subject = claims.get("sub")
    if not isinstance(subject, str):
        msg = "token missing subject"
        raise AuthError(msg)
    return subject


# ------------------------------------------------------------------ accounts
async def register_user(
    session: AsyncSession,
    *,
    email: str,
    password: str,
    display_name: str = "",
    locale: str = "fa",
) -> User:
    """Create an account. The bootstrap admin email grants the admin role."""
    cfg = get_settings()
    normalised = email.strip().lower()
    existing = await session.execute(select(User).where(User.email == normalised))
    if existing.scalars().first() is not None:
        msg = "an account with this email already exists"
        raise AuthError(msg)

    is_admin = bool(cfg.admin_bootstrap_email) and normalised == cfg.admin_bootstrap_email.lower()
    user = User(
        email=normalised,
        display_name=display_name or normalised.split("@")[0],
        locale=locale,
        is_admin=is_admin,
    )
    session.add(user)
    await session.flush()
    # The hash goes to the dedicated credential table - never into the
    # preferences JSON (which is treated as display-safe data).
    session.add(UserCredential(user_id=user.id, password_hash=hash_password(password)))
    await session.flush()
    if is_admin:
        logger.info("bootstrap admin created for %s", normalised)
    return user


async def authenticate_user(
    session: AsyncSession, *, email: str, password: str
) -> User:
    normalised = email.strip().lower()
    result = await session.execute(select(User).where(User.email == normalised))
    user = result.scalars().first()
    if user is None:
        msg = "invalid email or password"
        raise AuthError(msg)

    cred_result = await session.execute(
        select(UserCredential).where(UserCredential.user_id == user.id)
    )
    credential = cred_result.scalars().first()
    if credential is not None:
        if not verify_password(password, credential.password_hash):
            msg = "invalid email or password"
            raise AuthError(msg)
        return user

    # Legacy fallback: hashes written to the preferences JSON by the phase 6
    # code. Verified read-only, then lazily migrated to the credential table
    # so the legacy copy disappears from the payload.
    legacy_stored = str(user.preferences.get("password", ""))
    if legacy_stored and verify_password(password, legacy_stored):
        session.add(UserCredential(user_id=user.id, password_hash=legacy_stored))
        user.preferences = {k: v for k, v in user.preferences.items() if k != "password"}
        await session.flush()
        return user

    msg = "invalid email or password"
    raise AuthError(msg)


async def get_user(session: AsyncSession, user_id: str) -> User | None:
    try:
        parsed = uuid.UUID(user_id)
    except ValueError:
        return None
    return await session.get(User, parsed)


async def require_admin(session: AsyncSession, user_id: str) -> User:
    """Return the user and raise unless they carry the admin role."""
    user = await get_user(session, user_id)
    if user is None:
        msg = "account not found"
        raise AuthError(msg)
    if not user.is_admin:
        msg = "admin role required"
        raise AuthError(msg)
    return user
