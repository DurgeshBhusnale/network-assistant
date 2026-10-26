"""Billing (FR-PAY-*): plans, current entitlement, orders, checkout result, Razorpay webhook."""

import json
import logging
import uuid

from fastapi import APIRouter, Request, Response
from sqlalchemy import select

from app.analytics.track import track
from app.api.v1.deps import ClockDep, SettingsDep
from app.billing.razorpay import RazorpayClient, RazorpayError, webhook_signature_valid
from app.core.auth import CurrentUser
from app.core.db import Engine, service_session, user_session
from app.core.errors import AppError, ErrorCode
from app.domain.models import Payment
from app.domain.schemas import (
    CheckoutResultIn,
    EntitlementOut,
    OrderIn,
    OrderOut,
    PaymentStatusOut,
    PlanOption,
    PlansOut,
)
from app.services import payments
from app.services.profiles import ensure_profile

logger = logging.getLogger(__name__)
router = APIRouter(tags=["billing"])


def _dev_checkout(settings_app_env: str, client: RazorpayClient) -> bool:
    return not client.configured and settings_app_env in ("local", "test")


@router.get("/billing/plans", response_model=PlansOut)
async def plans(settings: SettingsDep) -> PlansOut:
    client = RazorpayClient(settings)
    return PlansOut(
        products=[
            PlanOption(product=p.code, price_paise=p.price_paise, days=p.days, enabled=p.enabled)
            for p in payments.products(settings).values()
        ],
        checkout_key_id=client.key_id or None,
        dev_checkout=_dev_checkout(settings.app_env, client),
    )


@router.get("/billing/entitlement", response_model=EntitlementOut)
async def entitlement(
    user: CurrentUser, engine: Engine, settings: SettingsDep, clock: ClockDep
) -> EntitlementOut:
    async with user_session(engine, user) as session:
        profile = await ensure_profile(session, user)
        return await payments.entitlement_out(
            session, user.id, clock.now(), profile.timezone, settings
        )


@router.post("/billing/orders", response_model=OrderOut, status_code=201)
async def create_order(
    body: OrderIn, user: CurrentUser, engine: Engine, settings: SettingsDep
) -> OrderOut:
    product = payments.products(settings)[body.product]
    if not product.enabled:
        raise AppError(ErrorCode.PRODUCT_UNAVAILABLE, "That plan isn't available yet.", 422)
    client = RazorpayClient(settings)
    dev = _dev_checkout(settings.app_env, client)
    if not client.configured and not dev:
        raise AppError(ErrorCode.PAYMENTS_UNAVAILABLE, "Payments aren't available yet.", 503)
    payment_id = uuid.uuid4()
    if dev:
        order_id = f"order_dev_{payment_id.hex[:14]}"
    else:
        try:
            order_id = await client.create_order(
                product.price_paise,
                str(payment_id),
                {"user_id": str(user.id), "product": product.code},
            )
        except RazorpayError as exc:
            raise AppError(
                ErrorCode.PAYMENTS_UNAVAILABLE, "Couldn't start the payment. Try again.", 503
            ) from exc
    # Payments are read-only to users (RLS): written with the service role, scoped to this user.
    async with service_session(engine) as session:
        session.add(
            Payment(
                id=payment_id,
                user_id=user.id,
                product=product.code,
                amount_paise=product.price_paise,
                provider_order_id=order_id,
            )
        )
    await track(
        engine, user.id, "checkout_started", {"product": product.code, "price": product.price_paise}
    )
    return OrderOut(
        payment_id=payment_id,
        order_id=order_id,
        amount_paise=product.price_paise,
        currency="INR",
        key_id=client.key_id or None,
        product=product.code,
        dev_checkout=dev,
    )


async def _status(
    engine: Engine, user: CurrentUser, settings: SettingsDep, clock: ClockDep, order_id: str
) -> PaymentStatusOut:
    async with user_session(engine, user) as session:
        profile = await ensure_profile(session, user)
        payment = await session.scalar(
            select(Payment).where(Payment.provider_order_id == order_id, Payment.user_id == user.id)
        )
        if payment is None:
            raise AppError(ErrorCode.NOT_FOUND, "Payment not found.", 404)
        ent = await payments.entitlement_out(
            session, user.id, clock.now(), profile.timezone, settings
        )
        return PaymentStatusOut(status=payment.status, entitlement=ent)


@router.post("/billing/checkout-result", response_model=PaymentStatusOut)
async def checkout_result(
    body: CheckoutResultIn,
    user: CurrentUser,
    engine: Engine,
    settings: SettingsDep,
    clock: ClockDep,
) -> PaymentStatusOut:
    """UX only: confirms the Checkout signature so the app can show "Payment processing".
    Never grants an entitlement; the webhook does (FR-PAY-4)."""
    client = RazorpayClient(settings)
    if client.configured and not client.checkout_valid(
        body.razorpay_order_id, body.razorpay_payment_id, body.razorpay_signature
    ):
        raise AppError(ErrorCode.VALIDATION_ERROR, "Couldn't verify that payment.", 422)
    return await _status(engine, user, settings, clock, body.razorpay_order_id)


@router.get("/billing/orders/{order_id}", response_model=PaymentStatusOut)
async def order_status(
    order_id: str, user: CurrentUser, engine: Engine, settings: SettingsDep, clock: ClockDep
) -> PaymentStatusOut:
    return await _status(engine, user, settings, clock, order_id)


@router.post("/billing/dev/complete/{order_id}", response_model=PaymentStatusOut)
async def dev_complete(
    order_id: str, user: CurrentUser, engine: Engine, settings: SettingsDep, clock: ClockDep
) -> PaymentStatusOut:
    """Local development only (no Razorpay keys): runs the same grant path the webhook uses."""
    if not _dev_checkout(settings.app_env, RazorpayClient(settings)) or not order_id.startswith(
        "order_dev_"
    ):
        raise AppError(ErrorCode.NOT_FOUND, "Not found.", 404)
    async with user_session(engine, user) as session:
        owned = await session.scalar(
            select(Payment.id).where(
                Payment.provider_order_id == order_id, Payment.user_id == user.id
            )
        )
    if owned is None:
        raise AppError(ErrorCode.NOT_FOUND, "Payment not found.", 404)
    granted = await payments.grant_from_event(
        engine,
        settings,
        event_id=f"dev_{order_id}",
        order_id=order_id,
        payment_id=f"pay_dev_{order_id[10:]}",
        now=clock.now(),
    )
    if granted:
        await track(engine, user.id, "payment_succeeded", {"dev": True})
    return await _status(engine, user, settings, clock, order_id)


@router.post("/webhooks/razorpay")
async def razorpay_webhook(
    request: Request, engine: Engine, settings: SettingsDep, clock: ClockDep
) -> Response:
    raw = await request.body()
    secret = (
        settings.razorpay_webhook_secret.get_secret_value()
        if settings.razorpay_webhook_secret
        else ""
    )
    if not webhook_signature_valid(raw, request.headers.get("x-razorpay-signature"), secret):
        return Response(status_code=400)
    try:
        event = json.loads(raw)
    except ValueError:
        return Response(status_code=400)
    name = str(event.get("event", ""))
    event_id = request.headers.get("x-razorpay-event-id") or str(event.get("id") or "")
    order_id, payment_id = payments.event_order_and_payment(event)
    now = clock.now()
    if name in ("payment.captured", "order.paid") and order_id:
        if await payments.grant_from_event(
            engine, settings, event_id=event_id, order_id=order_id, payment_id=payment_id, now=now
        ):
            async with service_session(engine) as session:
                payment = await session.scalar(
                    select(Payment).where(Payment.provider_order_id == order_id)
                )
            if payment is not None and payment.user_id is not None:
                await track(
                    engine,
                    payment.user_id,
                    "payment_succeeded",
                    {"product": payment.product, "price": payment.amount_paise},
                )
                if payment.product != "sprint":
                    await track(
                        engine, payment.user_id, "pro_upgraded", {"product": payment.product}
                    )
    elif name in ("refund.processed", "payment.refunded") and payment_id:
        await payments.refund(engine, payment_id=payment_id, now=now)
    else:
        logger.info("razorpay_event_ignored", extra={"event": name})
    return Response(status_code=200)
