#!/bin/bash
set -e
R=/mnt/e/Library/Desktop/ghostlock-beyond0q
cd "$R"
cat > .gitattributes <<'EOF'
* text=auto eol=lf
*.gz binary
*.gz2 binary
*.png binary
*.jpg binary
*.jpeg binary
*.apk binary
*.dex binary
*.a64 binary
*.ko binary
EOF
git branch -m master main 2>/dev/null || true
git add -A
git commit -q -m "chore(github): README status (session 6), .gitattributes; prep for public push" || echo "(nothing to commit)"
echo "== log =="
git log --oneline -4
echo "== branch =="
git branch -vv
echo "== remote =="
git remote -v || echo "(no remote)"
echo "== status =="
git status --short | head
echo "== size =="
git count-objects -vH | grep -E "size-pack|in-pack" || true
