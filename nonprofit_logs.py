"""Typed nonprofit events and their structured log representation."""

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field


class DonorReceipt(BaseModel):
    kind: Literal["donor_receipt"]
    receipt_id: str
    donor_id: str
    amount: Decimal = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    delivered: bool


class VolunteerReminder(BaseModel):
    kind: Literal["volunteer_reminder"]
    reminder_id: str
    volunteer_id: str
    shift_id: str
    delivered: bool


class CampaignReport(BaseModel):
    kind: Literal["campaign_report"]
    campaign_id: str
    donations_count: int = Field(ge=0)
    total_amount: Decimal = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)


NonprofitEvent = Annotated[
    Union[DonorReceipt, VolunteerReminder, CampaignReport],
    Field(discriminator="kind"),
]


def to_structured_log(event: NonprofitEvent, occurred_at: datetime | None = None) -> dict:
    """Make the operational decision visible in a stable, searchable shape."""
    timestamp = occurred_at or datetime.now(timezone.utc)
    base = {
        "timestamp": timestamp.isoformat(),
        "service": "nonprofit-jobs",
        "event": event.kind,
        "level": "info",
    }

    if isinstance(event, DonorReceipt):
        cents = int((event.amount * 100).quantize(Decimal("1"), ROUND_HALF_UP))
        return base | {
            "message": "donor receipt processed",
            "status": "delivered" if event.delivered else "delivery_pending",
            "entity_id": event.receipt_id,
            "donor_id": event.donor_id,
            "amount_minor": cents,
            "currency": event.currency.upper(),
        }

    if isinstance(event, VolunteerReminder):
        return base | {
            "message": "volunteer reminder processed",
            "status": "delivered" if event.delivered else "delivery_pending",
            "entity_id": event.reminder_id,
            "volunteer_id": event.volunteer_id,
            "shift_id": event.shift_id,
        }

    cents = int((event.total_amount * 100).quantize(Decimal("1"), ROUND_HALF_UP))
    return base | {
        "message": "campaign report completed",
        "status": "completed",
        "entity_id": event.campaign_id,
        "donations_count": event.donations_count,
        "amount_minor": cents,
        "currency": event.currency.upper(),
    }

