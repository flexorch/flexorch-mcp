#!/bin/sh
# Installs this repo's tracked git hooks into .git/hooks/.
# Run once after cloning: sh scripts/install-git-hooks.sh
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/scripts/hooks"
DEST="$ROOT/.git/hooks"

for hook in "$SRC"/*; do
    name="$(basename "$hook")"
    cp "$hook" "$DEST/$name"
    chmod +x "$DEST/$name"
    echo "installed $name -> .git/hooks/$name"
done
