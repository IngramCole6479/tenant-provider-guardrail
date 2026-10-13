from __future__ import annotations

import httpx

from tenant_control import InfraiAccountClient, TenantOnboarding


def test_onboarding_excludes_provider_only_for_selected_capability() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/v1/account/keys/create":
            return httpx.Response(200, json={"ok": True, "data": {"id": "key_42", "key": "issued-once"}})
        return httpx.Response(200, json={"ok": True, "data": {}})

    client = InfraiAccountClient("test-credential", transport=httpx.MockTransport(handler))
    try:
        result = client.onboard_tenant(
            TenantOnboarding(
                tenant_id="tenant-42",
                capability="email.send",
                excluded_provider="vendor-a",
                hard_cap_usd=100,
                period="monthly",
            )
        )
    finally:
        client.close()

    assert result.excluded_provider == "vendor-a"
    assert [request.method for request in requests] == ["PUT", "PUT", "POST"]
    routing_request = requests[1]
    assert routing_request.url.path == "/v1/account/routing/set"
    assert routing_request.read() == b'{"capability":"email.send","exclude":["vendor-a"]}'
    assert requests[2].headers["Authorization"] == "Bearer test-credential"
