#!/bin/bash
R=/root/ghostlock/ghostlock-oneplus
echo "=== files ==="
ls $R/src/core/
echo
echo "=== route_only_mode / --route / select_offsets occurrences ==="
grep -rn -e route_only_mode -e -- --route -e select_offsets -e run_route $R/src/ | head -40
