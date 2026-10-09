#!/usr/bin/env python3
"""
Generate the <!-- TOPOLOGY:START --> block in an instance's CLAUDE.md from its
manifest.json, and keep the instance's AGENTS.md a symlink to it.
Run manually or via the instance's git pre-commit hook. Never hand-edit between
the markers.

Which instance (first match wins):
  1. --instance DIR
  2. the directory holding this file, when a manifest.json sits beside it. An
     instance may keep a copy of this file for hosts that have no g-core
     checkout, and that copy always renders the repo it lives in.
  3. $G_INSTANCE
  4. a sibling gp-core, then a sibling gcore (the legacy name)

The rendered format is byte-stable on purpose: instances commit the output, and
a host still running an older copy must produce the same bytes.

AGENTS.md used to be injected as a second real file. inject() only ever replaces
the topology block, so the AGENTS.md born from the "file does not exist" branch
started life as a bare block with none of the prose above it, and every later run
faithfully refreshed the block while the prose stayed missing. It drifted for
months and could never self-correct. A symlink removes the whole failure class.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCHEMA = HERE / "manifest.schema.json"
MARKER_START = "<!-- TOPOLOGY:START -->"
MARKER_END   = "<!-- TOPOLOGY:END -->"
# The G-System session loader injects only what sits between these; the rest of
# the block is reference that agents read here when a task touches it.
SESSION_START = "<!-- SESSION:START -->"
SESSION_END   = "<!-- SESSION:END -->"
# Separators of the rendered format (em dash, middle dot).
DASH = " \u2014 "
DOT  = " \u00b7 "

NO_INSTANCE = """No instance found. Pass --instance DIR, set G_INSTANCE, or put an
instance repo (gp-core) beside this g-core checkout. To start one:
  cp -r {examples} ../my-core && python3 {me} --instance ../my-core"""


def resolve_instance(explicit: Path | None = None) -> Path | None:
    if explicit is not None:
        return explicit.resolve()
    if (HERE / "manifest.json").exists():
        return HERE
    if os.environ.get("G_INSTANCE"):
        return Path(os.environ["G_INSTANCE"]).resolve()
    for name in ("gp-core", "gcore"):
        candidate = HERE.parent / name
        if (candidate / "manifest.json").exists():
            return candidate.resolve()
    return None


def instance_name(manifest: dict, instance: Path) -> str:
    """The instance's own id: its system entry marked "instance": true, else its directory name."""
    for r in manifest.get("system", []):
        if r.get("instance"):
            return r["id"]
    return instance.name


def generate(manifest: dict, name: str) -> str:
    lines = [MARKER_START, "## G-System topology (auto-generated from manifest.json)", ""]

    # Hosts (the session excerpt)
    lines.append(SESSION_START)
    lines.append("### Hosts")
    for h in manifest.get("hosts", []):
        aliases = ", ".join(h.get("aliases", []))
        lines.append(f"- **{h['id']}**{DASH}{h['hostname']} ({h['provider']}){DOT}user: {h['user']}{DOT}aliases: {aliases}")
    lines.append("")
    lines.append(f"Services, system repos and key paths: {name}/CLAUDE.md topology block; manifest.json is the SSOT.")
    lines.append(SESSION_END)
    lines.append("")

    # Services grouped by host
    lines.append("### Services")
    by_host: dict[str, list] = {}
    for s in manifest.get("services", []):
        by_host.setdefault(s.get("host", "?"), []).append(s)
    for host, svcs in by_host.items():
        lines.append(f"**{host}**")
        for s in svcs:
            domain = s.get("domain") or (f":{s['port']}" if s.get("port") else "")
            unit = s.get("unit", "")
            lines.append(f"  - {s['id']}{(DOT + domain) if domain else ''}{(DOT + 'systemd: ' + unit) if unit else ''}")
    lines.append("")

    # System repos
    lines.append("### System repos")
    for r in manifest.get("system", []):
        inherits = ", ".join(r.get("inherits_from", []))
        lines.append(f"- **{r['id']}**{DASH}{r['description']}{(' (inherits: ' + inherits + ')') if inherits else ''}")
    lines.append("")

    # Key paths, per host
    for h in manifest.get("hosts", []):
        if not h.get("key_paths"):
            continue
        lines.append(f"### Key paths on {h['id']}")
        for k in h["key_paths"]:
            lines.append(f"- `{k['path']}`{DASH}{k['note']}")
        lines.append("")

    lines.append(MARKER_END)
    return "\n".join(lines)


def inject(text: str | None, block: str) -> str:
    """Return the file contents with the topology block replaced or appended."""
    if text is None:
        return block + "\n"
    if MARKER_START in text and MARKER_END in text:
        before = text[:text.index(MARKER_START)]
        after  = text[text.index(MARKER_END) + len(MARKER_END):]
        return before + block + after
    # No markers yet: append
    return text.rstrip() + "\n\n" + block + "\n"


def mirror(claude: Path, agents: Path) -> str:
    """Point AGENTS.md at CLAUDE.md, repairing it if it drifted back to a file."""
    if agents.is_symlink() and agents.readlink() == Path(claude.name):
        return "AGENTS.md -> CLAUDE.md"
    if agents.exists() or agents.is_symlink():
        agents.unlink()
    try:
        agents.symlink_to(claude.name)
        return "AGENTS.md -> CLAUDE.md (relinked)"
    except OSError:
        # No symlink support here; a full copy still beats a headless file.
        agents.write_text(claude.read_text(encoding="utf-8"), encoding="utf-8")
        return "AGENTS.md copied (no symlink support)"


def problems(value, schema: dict, where: str = "manifest") -> list[str]:
    """The subset of JSON Schema that manifest.schema.json uses: type, enum,
    required, properties, items. Standard library only."""
    names = {"object": dict, "array": list, "string": str, "boolean": bool,
             "integer": int, "number": (int, float), "null": type(None)}
    types = schema.get("type")
    if types:
        types = [types] if isinstance(types, str) else types
        ok = any(isinstance(value, names[t]) and not (t in ("integer", "number") and isinstance(value, bool))
                 for t in types)
        if not ok:
            return [f"{where}: expected {' or '.join(types)}, got {type(value).__name__}"]
    if "enum" in schema and value not in schema["enum"]:
        return [f"{where}: {value!r} is not one of {schema['enum']}"]
    out = []
    if isinstance(value, dict):
        out += [f"{where}: missing required key '{k}'" for k in schema.get("required", []) if k not in value]
        for k, sub in schema.get("properties", {}).items():
            if k in value:
                out += problems(value[k], sub, f"{where}.{k}")
    if isinstance(value, list) and "items" in schema:
        for i, item in enumerate(value):
            label = item.get("id", item.get("number", i)) if isinstance(item, dict) else i
            out += problems(item, schema["items"], f"{where}[{label}]")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Render an instance's topology block from its manifest.json.")
    ap.add_argument("--instance", type=Path, help="instance repo holding manifest.json and CLAUDE.md")
    ap.add_argument("--stdout", action="store_true", help="print the rendered CLAUDE.md instead of writing it")
    ap.add_argument("--check", action="store_true", help="validate manifest.json against manifest.schema.json")
    args = ap.parse_args(argv)

    instance = resolve_instance(args.instance)
    if instance is None:
        print(NO_INSTANCE.format(examples=HERE / "examples", me=Path(__file__).name), file=sys.stderr)
        return 1
    if not (instance / "manifest.json").exists():
        print(f"{instance}: no manifest.json", file=sys.stderr)
        return 1
    manifest = json.loads((instance / "manifest.json").read_text(encoding="utf-8"))

    if args.check:
        if not SCHEMA.exists():
            print(f"{SCHEMA.name} not found beside {Path(__file__).name}", file=sys.stderr)
            return 1
        found = problems(manifest, json.loads(SCHEMA.read_text(encoding="utf-8")))
        for p in found:
            print(p)
        print(f"{instance / 'manifest.json'}: {len(found)} problem(s)")
        return 1 if found else 0

    claude = instance / "CLAUDE.md"
    text = inject(claude.read_text(encoding="utf-8") if claude.exists() else None,
                  generate(manifest, instance_name(manifest, instance)))
    if args.stdout:
        sys.stdout.buffer.write(text.encode("utf-8"))
        return 0
    claude.write_text(text, encoding="utf-8")
    print(f"{instance.name} context rendered -> CLAUDE.md, {mirror(claude, instance / 'AGENTS.md')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
