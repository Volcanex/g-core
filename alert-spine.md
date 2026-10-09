# The alert spine and the external-dependency catalog

Reference for wiring a dependency into monitoring, or for giving a service a `/health`
endpoint. The alert spine is the one push channel every alert goes through. Which server
and topics an instance uses is instance data and is not recorded here.

## The catalog

The `dependencies` list in `manifest.json` is the shared catalog of paid and external things
the system rests on: the push service, an LLM API, an SMS gateway, a domain registration.
Each entry carries a `provider`, what it `powers`, a `criticality` (`vital`, `important` or
`nice`) and a way to check it.

The brain's status layer (L5) checks every entry on a timer. It checks liveness (the
credentials still work, so the account is not unpaid or suspended) and, where it applies, a
balance threshold or an expiry date. It folds the result into the status snapshot and pages
the alert spine when any service or dependency goes down, starts to warn, or recovers.
Checks run where the credentials already live, in the instance passport or the brain's own
environment. Secrets are never copied into the manifest: a probe names the environment
variable and the brain reads it at check time.

A repo declares the catalog ids it relies on in `[tool.g-core].depends`. The reverse map
("the LLM API is down, so these repos are affected") comes from the lineage crawl, so it
needs no extra wiring. To add an external dependency, add a catalog entry with a check, then
name its id in each repo that uses it.

## How a dependency's liveness resolves

The first match wins:
1. `"health": {"service": "<id>", "check": "<key>"}`. The brain reads that service's
   `/health` and forwards the named check. The repo owns the check and keeps its own
   credentials, and the brain never holds them.
2. Else a central `probe`, used when the brain can reach the credentials itself, for example
   a shared token in the passport.
3. Else the entry is recorded as `unknown` ("declared, no probe").

Prefer `health` when the owning service can check the dependency better than the brain can,
for example a balance it already queries. Keep a central `probe` when the brain holds the
token and its check is richer, for example a balance threshold where the service only checks
auth. An entry may have both. `health` wins while the service is reachable, and the `probe`
is the fallback.

Probe types:
- `ntfy`: GET `/v1/health` on the server named by `url_env`.
- `http`: GET `url`, with the token from `auth_env` (sent as `auth_scheme`, default Bearer)
  or from `key_env` as a query parameter (`key_param`, default `api_key`). A 401 or 403 means
  down.
- `balance`: the same request, then read the number at `value_path` and subtract the one at
  `minus_path` if set. Zero or less is down, below `min` is a warning.
- `expires`: down after `date`, a warning within `warn_days` of it (default 14).

## The /health contract

A service exposes `GET /health`, which returns
`{"ok": bool, "checks": {"<key>": {"ok": bool, "detail": str}}}`. It returns 200 whenever
the process is up, even when a dependency is degraded. Dependency health lives in `checks`
and not in the status code, so "service up" and "dependency healthy" stay separate signals.
The brain forwards any mapped check with `ok: false` to the spine. It sends only transitions,
drops duplicates and tiers each alert by the dependency's `criticality`. A `nice` dependency
degrading is a warning, and a `vital` or `important` one going down is loud.

## Graded self-monitoring

Declaring dependencies is the floor (compliance box 4). Checking each declared dependency
above `nice`, through a central `probe` or a `/health` mapping, is the gold tier, and `nice`
dependencies are optional. This is enforced at runtime, not at commit time: an audit pulls
each service's `/health`, compares it with the dependencies the service declared above
`nice`, and pages the spine for any required one with no working check. The system polices
its own monitoring coverage through the one channel.
