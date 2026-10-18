"""Bearer-token verification: a dev mode for local work and Microsoft Entra External ID."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Principal:
    subject: str
    email: str | None
    name: str | None


class AuthError(Exception):
    pass


class TokenVerifier(Protocol):
    def verify(self, token: str) -> Principal: ...


class DevVerifier:
    """Accepts `dev:<email>` tokens. Never use outside local development."""

    def verify(self, token: str) -> Principal:
        if not token.startswith("dev:") or len(token) <= 4:
            raise AuthError("invalid dev token")
        email = token[4:].strip().lower()
        return Principal(subject=f"dev|{email}", email=email, name=email.split("@")[0])


class EntraVerifier:
    """Validates access tokens issued by a Microsoft Entra External ID (CIAM) tenant."""

    def __init__(self, tenant_id: str, tenant_subdomain: str, audience: str, jwks_client=None):
        import jwt

        self._jwt = jwt
        self._audience = audience
        self._issuer = f"https://{tenant_id}.ciamlogin.com/{tenant_id}/v2.0"
        jwks_url = f"https://{tenant_subdomain}.ciamlogin.com/{tenant_id}/discovery/v2.0/keys"
        self._jwks = jwks_client or jwt.PyJWKClient(jwks_url, cache_keys=True)

    def verify(self, token: str) -> Principal:
        try:
            key = self._jwks.get_signing_key_from_jwt(token).key
            claims = self._jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                audience=self._audience,
                issuer=self._issuer,
                options={"require": ["exp", "iss", "aud", "sub"]},
            )
        except self._jwt.PyJWTError as exc:
            raise AuthError(str(exc)) from exc
        email = claims.get("email") or claims.get("preferred_username")
        return Principal(subject=claims["sub"], email=email, name=claims.get("name"))
