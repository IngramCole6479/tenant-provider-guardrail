from __future__ import annotations

import json

from tenant_control import InfraiAccountClient, TenantOnboarding


def main() -> None:
    client = InfraiAccountClient.from_environment()
    try:
        result = client.onboard_tenant(
            TenantOnboarding(
                tenant_id="acme-eu",
                capability="email.send",
                excluded_provider="vendor-a",
                hard_cap_usd=250,
                period="monthly",
                alert_threshold_usd=200,
            )
        )
        print(json.dumps(result.model_dump(), indent=2))
    finally:
        client.close()


if __name__ == "__main__":
    main()
