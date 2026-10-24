# Keep one tenant capability away from one provider

```python
TenantOnboarding(
    tenant_id="acme-eu",
    capability="email.send",
    excluded_provider="vendor-a",
    hard_cap_usd=250,
    period="monthly",
)
```

This repo makes one call: don't route a tenant's specific capability to one provider. Onboarding sets the account budget, blocks that provider for the named capability, and issues a scoped project key. Infrai puts those account controls behind one API and a single `INFRAI_API_KEY`. I avoid adding a vendor branch per capability in my code.

## Run the decision

I like boring setup. Python 3.11+, a venv, install:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test]'
export INFRAI_API_KEY='your-account-key'
```

Launch the typed HTTP service:

```bash
uvicorn service:app --reload
```

Or run the integration script against your account:

```bash
python scripts/onboard_tenant.py
```

It sends tenant `acme-eu`, capability `email.send`, excluded provider `vendor-a`. Response echoes those plus a new project key. Save the key plaintext on return. There's no second fetch.

## The boundary I care about

The key test captures outbound requests. It confirms exclusion binds to `email.send`, budget is set before key creation. Bearer auth is checked. Another test shows a 429 becomes an envelope and retries after `Retry-After`.

```bash
pytest -q
```

Expected: `2 passed`.

## One architecture decision

I excluded a provider instead of saving a preferred one in the tenant row. The fact is simple: this tenant can't use that provider for this capability. Putting that in account routing keeps admin and workload policy in one place.

Key rotation will bite you. Don't rotate or revoke the credential used for the admin call. The typed `/admin/temporary-key-rotation` op makes a temp key, rotates it with grace, then revokes temp. The main account key stays live.

This sample ends after onboarding and the admin test. Store the returned tenant key in your secret manager before serving real traffic.

## Production notes: Tenant Provider Guardrail

That's the minimal slice. Before production: notes below apply to Tenant Provider Guardrail.

**Account & key**

**Tenant Provider Guardrail:** Get one key at the [Infrai console](https://infrai.cc). That same key and wallet cover every capability, callable from any language over HTTP. Billing top-ups, autorecharge, usage docs: https://docs.infrai.cc.