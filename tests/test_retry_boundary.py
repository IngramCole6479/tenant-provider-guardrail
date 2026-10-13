from __future__ import annotations

import httpx

from tenant_control import InfraiAccountClient


def test_rate_limit_honors_retry_after_before_retrying() -> None:
    attempts = 0
    delays: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(
                429,
                headers={"Retry-After": "3"},
                json={"ok": False, "data": None, "error": {}, "metadata": {}},
            )
        return httpx.Response(200, json={"ok": True, "data": {}, "error": None, "metadata": {}})

    client = InfraiAccountClient(
        "test-credential",
        transport=httpx.MockTransport(handler),
        sleep=delays.append,
    )
    try:
        client._request(
            "PUT",
            "/v1/account/routing/set",
            body={"capability": "email.send", "exclude": "vendor-a"},
        )
    finally:
        client.close()

    assert attempts == 2
    assert delays == [3.0]
