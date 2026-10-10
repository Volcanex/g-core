# g-core

g-core is the topology layer of the G-System, a set of repos that wires agents, hosts and
services together, and it holds the schema and the renderers. The data itself lives in an
instance repo, which stays private: a `manifest.json` that lists the hosts, workspaces,
system repos, services, external dependencies and projects.

From that manifest g-core writes two things: the topology block in the instance's
`CLAUDE.md`, which every agent session loads, and the elements for the system diagram on the
command dashboard.

## Start an instance

```sh
cp -r g-core/examples my-core
cd my-core && git init
mkdir .githooks && cp ../g-core/.githooks/pre-commit .githooks/
git config core.hooksPath .githooks
python3 ../g-core/render_context.py --instance . --check
python3 ../g-core/render_context.py --instance .
```

Edit `manifest.json` and commit, and the hook renders `CLAUDE.md` again. `conventions.md` and
`alert-spine.md` describe how the rest of the system reads the manifest and what it expects
from each project.

## Licence

Copyright (C) 2026 Gabriel Penman. Licensed under the GNU Affero General Public License v3.0 only, see `LICENSE`.
