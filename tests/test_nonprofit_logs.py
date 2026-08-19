from datetime import datetime, timezone
from decimal import Decimal

import httpx
import pytest

from infrai_logs import InfraiError, InfraiLogs
from nonprofit_logs import DonorReceipt, to_structured_log


def test_pending_receipt_becomes_searchable_money_in_minor_units() -> None:
    receipt = DonorReceipt(
        kind="donor_receipt",
        receipt_id="receipt-1042",
        donor_id="donor-88",
        amount=Decimal("19.995"),
        currency="usd",
        delivered=False,
    )

    record = to_structured_log(
        receipt, datetime(2026, 8, 19, 9, 30, tzinfo=timezone.utc)
    )

    assert record["status"] == "delivery_pending"
    assert record["amount_minor"] == 2000
    assert record["currency"] == "USD"
    assert record["entity_id"] == "receipt-1042"


def test_business_rejection_is_read_from_envelope_before_status() -> None:
    def reject(request: httpx.Request) -> httpx.Response:
        assert dict(request.url.params) == {"q": "receipts", "limit": "20"}
        return httpx.Response(
            400,
            json={
                "ok": False,
                "data": None,
                "error": {"code": "rejected", "message": "query is required"},
                "metadata": {},
            },
        )

    with InfraiLogs(api_key="test-key", transport=httpx.MockTransport(reject)) as logs:
        with pytest.raises(InfraiError) as caught:
            logs.search("receipts")

    assert caught.value.status_code == 400
    assert caught.value.code == "rejected"


def test_ingest_retries_429_with_the_same_idempotency_key() -> None:
    requests: list[httpx.Request] = []

    def rate_limit_once(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if len(requests) == 1:
            return httpx.Response(
                429,
                headers={"Retry-After": "0"},
                json={"ok": False, "data": None, "error": {}, "metadata": {}},
            )
        return httpx.Response(
            200, json={"ok": True, "data": {"accepted": True}, "error": None, "metadata": {}}
        )

    with InfraiLogs(
        api_key="test-key",
        transport=httpx.MockTransport(rate_limit_once),
        sleep=lambda _: None,
    ) as logs:
        result = logs.ingest({"message": "receipt processed"}, "receipt:1042")

    assert result == {"accepted": True}
    assert [request.headers["Idempotency-Key"] for request in requests] == [
        "receipt:1042",
        "receipt:1042",
    ]
    assert requests[0].read() == (
        b'{"entries":[{"message":"receipt processed"}],'
        b'"idempotency_key":"receipt:1042"}'
    )
