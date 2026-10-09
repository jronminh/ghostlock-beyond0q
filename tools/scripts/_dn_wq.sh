#!/bin/bash
G="$HOME/ghostlock/src/g9700"
echo "=== kernel version ==="
grep -E '^(VERSION|PATCHLEVEL|SUBLEVEL)' "$G/Makefile" | head
echo
echo "=== workqueue_struct ==="
awk '/^struct workqueue_struct \{/{f=1} f{print} f&&/^\};/{exit}' "$G/kernel/workqueue.c"
echo
echo "=== worker_pool ==="
awk '/^struct worker_pool \{/{f=1} f{print} f&&/^\};/{exit}' "$G/kernel/workqueue.c"
