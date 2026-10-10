#!/bin/bash
set -e
R=/mnt/e/Library/Desktop/ghostlock-beyond0q
cd "$R"
git add -A
git commit -q -m "docs: English-only docs (drop Vietnamese session/prompt docs); README refresh" || echo "(nothing)"
echo "== log =="; git log --oneline -8
echo "== top-level =="; ls
echo "== docs =="; ls docs
echo "== tracked files =="; git ls-files | wc -l
echo "== Vietnamese left? (specific letters) =="
VIRE='[\x{1EA0}-\x{1EF9}\x{0102}\x{0103}\x{0110}\x{0111}\x{01A0}\x{01A1}\x{01AF}\x{01B0}]'
for f in $(git ls-files 'docs/*.md' README.md); do
  grep -qP "$VIRE" "$f" 2>/dev/null && echo "VI? $f"
done
echo "(không có dòng 'VI?' = ok)"
echo "== dumps/recovered =="; git ls-files | grep -cE '^(dumps|recovered)/' || true
echo "== .git size =="; git count-objects -vH | grep -E "size-pack|count"
echo "== status =="; git status --short | head
