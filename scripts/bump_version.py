#!/usr/bin/env python3
"""Bump flexorch-mcp version across all config files.

Usage:
    python scripts/bump_version.py X.Y.Z

Updates: pyproject.toml, server.json, server-card.json, CHANGELOG.md (stub entry).
__init__.py is NOT in the list — it reads version from package metadata automatically.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")
    print(f"  ok: {path.relative_to(ROOT)}")


def current_version() -> str:
    m = re.search(r'^version\s*=\s*"([\d.]+)"', _read(ROOT / "pyproject.toml"), re.MULTILINE)
    assert m, "version not found in pyproject.toml"
    return m.group(1)


def main() -> None:
    if len(sys.argv) != 2 or not re.fullmatch(r"\d+\.\d+\.\d+", sys.argv[1]):
        print("Usage: python scripts/bump_version.py X.Y.Z")
        sys.exit(1)

    new = sys.argv[1]
    old = current_version()
    print(f"Bumping {old} -> {new}\n")

    # pyproject.toml — match only the [project] version line
    p = ROOT / "pyproject.toml"
    _write(p, re.sub(
        rf'^(version\s*=\s*"){re.escape(old)}"',
        rf'\g<1>{new}"',
        _read(p), flags=re.MULTILINE
    ))

    # server.json — replace all occurrences of the old version string
    for fname in ("server.json", "server-card.json"):
        f = ROOT / fname
        _write(f, _read(f).replace(f'"{old}"', f'"{new}"'))

    # CHANGELOG.md — prepend stub entry
    cl = ROOT / "CHANGELOG.md"
    stub = f"## [{new}] — YYYY-MM-DD\n\n### Changed\n- TODO\n\n---\n\n"
    _write(cl, _read(cl).replace("# Changelog\n\nAll notable changes", f"# Changelog\n\nAll notable changes", 1))
    content = _read(cl)
    insert_at = content.index("\n## [")
    _write(cl, content[:insert_at + 1] + stub + content[insert_at + 1:])

    print(f"\nAll files updated. Checklist for releasing v{new}:")
    print(f"  1. Fill in CHANGELOG entry for {new}")
    print(f"  2. git add pyproject.toml server.json server-card.json CHANGELOG.md")
    print(f"  3. git commit -m 'chore: bump version to {new}'")
    print(f"  4. git tag v{new} && git push origin main --tags")
    print(f"  5. rm -rf dist/ && python -m build")
    print(f"  6. python -m twine upload \"dist/flexorch_mcp-{new}*\"")
    print(f"  7. Hetzner docker:")
    print(f"       sed -i 's/flexorch-mcp=={old}/flexorch-mcp=={new}/' docker-compose.yml")
    print(f"       docker compose build flexorch-mcp && docker compose up -d flexorch-mcp")
    print(f"  8. Hetzner server-card.json:")
    print(f"       wget -O /opt/flexorch/mcp-static/.well-known/mcp/server-card.json \\")
    print(f"            https://raw.githubusercontent.com/flexorch/flexorch-mcp/main/server-card.json")
    print(f"  9. Smithery: publish")


if __name__ == "__main__":
    main()
