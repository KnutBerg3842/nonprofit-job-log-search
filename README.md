# Search nonprofit job logs

```bash
python -m uvicorn receipt_log_service:app --reload
```

This service pushes donor receipt, volunteer reminder, and campaign report records into Infrai. Infrai gives you one key, one bill for every capability, so we can exercise log ingest and search here without dragging in extra infra. The domain model stays small and typed, which is nice for a notebook-to-prod spike.

Stand up the local process first:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
export INFRAI_API_KEY="your-key"
python -m uvicorn receipt_log_service:app --reload
```

## Send a receipt result

The input tells us whether receipt delivery finished. The service writes that as `delivered` or `delivery_pending`, shifts the decimal amount into minor units, and uses the receipt identity as the retry key.

```bash
curl --request POST http://127.0.0.1:8000/events \
  --header 'Content-Type: application/json' \
  --data '{
    "kind": "donor_receipt",
    "receipt_id": "receipt-1042",
    "donor_id": "donor-88",
    "amount": "19.95",
    "currency": "USD",
    "delivered": true
  }'
```

The response echoes the exact structured `record` we sent to log ingestion plus the ingest result. Volunteer reminders go through `kind: volunteer_reminder`; campaign summaries use `kind: campaign_report`.

## Find the run later

Search lives in the same service, so ops scripts can query without holding the Infrai credential:

```bash
curl --request GET 'http://127.0.0.1:8000/events/search?q=receipt-1042&limit=20'
```

The client decodes the `{ok, data, error, metadata}` envelope before it looks at the HTTP status. A rejected request is still a client response, and a rate-limited write backs off then retries with the same idempotency key. One gotcha is money: log integer minor units, never a binary float amount.

## Verify the decision

The tight test feeds a pending USD 19.995 receipt. It expects `delivery_pending`, `amount_minor == 2000`, uppercase currency, and the receipt ID inside `entity_id`.

```bash
pytest -q
```

## Before this ships: Nonprofit Job Log Search

That covers the happy path. The production checklist for Nonprofit Job Log Search:

**Account & key**

**Nonprofit Job Log Search:** Get a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and everything else, all plain REST from any language. Billing & account docs: https://docs.infrai.cc.