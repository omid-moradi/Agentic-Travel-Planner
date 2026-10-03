"""Auth endpoints: register, login, me. Optional bearer auth elsewhere."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from travel_planner.api.app import error_response
from travel_planner.api.routers.trips import db_session
from travel_planner.db.models import User
from travel_planner.services import auth

router = APIRouter(tags=["auth"])

_bearer = HTTPBearer(auto_error=False)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(default="", max_length=120)
    locale: str = Field(default="fa", pattern="^(fa|en)$")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str | None
    is_admin: bool


async def current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(db_session),
) -> User | None:
    """The caller's user, or None for an anonymous (guest) caller."""
    if credentials is None:
        return None
    try:
        user_id = auth.decode_access_token(credentials.credentials)
    except auth.AuthError:
        return None
    return await auth.get_user(session, user_id)


@router.post("/auth/register", status_code=201)
async def register(
    body: RegisterRequest,
    request: Request,
    session: AsyncSession = Depends(db_session),
) -> object:
    try:
        user = await auth.register_user(
            session,
            email=body.email,
            password=body.password,
            display_name=body.display_name,
            locale=body.locale,
        )
    except auth.AuthError as exc:
        return error_response(409, "email_taken", str(exc), request.state.request_id)
    token = auth.create_access_token(str(user.id))
    await session.commit()
    return AuthResponse(
        access_token=token,
        user_id=str(user.id),
        email=user.email,
        is_admin=user.is_admin,
    )


@router.post("/auth/login")
async def login(
    body: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(db_session),
) -> object:
    try:
        user = await auth.authenticate_user(session, email=body.email, password=body.password)
    except auth.AuthError as exc:
        return error_response(401, "invalid_credentials", str(exc), request.state.request_id)
    token = auth.create_access_token(str(user.id))
    return AuthResponse(
        access_token=token,
        user_id=str(user.id),
        email=user.email,
        is_admin=user.is_admin,
    )


@router.get("/auth/me")
async def me(
    request: Request,
    user: User | None = Depends(current_user),
) -> object:
    if user is None:
        return error_response(
            401, "unauthenticated", "Provide a bearer token or stay a guest.", request.state.request_id
        )
    return {
        "user_id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
        "is_admin": user.is_admin,
    }
