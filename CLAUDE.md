# g-core

The framework half of the G-System's topology layer. g-core holds no topology of its own.
An instance repo (gp-core is the reference one) holds the real `manifest.json`,
`presentation.json`, passport and house conventions, and g-core renders and validates them.
Open source under the GNU AGPL v3.0 only (`LICENSE`).

## Files
- `render_context.py` writes the topology block of an instance's `CLAUDE.md` from its
  `manifest.json` and keeps the instance's `AGENTS.md` a symlink to it. `--instance DIR`
  picks the instance, `--stdout` prints the result instead of writing it, and `--check`
  validates the manifest against the schema. With no `--instance` it tries `$G_INSTANCE`,
  then a sibling `gp-core`, then a sibling `gcore`.
- `render.py` builds the Cytoscape.js elements for the system diagram from
  `manifest.system`. Callers put g-core on `sys.path` and call `diagram_elements()`.
- `manifest.schema.json` lists the manifest keys in use. Readers ignore keys they do not
  know, so an instance can add its own.
- `examples/` is a complete, made-up instance on documentation addresses (192.0.2.x,
  example.com). Copy it to start a new instance.
- `conventions.md` holds the generic conventions: nervous system, agents/ pattern,
  compliance, health checks and lifecycle status.
- `alert-spine.md` is the contract between dependency probes, `/health` endpoints and the
  alert spine.
- `.githooks/pre-commit` is the template hook for an instance repo.
- `.env.example` shows the shape of a passport.

## Gotchas
- The rendered format, separators included, is byte-stable on purpose. Instances commit the
  output, and a host that runs an older copy of the renderer must produce the same bytes.
  A format change lands in g-core and in every vendored copy in the same sitting.
- An instance may keep a copy of `render_context.py` for hosts with no g-core checkout. A
  copy that sits beside a `manifest.json` renders its own directory before it looks at
  `$G_INSTANCE`. Keep such copies identical to this one.
- The session excerpt names the instance by the id of its own `system` entry (marked
  `"instance": true`), else by its directory name.
- Nothing instance-specific belongs here: no real hostnames, addresses, domains, tokens or
  alert topics. Run `gitleaks detect` on the history and on the working tree before pushing.
- `pyproject.toml` declares `[tool.g-core]`. Readers also accept the older `[tool.gcore]`.
