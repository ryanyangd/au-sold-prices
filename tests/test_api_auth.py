import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from au_sold_prices.api.auth import AuthError, DevVerifier, EntraVerifier

TENANT = "11111111-2222-3333-4444-555555555555"
AUDIENCE = "api-client-id"
ISSUER = f"https://{TENANT}.ciamlogin.com/{TENANT}/v2.0"


class FakeSigningKey:
    def __init__(self, key):
        self.key = key


class FakeJwks:
    def __init__(self, public_key):
        self._key = FakeSigningKey(public_key)

    def get_signing_key_from_jwt(self, token):
        return self._key


@pytest.fixture(scope="module")
def keypair():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture
def verifier(keypair):
    return EntraVerifier(TENANT, "contoso", AUDIENCE, jwks_client=FakeJwks(keypair.public_key()))


def token(keypair, **over):
    claims = {
        "iss": ISSUER, "aud": AUDIENCE, "sub": "user-123", "exp": int(time.time()) + 600,
        "email": "a@example.com", "name": "Alex",
    }  # fmt: skip
    claims.update(over)
    return jwt.encode({k: v for k, v in claims.items() if v is not None}, keypair, algorithm="RS256")


def test_valid_token(verifier, keypair):
    principal = verifier.verify(token(keypair))
    assert (principal.subject, principal.email, principal.name) == (
        "user-123", "a@example.com", "Alex",
    )  # fmt: skip


def test_email_falls_back_to_preferred_username(verifier, keypair):
    principal = verifier.verify(token(keypair, email=None, preferred_username="p@example.com"))
    assert principal.email == "p@example.com"


@pytest.mark.parametrize(
    "over",
    [
        {"aud": "someone-else"},
        {"iss": "https://evil.example/v2.0"},
        {"exp": int(time.time()) - 10},
        {"sub": None},
    ],
)
def test_rejects_bad_claims(verifier, keypair, over):
    with pytest.raises(AuthError):
        verifier.verify(token(keypair, **over))


def test_rejects_token_signed_with_other_key(verifier):
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    with pytest.raises(AuthError):
        verifier.verify(token(other))


def test_rejects_garbage(verifier):
    with pytest.raises(AuthError):
        verifier.verify("not-a-jwt")


def test_dev_verifier():
    principal = DevVerifier().verify("dev:Pat@Example.com")
    assert principal.email == "pat@example.com" and principal.subject == "dev|pat@example.com"
    for bad in ("dev:", "Bearer x", "abc"):
        with pytest.raises(AuthError):
            DevVerifier().verify(bad)
