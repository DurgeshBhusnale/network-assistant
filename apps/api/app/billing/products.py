"""Products and entitlement windows (FR-PAY-1/5, tech spec §10). Pure; prices come from config."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

ProductCode = Literal["sprint", "pro_monthly", "pro_yearly"]


@dataclass(frozen=True)
class Product:
    code: ProductCode
    price_paise: int
    days: int
    enabled: bool


def catalogue(
    *,
    sprint_paise: int,
    sprint_days: int,
    pro_monthly_paise: int,
    pro_yearly_paise: int,
    pro_monthly_days: int,
    pro_yearly_days: int,
    pro_enabled: bool,
) -> dict[ProductCode, Product]:
    return {
        "sprint": Product("sprint", sprint_paise, sprint_days, True),
        "pro_monthly": Product("pro_monthly", pro_monthly_paise, pro_monthly_days, pro_enabled),
        "pro_yearly": Product("pro_yearly", pro_yearly_paise, pro_yearly_days, pro_enabled),
    }


def entitlement_window(
    product: Product, paid_at: datetime, current_end: datetime | None
) -> tuple[datetime, datetime]:
    """A new purchase starts now, or when the current paid period ends (purchases extend)."""
    starts = max(paid_at, current_end) if current_end else paid_at
    return starts, starts + timedelta(days=product.days)
