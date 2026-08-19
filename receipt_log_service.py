"""HTTP boundary for nonprofit job logs."""

from typing import Any

from fastapi import FastAPI, HTTPException, Query

from infrai_logs import InfraiError, InfraiLogs
from nonprofit_logs import NonprofitEvent, to_structured_log

app = FastAPI(title="Nonprofit job logs")


@app.post("/events")
def record_event(event: NonprofitEvent) -> dict[str, Any]:
    record = to_structured_log(event)
    idempotency_key = f"{event.kind}:{record['entity_id']}"
    try:
        with InfraiLogs() as logs:
            result = logs.ingest(record, idempotency_key=idempotency_key)
    except InfraiError as exc:
        status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(status_code=status, detail=exc.detail) from exc
    return {"record": record, "ingest": result}


@app.get("/events/search")
def search_events(q: str = Query(min_length=1), limit: int = Query(20, ge=1, le=100)) -> Any:
    try:
        with InfraiLogs() as logs:
            return logs.search(q, limit)
    except InfraiError as exc:
        status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(status_code=status, detail=exc.detail) from exc

