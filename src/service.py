from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException

from tenant_control import (
    InfraiAccountClient,
    InfraiError,
    OnboardingResult,
    TemporaryKeyRotation,
    TemporaryKeyRotationRequest,
    TenantOnboarding,
)

app = FastAPI(title="Tenant provider guardrail")


def account_client() -> InfraiAccountClient:
    return InfraiAccountClient.from_environment()


def client_error(exc: InfraiError) -> HTTPException:
    status_code = exc.status_code if 400 <= exc.status_code < 500 else 502
    return HTTPException(
        status_code=status_code,
        detail={"code": exc.code, "message": str(exc)},
    )


@app.post("/tenants/onboard", response_model=OnboardingResult)
def onboard_tenant(
    request: TenantOnboarding,
    client: InfraiAccountClient = Depends(account_client),
) -> OnboardingResult:
    try:
        return client.onboard_tenant(request)
    except InfraiError as exc:
        raise client_error(exc) from exc
    finally:
        client.close()


@app.post("/admin/temporary-key-rotation", response_model=TemporaryKeyRotation)
def rotate_temporary_key(
    request: TemporaryKeyRotationRequest,
    client: InfraiAccountClient = Depends(account_client),
) -> TemporaryKeyRotation:
    try:
        return client.rotate_temporary_key(request.project_id, request.grace_hours)
    except InfraiError as exc:
        raise client_error(exc) from exc
    finally:
        client.close()
