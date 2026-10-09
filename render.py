"""g-core renderer: generates Cytoscape.js elements from an instance's manifest.json.

Every entry in manifest.system becomes a node and every inherits_from link an
"inherit" edge from parent to child. A few framework nodes (conventions, the
nervous system, git repos, terminal agents) hang off the roots. Put g-core on
sys.path and call diagram_elements(); the instance resolves as in
render_context.py.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from render_context import resolve_instance

# A description's subtitle ends at its first colon, or at the em dash that older
# instance data still uses there.
SUBTITLE_END = re.compile(": | \u2014 ")


def manifest(instance: Path | None = None) -> dict:
    inst = resolve_instance(instance)
    if inst is None:
        raise FileNotFoundError("no G-System instance found (pass one, or set G_INSTANCE)")
    return json.loads((inst / "manifest.json").read_text(encoding="utf-8"))


def diagram_elements(highlight: str | None = None, instance: Path | None = None) -> list[dict]:
    """Return Cytoscape.js elements (nodes + edges) from manifest."""
    els = []

    def node(id_, label, subtitle, type_, hl=False):
        els.append({"data": {
            "id": id_, "label": label, "subtitle": subtitle,
            "type": type_, "highlight": hl,
        }})

    def edge(id_, src, tgt, type_, label=""):
        els.append({"data": {
            "id": id_, "source": src, "target": tgt,
            "type": type_, "label": label,
        }})

    system = manifest(instance).get("system", [])
    ids = {r["id"] for r in system}

    # System repos
    for r in system:
        subtitle = SUBTITLE_END.split(r.get("description", ""), maxsplit=1)[0]
        node(r["id"], r["id"], subtitle, "system", highlight == r["id"])

    # Framework
    node("conventions",    "conventions",     "nervous system, lineage", "meta",   highlight == "conventions")
    node("nervous-system", "nervous system",  "CLAUDE.md and AGENTS.md",  "meta",   highlight == "nervous-system")
    node("terminal",       "terminal agents", "Claude Code, Codex",       "external")
    node("git-repos",      "git repos",       "source of truth",          "source")

    # Edges
    for r in system:
        parents = [p for p in r.get("inherits_from", []) if p in ids]
        for p in parents:
            edge(f"e-{p}-{r['id']}", p, r["id"], "inherit")
        if not r.get("inherits_from"):
            edge(f"e-{r['id']}-conv", r["id"], "conventions", "owns", "owns")

    edge("e-conv-ns",           "conventions",    "nervous-system", "defines",  "defines")
    edge("e-ns-git",            "nervous-system", "git-repos",      "lives-in", "lives in")
    edge("e-ns-terminal",       "nervous-system", "terminal",       "context",  "context")
    edge("e-terminal-write-git", "terminal",      "git-repos",      "writes",   "writes")

    return els


if __name__ == "__main__":
    print(json.dumps(diagram_elements(instance=Path(sys.argv[1]) if len(sys.argv) > 1 else None), indent=2))
