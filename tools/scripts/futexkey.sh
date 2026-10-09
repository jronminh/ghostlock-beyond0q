#!/bin/bash
K=/root/ghostlock/src/g9700
F=$K/kernel/futex.c
echo "=== get_futex_key signature ==="
grep -n 'get_futex_key' "$F" | head
echo
echo "=== private key setup (address/offset) ==="
awk '/get_futex_key\(/{f=1} f{print} /^}/{if(f)exit}' "$F" | grep -nE 'private|address|both|offset|PAGE_MASK|PAGE_SHIFT|key->|shared' | head -40
echo
echo "=== union futex_key ==="
awk '/^union futex_key \{/{f=1} f{print} /^};/{if(f)exit}' "$F"
