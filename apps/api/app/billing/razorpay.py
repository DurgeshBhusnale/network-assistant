"""Razorpay Orders + signatures (FR-PAY-4). Entitlements come only from verified webhooks."""

import hashlib
import hmac

import httpx

from app.core.config import Settings

API = "https://api.razorpay.com/v1"


class RazorpayError(RuntimeError):
    pass


def _hmac(secret: str, message: bytes) -> str:
    return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()


def checkout_signature_valid(
    order_id: str, payment_id: str, signature: str, key_secret: str
) -> bool:
    """The Checkout handler's signature: HMAC-SHA256("order_id|payment_id", key secret). UX only."""
    if not (order_id and payment_id and signature and key_secret):
        return False
    return hmac.compare_digest(_hmac(key_secret, f"{order_id}|{payment_id}".encode()), signature)


def webhook_signature_valid(raw_body: bytes, signature: str | None, webhook_secret: str) -> bool:
    """X-Razorpay-Signature = HMAC-SHA256(raw body, webhook secret), constant-time."""
    if not (signature and webhook_secret):
        return False
    return hmac.compare_digest(_hmac(webhook_secret, raw_body), signature)


class RazorpayClient:
    def __init__(self, settings: Settings) -> None:
        self.key_id = settings.razorpay_key_id
        self._secret = (
            settings.razorpay_key_secret.get_secret_value() if settings.razorpay_key_secret else ""
        )

    @property
    def configured(self) -> bool:
        return bool(self.key_id and self._secret)

    async def create_order(self, amount_paise: int, receipt: str, notes: dict[str, str]) -> str:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                f"{API}/orders",
                auth=(self.key_id, self._secret),
                json={
                    "amount": amount_paise,
                    "currency": "INR",
                    "receipt": receipt,
                    "notes": notes,
                },
            )
        if r.status_code >= 300:
            raise RazorpayError(f"order failed: {r.status_code}")
        return str(r.json()["id"])

    def checkout_valid(self, order_id: str, payment_id: str, signature: str) -> bool:
        return checkout_signature_valid(order_id, payment_id, signature, self._secret)
