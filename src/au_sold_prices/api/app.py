import logging
from datetime import datetime, timezone
from typing import Annotated, Any, Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from psycopg import OperationalError
from psycopg_pool import PoolTimeout
from pydantic import BaseModel

from au_sold_prices.api.auth import AuthError, Principal, TokenVerifier
from au_sold_prices.api.billing import BillingGateway
from au_sold_prices.api.config import Settings
from au_sold_prices.api.db import Repository, UserRecord

log = logging.getLogger("api")

FREE_LOCKED_SECTIONS = ["sales_history", "trend", "distribution", "comparables"]
SUBSCRIPTION_EVENTS = {
    "customer.subscription.created",
    "customer.subscription.updated",
    "customer.subscription.deleted",
}


class CheckoutRequest(BaseModel):
    plan: Literal["pro_monthly", "pro_annual"]


def _round(value: Any, digits: int = 1) -> float | None:
    return None if value is None else round(float(value), digits)


def _int(value: Any) -> int | None:
    return None if value is None else round(float(value))


def _period_end(subscription: dict[str, Any]) -> datetime | None:
    stamp = subscription.get("current_period_end")
    if stamp is None:  # newer Stripe API versions put it on the subscription item
        items = (subscription.get("items") or {}).get("data") or []
        stamp = items[0].get("current_period_end") if items else None
    return datetime.fromtimestamp(stamp, tz=timezone.utc) if stamp else None


def create_app(
    settings: Settings,
    repo: Repository,
    verifier: TokenVerifier,
    billing: BillingGateway | None = None,
) -> FastAPI:
    app = FastAPI(title="AusSold API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type"],
    )

    def optional_principal(authorization: Annotated[str | None, Header()] = None):
        if not authorization:
            return None
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise HTTPException(401, "Invalid authorization header")
        try:
            return verifier.verify(token)
        except AuthError as exc:
            raise HTTPException(401, "Invalid or expired token") from exc

    def required_principal(
        principal: Annotated[Principal | None, Depends(optional_principal)],
    ) -> Principal:
        if principal is None:
            raise HTTPException(401, "Sign in required")
        return principal

    def current_user(principal: Annotated[Principal, Depends(required_principal)]) -> UserRecord:
        return repo.upsert_user(principal.subject, principal.email, principal.name)

    def plan_for(principal: Principal | None) -> str:
        if principal is None:
            return "free"
        return repo.upsert_user(principal.subject, principal.email, principal.name).plan

    @app.exception_handler(PoolTimeout)
    @app.exception_handler(OperationalError)
    async def database_unavailable(request: Request, exc: Exception) -> JSONResponse:
        log.error("database unavailable: %s", exc)
        return JSONResponse({"detail": "Service temporarily unavailable"}, status_code=503)

    # async so liveness never queues behind blocked database calls in the thread pool
    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/ready")
    def ready() -> dict[str, str]:
        if not repo.ping():
            raise HTTPException(503, "Database unavailable")
        return {"status": "ok"}

    @app.get("/search/addresses")
    def search_addresses(
        q: Annotated[str, Query(min_length=1, max_length=100)],
        limit: Annotated[int, Query(ge=1)] = 8,
    ) -> dict[str, Any]:
        rows = repo.search_addresses(q, min(limit, settings.search_limit_max))
        return {
            "results": [
                {
                    "property_id": r["property_key"],
                    "address": r["address_display"],
                    "suburb": r["suburb"],
                    "postcode": r["postcode"],
                    "state": r["state"],
                    "property_type": r["property_type"],
                    "display": f"{r['address_display']}, {r['suburb']} {r['state']} "
                    f"{r['postcode'] or ''}".strip(),
                    "last_sale_price": r["last_sale_price"],
                    "last_sale_date": r["last_sale_date"],
                }
                for r in rows
            ]
        }

    @app.get("/properties/{property_id}")
    def get_property(
        property_id: str,
        principal: Annotated[Principal | None, Depends(optional_principal)],
    ) -> dict[str, Any]:
        prop = repo.get_property(property_id)
        as_of = repo.data_as_of()
        if prop is None or as_of is None:
            raise HTTPException(404, "Property not found")
        pro = plan_for(principal) == "pro"
        suburb, state, ptype = prop["suburb"], prop["state"], prop["property_type"]
        stats = repo.get_suburb_stats(suburb, state, ptype) or {}

        sales = trend = distribution = comparables = None
        if pro:
            sales = [
                {
                    "contract_date": s["sale_date"],
                    "settlement_date": s["settlement_date"],
                    "price": s["price"],
                    "change_pct": _round(s["change_pct"]),
                    "years_held": _round(s["years_held"], 2),
                }
                for s in repo.get_sales(property_id)
            ]
            trend = [
                {
                    "month": t["month"].strftime("%Y-%m"),
                    "median": _int(t["median_price"]),
                    "sales_count": t["sales_count"],
                }
                for t in repo.get_trend(suburb, state, ptype)
            ]
            distribution = repo.get_distribution(suburb, state, ptype, as_of)
            comparables = [
                {
                    "property_id": c["property_key"],
                    "address": c["address_display"],
                    "property_type": c["property_type"],
                    "price": c["price"],
                    "contract_date": c["sale_date"],
                    "land_area_m2": _round(c["land_area_m2"], 0),
                }
                for c in repo.get_comparables(prop, as_of)
            ]

        return {
            "property": {
                "id": prop["property_key"],
                "address": prop["address_display"],
                "suburb": suburb,
                "postcode": prop["postcode"],
                "state": state,
                "property_type": ptype,
                "land_area_m2": _round(prop["land_area_m2"], 0),
                "zoning": prop["zoning"],
                "sale_count": prop["sale_count"],
            },
            "metrics": {
                "last_sale_price": prop["last_sale_price"],
                "last_sale_date": prop["last_sale_date"],
                "cagr_pct": _round(prop["cagr_pct"]),
                "holding_years": _round(prop["holding_years"]),
                "vs_suburb_median_pct": _round(prop["vs_suburb_median_pct"]),
            },
            "suburb": {
                "name": suburb,
                "state": state,
                "property_type": ptype,
                "median_12m": _int(stats.get("median_12m")),
                "p25_12m": _int(stats.get("p25_12m")),
                "p75_12m": _int(stats.get("p75_12m")),
                "sales_12m": stats.get("sales_12m", 0),
                "change_1y_pct": _round(stats.get("change_1y_pct")),
                "change_3y_pct": _round(stats.get("change_3y_pct")),
                "change_5y_pct": _round(stats.get("change_5y_pct")),
            },
            "sales": sales,
            "trend": trend,
            "distribution": distribution,
            "comparables": comparables,
            "access": {
                "plan": "pro" if pro else "free",
                "locked_sections": [] if pro else FREE_LOCKED_SECTIONS,
            },
            "data_as_of": as_of,
        }

    @app.get("/me")
    def me(user: Annotated[UserRecord, Depends(current_user)]) -> dict[str, Any]:
        return {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "plan": user.plan,
            "status": user.status,
        }

    def require_billing() -> BillingGateway:
        if billing is None:
            raise HTTPException(503, "Billing is not configured")
        return billing

    def ensure_customer(gateway: BillingGateway, user: UserRecord) -> str:
        if user.stripe_customer_id:
            return user.stripe_customer_id
        customer_id = gateway.create_customer(user.email, user.name, user.id)
        repo.set_customer_id(user.id, customer_id)
        return customer_id

    @app.post("/billing/checkout")
    def checkout(
        body: CheckoutRequest, user: Annotated[UserRecord, Depends(current_user)]
    ) -> dict[str, str]:
        gateway = require_billing()
        price = {
            "pro_monthly": settings.stripe_price_monthly,
            "pro_annual": settings.stripe_price_annual,
        }[body.plan]
        if not price:
            raise HTTPException(503, "Billing is not configured")
        if user.plan == "pro":
            raise HTTPException(409, "Already subscribed; use the billing portal")
        base = settings.app_base_url.rstrip("/")
        url = gateway.checkout_url(
            ensure_customer(gateway, user), price, f"{base}/account?checkout=success", f"{base}/pricing"
        )
        return {"url": url}

    @app.post("/billing/portal")
    def portal(user: Annotated[UserRecord, Depends(current_user)]) -> dict[str, str]:
        gateway = require_billing()
        return_url = f"{settings.app_base_url.rstrip('/')}/account"
        return {"url": gateway.portal_url(ensure_customer(gateway, user), return_url)}

    @app.post("/webhooks/stripe")
    async def stripe_webhook(
        request: Request, stripe_signature: Annotated[str | None, Header()] = None
    ) -> dict[str, str]:
        if billing is None or not stripe_signature:
            raise HTTPException(400, "Webhook not accepted")
        payload = await request.body()
        try:
            event = billing.parse_event(payload, stripe_signature)
        except Exception as exc:  # signature or payload errors from the Stripe library
            raise HTTPException(400, "Invalid webhook signature") from exc
        if not repo.record_stripe_event(event["id"]):
            return {"status": "duplicate"}
        try:
            if event["type"] in SUBSCRIPTION_EVENTS:
                apply_subscription(event["data"]["object"])
        except Exception:
            repo.forget_stripe_event(event["id"])  # let Stripe retry the delivery
            raise
        return {"status": "ok"}

    def apply_subscription(subscription: dict[str, Any]) -> None:
        user = repo.get_user_by_customer(subscription["customer"])
        if user is None:
            log.warning("subscription event for unknown customer")
            return
        repo.upsert_subscription(
            subscription["id"], user.id, subscription["status"], _period_end(subscription)
        )

    return app


def build_default_app() -> FastAPI:
    """Entry point for `uvicorn au_sold_prices.api.app:build_default_app --factory`."""
    from au_sold_prices.api.auth import DevVerifier, EntraVerifier
    from au_sold_prices.api.billing import StripeGateway

    settings = Settings.from_env()
    settings.validate_for_production()
    repo = Repository.connect(settings.database_url)
    repo.ensure_app_schema()
    verifier: TokenVerifier
    if settings.auth_mode == "entra":
        verifier = EntraVerifier(
            settings.entra_tenant_id, settings.entra_tenant_subdomain, settings.entra_api_audience
        )
    else:
        verifier = DevVerifier()
    billing = (
        StripeGateway(settings.stripe_secret_key, settings.stripe_webhook_secret)
        if settings.stripe_secret_key
        else None
    )
    return create_app(settings, repo, verifier, billing)
