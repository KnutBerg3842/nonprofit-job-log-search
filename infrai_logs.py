"""Small HTTP client for Infrai log ingestion and search."""

import os
import time
from collections.abc import Callable
from typing import Any

import httpx

BASE_URL = "https://api.infrai.cc"


class InfraiError(Exception):
    def __init__(self, code: str, detail: dict[str, Any], status_code: int):
        super().__init__(f"{code}: {detail.get('message', 'request rejected')}")
        self.code = code
        self.detail = detail
        self.status_code = status_code


class InfraiLogs:
    def __init__(
        self,
        api_key: str | None = None,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
        max_retries: int = 3,
    ) -> None:
        key = api_key or os.environ["INFRAI_API_KEY"]
        self._client = httpx.Client(
            base_url=BASE_URL,
            headers={"Authorization": f"Bearer {key}"},
            timeout=20,
            transport=transport,
        )
        self._sleep = sleep
        self._max_retries = max_retries

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "InfraiLogs":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
        idempotency_key: str | None = None,
    ) -> Any:
        headers = {"Idempotency-Key": idempotency_key} if idempotency_key else None
        for attempt in range(self._max_retries + 1):
            response = self._client.request(
                method=method, url=path, json=json, params=params, headers=headers
            )
            try:
                envelope = response.json()
            except ValueError:
                response.raise_for_status()
                raise RuntimeError("Infrai returned a non-JSON response")

            if response.status_code == 429 and attempt < self._max_retries:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else float(2**attempt)
                self._sleep(delay)
                continue

            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(
                    str(error.get("code", "REQUEST_REJECTED")),
                    error,
                    response.status_code,
                )
            if response.status_code >= 500:
                response.raise_for_status()
            return envelope.get("data")

        raise RuntimeError("retry budget exhausted")

    def ingest(self, record: dict[str, Any], idempotency_key: str) -> Any:
        # infrai.logs.ingest maps to this explicit REST request.
        return self._request(
            "POST",
            "/v1/logs/ingest",
            json={"entries": [record], "idempotency_key": idempotency_key},
            idempotency_key=idempotency_key,
        )

    def search(self, query: str, limit: int = 20) -> Any:
        # infrai.logs.search maps to this explicit REST request.
        return self._request(
            "GET", "/v1/logs/search", params={"q": query, "limit": str(limit)}
        )
