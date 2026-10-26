"""Supabase JWT verification. Asymmetric keys via the project JWKS; HS256 secret as fallback."""

import uuid
from functools import lru_cache
from typing import Annotated, Any

import anyio
import jwt
from fastapi import Depends, Request
from pydantic import BaseModel

from app.core.config import Settings, get_settings
from app.core.errors import AppError, ErrorCode

AUDIENCE = "authenticated"
# Supabase's clock can run a little ahead of ours; without leeway a just-issued token fails
# the `iat` check on the first request after sign-in.
LEEWAY_SECONDS = 30


class AuthUser(BaseModel):
    id: uuid.UUID
    email: str | None
    claims: dict[str, Any]


def _unauthenticated(message: str = "Sign in to continue.") -> AppError:
    return AppError(ErrorCode.UNAUTHENTICATED, message, status_code=401)


@lru_cache
def _jwks_client(url: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(url, cache_keys=True, lifespan=3600)


def jwks_url(settings: Settings) -> str:
    return settings.supabase_jwks_url or f"{settings.supabase_url}/auth/v1/.well-known/jwks.json"


async def decode_token(token: str, settings: Settings) -> dict[str, Any]:
    try:
        header = jwt.get_unverified_header(token)
        alg = header.get("alg", "")
        if alg == "HS256":
            if settings.supabase_jwt_secret is None:
                raise _unauthenticated()
            key: Any = settings.supabase_jwt_secret.get_secret_value()
        else:
            client = _jwks_client(jwks_url(settings))
            signing_key = await anyio.to_thread.run_sync(client.get_signing_key_from_jwt, token)
            key = signing_key.key
        claims: dict[str, Any] = jwt.decode(
            token,
            key,
            algorithms=["ES256", "RS256", "HS256"],
            audience=AUDIENCE,
            leeway=LEEWAY_SECONDS,
        )
    except jwt.ExpiredSignatureError as exc:
        raise _unauthenticated("Your session has expired. Sign in again.") from exc
    except (jwt.PyJWTError, ValueError) as exc:
        raise _unauthenticated() from exc
    if claims.get("role") != AUDIENCE or "sub" not in claims:
        raise _unauthenticated()
    return claims


async def get_current_user(request: Request) -> AuthUser:
    settings: Settings = getattr(request.app.state, "settings", None) or get_settings()
    header = request.headers.get("authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise _unauthenticated()
    claims = await decode_token(token, settings)
    user = AuthUser(id=uuid.UUID(claims["sub"]), email=claims.get("email"), claims=claims)
    from app.core.ratelimit import general_limit  # local import: ratelimit depends on this module

    await general_limit(request, user)
    return user


CurrentUser = Annotated[AuthUser, Depends(get_current_user)]
