#!/bin/bash
set -e
R=/mnt/e/Library/Desktop/ghostlock-beyond0q
cd "$R"
mkdir -p tools/scripts

# 1) drop throwaway commit/prepublish helpers
for f in tools/_commit_*.sh tools/_prepush*.sh tools/_prepublish*.sh tools/_drop_vi_docs.sh tools/_rom_full_copy.sh tools/_hole.sh; do
  git rm -q --ignore-unmatch "$f" 2>/dev/null || true
done

# 2) move tracked root-level *.sh into tools/scripts/
for f in $(git ls-files '*.sh' | grep -v '^tools/' | grep -v '/'); do
  git mv "$f" tools/scripts/ 2>/dev/null || true
done

# 3) move tools/ scratch into tools/scripts/ (strip leading _)
for f in $(git ls-files 'tools/_*.sh' 'tools/_rsd.c' 'tools/getid.c' 'tools/mphelper.c'); do
  base=$(basename "$f" | sed 's/^_//')
  git mv "$f" "tools/scripts/$base" 2>/dev/null || true
done

git add -A
git commit -q -m "chore: tidy layout — helper scripts under tools/scripts/, drop throwaway scripts" || echo "(nothing to commit)"
echo "== root =="; ls
echo "== tools =="; ls tools
echo "== tools/scripts =="; ls tools/scripts
echo "== status =="; git status --short | head
