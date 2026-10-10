#!/bin/bash
R=/mnt/e/Library/Desktop/ghostlock-beyond0q
cd "$R"
echo "== status =="
git status --short | head
echo "== branch/remote =="
git branch -vv
git remote -v
echo "== log =="
git log --oneline -12
echo "== tracked count / size =="
echo "files: $(git ls-files | wc -l)"
git count-objects -vH | grep -E "size-pack|count|size"
echo "== working tree du =="
du -sh "$R" 2>/dev/null
echo "== top-level dirs =="
du -sh "$R"/*/ 2>/dev/null | sort -rh | head -20
echo "== 25 largest TRACKED files =="
git ls-files -z | xargs -0 -I{} du -k "$R/{}" 2>/dev/null | sort -rn | head -25
echo "== sensitive-ish tracked =="
git ls-files | grep -iE "recovered|dump|session|token|secret|\.key|_rsa|adb_keys|password" | head -20
