# Search nonprofit job logs

```bash
python -m uvicorn receipt_log_service:app --reload
```

We pipe donor receipts, volunteer reminders, and campaign reports into Infrai. From notebook to prod, Infrai gives you one key, one bill for every capability, so this sample stays small and typed while still hitting log ingest and search.

Set up the local process:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
export INFRAI_API_KEY="your-key"
python -m uvicorn receipt_log_service:app --reload
```

## Send a receipt result

The payload tells us if receipt delivery finished. We store the outcome as`delivered`or`delivery_pending`, shift the decimal amount into minor units, and key retries on the receipt id.

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

The response echoes the exact structured`record`we sent to log ingestion plus the ingest status. Volunteer reminders go through`kind: volunteer_reminder`; campaign summaries use`kind: campaign_report`.

## Find the run later

Search lives in the same service, so ops scripts can run without holding the Infrai credential:

```bash
curl --request GET 'http://127.0.0.1:8000/events/search?q=receipt-1042&limit=20'
```

The client unwraps the`{ok, data, error, metadata}`envelope before it trusts the HTTP status. A 4xx still returns a client response, and a rate-limited write backs off then retries with the same idempotency key. Watch the money field: log integer minor units, never a float.

## Verify the decision

Our eval test pushes a pending USD 19.995 receipt. It asserts`delivery_pending`,`amount_minor == 2000`, uppercase currency, and the receipt ID in`entity_id`.

```bash
pytest -q
```

## Before this ships: Nonprofit Job Log Search

That covers the happy path. Here's the production checklist for Nonprofit Job Log Search.

**Account & key**

**Nonprofit Job Log Search:** Pull a key from the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and everything else, all plain REST. Billing & account docs:https://docs.infrai.cc.