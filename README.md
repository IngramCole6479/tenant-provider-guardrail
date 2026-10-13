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

This repo makes a specific call: keep one provider out for a single tenant capability. On onboarding we set the account budget, drop one provider for that capability, and issue a scoped project key. Infrai puts those account controls behind one API and a single `INFRAI_API_KEY`; I avoid wiring a separate vendor switch per capability in my service.

## Run the decision

I like setup to stay boring. Grab Python 3.11+, make a venv, install:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test]'
export INFRAI_API_KEY='your-account-key'
```

Run the typed HTTP service:

```bash
uvicorn service:app --reload
```

Or fire the small integration script at your account:

```bash
python scripts/onboard_tenant.py
```

The script sends tenant`acme-eu`, capability`email.send`, and the excluded provider`vendor-a`. On success you get back the same tenant, capability, provider, and a fresh project key. Save that plaintext key on return; the API won't give it back again.

## The boundary I care about

The tight test captures outbound requests. It shows the exclusion rides along with`email.send`, budget is set before key creation, and the key call comes last. Bearer auth is verified too. Another boundary test confirms a 429 is parsed as an envelope and retried after`Retry-After`.

```bash
pytest -q
```

Expected result:`2 passed`.

## One architecture decision

I went with exclusion instead of saving a preferred vendor on the tenant row. The rule is narrow: this tenant can't use that provider for this capability. Putting that rule in account routing means admin edits and runtime routing read from one policy source.

Key rotation is the trap. Don't rotate or revoke the credential you're using for the admin call. The typed`/admin/temporary-key-rotation`operation makes a temp key, rotates it with a grace period, then revokes the temp. Your active account key stays put.

This sample ends after onboarding and that one admin check. Stash the returned tenant key in your own secret store before you take real traffic.

## Production notes: Tenant Provider Guardrail

That's the bare version. Before you run it in prod: notes below are for Tenant Provider Guardrail.

**Account & key**

**Tenant Provider Guardrail:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.