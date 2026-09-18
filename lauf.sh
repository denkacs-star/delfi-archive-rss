#!/bin/bash
# Täglicher Lauf: archive.ph-Snapshot-Liste für rus.delfi.lv abrufen,
# feed.xml + index.html bauen und nach GitHub pushen (GitHub Pages
# published dann automatisch aus docs/ auf main).
set -euo pipefail
cd "$(dirname "$0")"

./venv/bin/python generate_feed.py docs

git add docs
if ! git diff --cached --quiet -- docs; then
    git commit -m "Feed-Update $(date -u +%Y-%m-%dT%H:%MZ)"
    git push origin main
    echo "gepusht"
else
    echo "keine Änderungen"
fi
