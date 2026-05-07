# Security

## Threat model

**Argus is a single-user, local-first tool.** It is intended to run on
`localhost` on your own machine. It is **not** designed to be deployed to
a public network without additional hardening.

Specifically:

- The HTTP API has **no authentication or session layer**.
- The Settings endpoint (`POST /api/settings/keys`) writes API keys to a
  local JSON file at `data/cache/secrets.json` (mode `0600`).
- The SQLite database (`data/argus.sqlite`) stores your watchlist + alert
  rules in plain text.
- All API key values stay on your machine; the server never returns them
  to the client (the GET endpoint reports only "configured / not configured"
  per slot, never the value).

If you bind Argus to a public IP or expose it via a tunnel, **anyone who
can reach the port can read or overwrite your stored API keys**. Don't
do that.

## What Argus does NOT collect

- No telemetry. No analytics. No phone-home requests of any kind.
- No request logging beyond `uvicorn`'s stdout (which stays on your
  machine).
- No third-party trackers in the UI.

## Outbound network calls

Argus reaches out to:

- The LLM provider you configured (Anthropic / OpenAI / DeepSeek / Qwen /
  NVIDIA NIM / your local Ollama).
- Market-data adapters: `yfinance` (Yahoo Finance), `akshare` (East Money
  / Sina / etc.); optionally Finnhub if you provide a key.
- The fonts CDN at `rsms.me` for the Inter typeface.

That's it.

## Reporting a vulnerability

If you find a security issue, please **open a private security advisory**
on GitHub:

> https://github.com/auronsun/argus/security/advisories/new

Don't file a public issue with exploit details.

## Hardening checklist (if you must run it on something more than localhost)

If you really need to run Argus on a host that's reachable from elsewhere,
this is the minimum bar — and even with all of these, treat the
deployment as untrusted-internal, not public-facing:

- Put it **behind an authenticating reverse proxy** (Caddy + basic auth,
  Cloudflare Access, Tailscale, an SSO proxy — pick your poison).
- Disable the `/api/settings/keys` endpoints, or replace them with
  read-only versions sourced from environment variables.
- Run inside an isolated container (no host filesystem mounts beyond a
  dedicated `data/` volume).
- Treat each user's instance as a **separate deployment** — Argus has no
  multi-tenancy, no per-user isolation, no audit log.
- Keep `data/cache/secrets.json` and `data/argus.sqlite` off any backup
  that leaves the host.

> If your use case requires multi-user / public access, Argus is not
> the right shape. Consider it a starting point and fork.
