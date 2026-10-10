#!/bin/bash
set -e
R=/mnt/e/Library/Desktop/ghostlock-beyond0q
cd "$R"

# 1) LICENSE GPL-2.0
if [ -f /usr/share/common-licenses/GPL-2 ]; then
  cp /usr/share/common-licenses/GPL-2 LICENSE
elif [ -f /usr/share/common-licenses/GPL-2.0 ]; then
  cp /usr/share/common-licenses/GPL-2.0 LICENSE
else
  echo "!! no GPL-2 text found"; fi
ls -l LICENSE 2>&1 | head -1

# 2) purge dumps/ + recovered/ from ALL history
export FILTER_BRANCH_SQUELCH_WARNING=1
git filter-branch --force --index-filter \
  'git rm -r --cached --ignore-unmatch dumps recovered' \
  --prune-empty -- --all >/tmp/fb.log 2>&1 || { echo FILTER_FAIL; tail -5 /tmp/fb.log; }
rm -rf .git/refs/original 2>/dev/null || true

# 3) gitignore
grep -q '^dumps/$' .gitignore || printf '\n# evidence / session logs — not published\ndumps/\nrecovered/\n' >> .gitignore

# 4) commit + tidy
git add -A
git commit -q -m "chore: add GPL-2.0 LICENSE; drop dumps/ + recovered/ from the repo" || echo "(nothing)"
git reflog expire --expire=now --all 2>/dev/null || true
git gc --prune=now --aggressive >/dev/null 2>&1 || true

echo "== log =="
git log --oneline -6
echo "== tracked files =="; git ls-files | wc -l
echo "== dumps/recovered still tracked? =="; git ls-files | grep -cE '^(dumps|recovered)/' || true
echo "== .git size =="; du -sh .git
echo "== docs language (VI vs EN) =="
for f in docs/*.md README.md; do
  if grep -qP '[\x{00C0}-\x{1EF9}]' "$f" 2>/dev/null; then echo "VI  $f"; else echo "EN  $f"; fi
done
