import pytest

from au_sold_prices.api.config import Settings


def test_not_set_placeholder_becomes_empty(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "not-set")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_x")
    monkeypatch.setenv("CORS_ORIGINS", "https://a.example, https://b.example")
    settings = Settings.from_env()
    assert settings.stripe_secret_key == ""
    assert settings.stripe_webhook_secret == "whsec_x"
    assert settings.cors_origins == ["https://a.example", "https://b.example"]


def test_dev_auth_is_rejected_in_prod(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "prod")
    with pytest.raises(RuntimeError):
        Settings(auth_mode="dev").validate_for_production()
    Settings(auth_mode="entra").validate_for_production()
