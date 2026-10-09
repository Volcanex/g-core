---
title: Conventions
kind: core
---

# Conventions

The generic conventions of the G-System. An instance keeps its own `conventions.md` for
house rules and personal preferences, and the session loader injects only the block between
that file's SESSION markers. This file is reference, read when a task touches it.

## Nervous system (CLAUDE.md and AGENTS.md)

A `CLAUDE.md` says what is not already plain from the code. If the code tells you, don't
repeat it. If it doesn't, because of a hidden constraint, a structural choice, a gotcha or a
convention, write it down.

- Every directory with non-obvious behaviour gets its own `CLAUDE.md`.
- The docs follow the directory tree, so nested directories get nested docs.
- Agents update the relevant `CLAUDE.md` whenever they change a directory's shape.
- The root `CLAUDE.md` is the entry point and index. Keep it under about 300 lines and link
  down to child docs.
- File paths in code spans inside a `CLAUDE.md` must exist on disk.
- `AGENTS.md` mirrors `CLAUDE.md` for Codex-style agents. Make it a symlink to `CLAUDE.md` and
  commit the symlink.

A new project's `CLAUDE.md` is short: owner, what it does, how to run it, gotchas.

## agents/ pattern (parallel work)

For any task that splits across worktrees:
- an `agents/` directory at the repo root holds the kickoff briefs, one per workstream
- `agents/_template.md` is the starter to copy
- each brief names its worktree, its scope and its done condition
- prune `agents/` entries after the branch merges

## Compliance

A project is compliant (`managed: true` in its `manifest.json` entry) when it ticks all four
boxes:

1. **Nervous system.** `CLAUDE.md` (and `AGENTS.md`) in every directory with non-obvious
   behaviour.
2. **pip-installable.** A `pyproject.toml` at the root with at least `[project]` name, version
   and description.
3. **GitHub.** The repo lives under the instance's GitHub owner.
4. **Self-monitoring.** It declares its external dependencies in `[tool.g-core].depends`, so
   the system knows what it relies on and can route a lapse to the alert spine.

Lineage and dependencies go in `pyproject.toml`:

```toml
[tool.g-core]
starter = "seed-app@1.0.0"   # optional, leave it out if no starter was used
design  = "g-design@1.0.0"   # the design language, leave it out for a one-off look
depends = ["ntfy", "llm"]    # external dependency ids from the catalog, [] if none
```

Readers also accept the older table name `[tool.gcore]`. `starter` and `design` are lineage
metadata for the brain's lineage crawl. `depends` names ids from the catalog under
`dependencies` in `manifest.json`. An empty list is a positive claim: the repo has no
external dependencies and someone checked. Write `[]` rather than leaving `depends` out.

How probes, `/health` endpoints and the alert spine fit together is in `alert-spine.md`.

## Services and health checks

Every entry under `services` in `manifest.json` carries `unit`, its systemd service name,
so the command dashboard can check that the process is alive. It is `null` when systemd
does not run it, for example a static site served by the web server.

The health check resolves in this order, and the first match wins:
1. `health_url` set: HTTP GET, expect 2xx
2. `health_url` null and `domain` set: `GET https://{domain}/`, expect 2xx
3. `health_url` null and `port` set: TCP connect to `localhost:{port}`
4. `unit` only: `systemctl is-active {unit}`

A service with none of these is not compliant.

## Project lifecycle status

An entry under `projects` in `manifest.json` may carry a `status`:
- `active` is the default, so leave `status` out
- `deprecated` means it still exists, but nobody develops it and nothing new links to it
- `fossil` means it is frozen on purpose and has moved to its own address, so that a newer
  project can take the old one

`deprecated` and `fossil` both mean "don't build here". `fossil` also implies a live move to
a new address, not just neglect. Consumers show non-active projects greyed out rather than
hiding them, so the history stays visible.
