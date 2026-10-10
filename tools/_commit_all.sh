#!/bin/bash
set -e
R=/mnt/e/Library/Desktop/ghostlock-beyond0q
cd "$R"
git add -A
echo "== staged (summary) =="
git status --short | head -60
echo "== untracked after =="
git status --short | grep '^??' | head
git commit -q -m "docs+adv: full session notes — RKP/Defex/verity/SELinux, persistence hunt, rc scan

- docs/KSU_ROOT_FINDINGS.md: sections 10-13 (Samsung protection stack, RKP internals
  from source, SELinux config, init rc boot-hook scan, persistence conclusion, bottom line).
- tools: diagnostic/setup scripts (mphelper, getid, readpersist/readparam, scan_rc,
  suidtest, rootmount, probe_root, runner.sh, build scripts).
- .gitignore: exclude full ROM source, vendored kernelsu, and build artifacts."
git log --oneline -6
