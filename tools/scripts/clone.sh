#!/bin/bash
cd ~/ghostlock || exit 1
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq git >/dev/null 2>&1
export GIT_TERMINAL_PROMPT=0
echo "=== clone ghostlock-oneplus (baseline Android port) ==="
rm -rf ghostlock-oneplus && git clone --depth 1 -q https://github.com/JoinChang/ghostlock-oneplus.git 2>&1 | tail -2
echo "=== clone smt878u-ionstack-poc (closest: Samsung SD 4.19) ==="
rm -rf smt878u-ionstack-poc && git clone --depth 1 -q https://github.com/Wtrwx/smt878u-ionstack-poc.git 2>&1 | tail -2
echo "=== done ==="
ls -d ghostlock-oneplus smt878u-ionstack-poc 2>&1
echo "--- ghostlock tools ---"
ls ghostlock-oneplus/tools 2>&1
echo "--- smt878u tools ---"
ls smt878u-ionstack-poc/tools 2>&1
