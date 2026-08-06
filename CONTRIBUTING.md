# Contributing

## Setup

```bash
pip install -e ".[dev]"
sh scripts/install-git-hooks.sh
```

The second command installs a local `pre-push` hook that runs `pytest tests/ -v` and `mypy src/` before every push — the same two steps CI runs. It exists because commit bc73a0b once passed pytest locally but failed CI on a mypy `no-redef` error that pytest has no way to catch. Run the install script once after cloning (`.git/hooks/` is not tracked by git, so this step doesn't happen automatically).

## Tests

```bash
pytest tests/ -v
mypy src/
```

## Bumping the version

```bash
python scripts/bump_version.py X.Y.Z
```

Updates `pyproject.toml`, `server.json`, `server-card.json`, and stubs a `CHANGELOG.md` entry atomically. `__init__.py` is not touched — it reads the version from package metadata.

## Pull requests

- One feature / fix per PR
- Tests required for new code
- Update `CHANGELOG.md`
- CI must pass (Python 3.10 / 3.11 / 3.12 / 3.13)
