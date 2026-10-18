import os
from dataclasses import dataclass, field


def _split(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    database_url: str = ""
    auth_mode: str = "dev"  # "dev" accepts "dev:<email>" tokens; "entra" verifies real JWTs
    entra_tenant_id: str = ""
    entra_tenant_subdomain: str = ""
    entra_api_audience: str = ""
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_monthly: str = ""
    stripe_price_annual: str = ""
    app_base_url: str = "http://localhost:3000"
    cors_origins: list[str] = field(default_factory=lambda: ["http://localhost:3000"])
    search_limit_max: int = 10

    @classmethod
    def from_env(cls) -> "Settings":
        def env(name: str, default: str = "") -> str:
            value = os.environ.get(name, default)
            return "" if value == "not-set" else value  # placeholder written by the Bicep secrets

        return cls(
            database_url=env("DATABASE_URL"),
            auth_mode=env("AUTH_MODE", "dev"),
            entra_tenant_id=env("ENTRA_TENANT_ID"),
            entra_tenant_subdomain=env("ENTRA_TENANT_SUBDOMAIN"),
            entra_api_audience=env("ENTRA_API_AUDIENCE"),
            stripe_secret_key=env("STRIPE_SECRET_KEY"),
            stripe_webhook_secret=env("STRIPE_WEBHOOK_SECRET"),
            stripe_price_monthly=env("STRIPE_PRICE_MONTHLY"),
            stripe_price_annual=env("STRIPE_PRICE_ANNUAL"),
            app_base_url=env("APP_BASE_URL", "http://localhost:3000"),
            cors_origins=_split(env("CORS_ORIGINS", "http://localhost:3000")),
        )

    def validate_for_production(self) -> None:
        if self.auth_mode == "dev" and os.environ.get("ENVIRONMENT", "dev") == "prod":
            raise RuntimeError("AUTH_MODE=dev is not allowed when ENVIRONMENT=prod")
