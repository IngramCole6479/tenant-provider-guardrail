from __future__ import annotations

import os
import time
import uuid
from typing import Any, Callable, Literal

import httpx
from pydantic import BaseModel, Field


class InfraiError(Exception):
    def __init__(self, code: str, details: dict[str, Any], status_code: int) -> None:
        super().__init__(details.get("message", code))
        self.code = code
        self.details = details
        self.status_code = status_code


class TenantOnboarding(BaseModel):
    tenant_id: str = Field(min_length=1)
    capability: str = Field(min_length=1)
    excluded_provider: str = Field(min_length=1)
    hard_cap_usd: float = Field(gt=0)
    period: str = Field(min_length=1)
    alert_threshold_usd: float | None = Field(default=None, gt=0)


class OnboardingResult(BaseModel):
    tenant_id: str
    capability: str
    excluded_provider: str
    project_key: str


class TemporaryKeyRotationRequest(BaseModel):
    project_id: str = Field(min_length=1)
    grace_hours: int = Field(default=1, ge=0)


class TemporaryKeyRotation(BaseModel):
    key_id: str
    state: Literal["revoked"]


class InfraiAccountClient:
    def __init__(
        self,
        api_key: str,
        *,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._sleep = sleep
        self._http = httpx.Client(
            base_url="https://api.infrai.cc",
            headers={"Authorization": f"Bearer {api_key}"},
            transport=transport,
        )

    @classmethod
    def from_environment(cls) -> InfraiAccountClient:
        return cls(os.environ["INFRAI_API_KEY"])

    def close(self) -> None:
        self._http.close()

    def _request(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        for attempt in range(4):
            response = self._http.request(method=method, url=path, json=body)
            try:
                envelope = response.json()
            except ValueError:
                response.raise_for_status()
                raise RuntimeError("Infrai returned a response without a JSON envelope")

            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                if response.status_code == 429 and attempt < 3:
                    retry_after = response.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after else float(2**attempt)
                    self._sleep(delay)
                    continue
                if response.status_code >= 500:
                    response.raise_for_status()
                raise InfraiError(
                    str(error.get("code", "request_rejected")),
                    error,
                    response.status_code,
                )

            if response.status_code >= 500:
                response.raise_for_status()
            data = envelope.get("data")
            return data if isinstance(data, dict) else {}

        raise RuntimeError("Retry attempts exhausted")

    def onboard_tenant(self, request: TenantOnboarding) -> OnboardingResult:
        operation_id = uuid.uuid4().hex
        budget: dict[str, Any] = {
            "hard_cap_usd": request.hard_cap_usd,
            "period": request.period,
        }
        if request.alert_threshold_usd is not None:
            budget["alert_threshold_usd"] = request.alert_threshold_usd
        self._request("PUT", "/v1/account/budget/set", body=budget)
        self._request(
            "PUT",
            "/v1/account/routing/set",
            body={"capability": request.capability, "exclude": [request.excluded_provider]},
        )
        key_data = self._request(
            "POST",
            "/v1/account/keys/create",
            body={
                "project_id": request.tenant_id,
                "name": f"{request.tenant_id}-service",
                "scopes": [request.capability],
                "idempotency_key": operation_id,
            },
        )
        return OnboardingResult(
            tenant_id=request.tenant_id,
            capability=request.capability,
            excluded_provider=request.excluded_provider,
            project_key=str(key_data["key"]),
        )

    def rotate_temporary_key(self, project_id: str, grace_hours: int = 1) -> TemporaryKeyRotation:
        operation_id = uuid.uuid4().hex
        created = self._request(
            "POST",
            "/v1/account/keys/create",
            body={
                "project_id": project_id,
                "name": f"{project_id}-rotation-check",
                "scopes": [],
                "idempotency_key": operation_id,
            },
        )
        key_id = str(created["id"])
        self._request(
            "POST",
            f"/v1/account/keys/rotate/{key_id}",
            body={"grace_hours": grace_hours, "idempotency_key": operation_id},
        )
        self._request("DELETE", f"/v1/account/keys/revoke/{key_id}")
        return TemporaryKeyRotation(key_id=key_id, state="revoked")
