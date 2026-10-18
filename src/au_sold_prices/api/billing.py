"""Stripe integration behind a small interface so the API can be tested without the network."""

from typing import Any, Protocol


class BillingGateway(Protocol):
    def create_customer(self, email: str | None, name: str | None, user_id: str) -> str: ...

    def checkout_url(
        self, customer_id: str, price_id: str, success_url: str, cancel_url: str
    ) -> str: ...

    def portal_url(self, customer_id: str, return_url: str) -> str: ...

    def parse_event(self, payload: bytes, signature: str) -> dict[str, Any]: ...


class StripeGateway:
    def __init__(self, secret_key: str, webhook_secret: str) -> None:
        import stripe

        self._stripe = stripe
        self._client = stripe.StripeClient(secret_key)
        self._webhook_secret = webhook_secret

    def create_customer(self, email: str | None, name: str | None, user_id: str) -> str:
        params: dict[str, Any] = {"metadata": {"user_id": user_id}}
        if email:
            params["email"] = email
        if name:
            params["name"] = name
        return self._client.customers.create(params=params).id

    def checkout_url(
        self, customer_id: str, price_id: str, success_url: str, cancel_url: str
    ) -> str:
        session = self._client.checkout.sessions.create(
            params={
                "mode": "subscription",
                "customer": customer_id,
                "line_items": [{"price": price_id, "quantity": 1}],
                "success_url": success_url,
                "cancel_url": cancel_url,
                "allow_promotion_codes": True,
                "automatic_tax": {"enabled": True},
                "customer_update": {"address": "auto"},
            }
        )
        return session.url

    def portal_url(self, customer_id: str, return_url: str) -> str:
        session = self._client.billing_portal.sessions.create(
            params={"customer": customer_id, "return_url": return_url}
        )
        return session.url

    def parse_event(self, payload: bytes, signature: str) -> dict[str, Any]:
        event = self._stripe.Webhook.construct_event(payload, signature, self._webhook_secret)
        return event.to_dict() if hasattr(event, "to_dict") else dict(event)
