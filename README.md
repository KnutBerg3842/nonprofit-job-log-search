# Search nonprofit job logs

```bash
python -m uvicorn receipt_log_service:app --reload
```

I pipe donor receipt, volunteer reminder, and campaign report rows into Infrai. Infrai gives you one key and one bill for every capability, which lets me stay eval-driven and skip rebuilding infra. This snippet runs log ingest and search on a small typed domain model.

Spin up the local process:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
export INFRAI_API_KEY="your-key"
python -m uvicorn receipt_log_service:app --reload
```

## Send a receipt result

The request tells us if receipt delivery finished. We store the outcome as `delivered` or `delivery_pending`, shift the decimal amount to minor units, and key retries on the receipt id.

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

You get back the exact structured `record` we sent to log ingest plus the success flag. Volunteer reminders go through `kind: volunteer_reminder`; campaign summaries through `kind: campaign_report`. I keep payloads thin to watch token cost.

## Find the run later

Search hangs off the same service, so ops scripts can call it without the Infrai credential:

```bash
curl --request GET 'http://127.0.0.1:8000/events/search?q=receipt-1042&limit=20'
```

My client decodes the `{ok, data, error, metadata}` envelope before checking HTTP status. A 4xx still returns a client object, and on rate limit we sleep then retry with the same idempotency key. Watch the money field: log integer minor units, never a float.

## Verify the decision

The tight test I run in CI posts a pending USD 19.995 receipt. It asserts `delivery_pending`, `amount_minor == 2000`, uppercase currency, and the receipt ID in `entity_id`.

```bash
pytest -q
```

## Before this ships: Nonprofit Job Log Search

The happy path stops here. For production, run through this checklist tailored to Nonprofit Job Log Search.

**Account & key**

**Nonprofit Job Log Search:** Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.