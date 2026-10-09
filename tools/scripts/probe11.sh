#!/bin/bash
R=/root/ghostlock/ghostlock-oneplus/src
echo "=== uname_r entries ==="
grep -rn "uname_r" $R/devices/*.h $R/devices/*/*.h 2>/dev/null | head -40
echo
echo "=== waiter_compact entries ==="
grep -rn "waiter_compact" $R/devices/ 2>/dev/null
echo
echo "=== known_offsets table ==="
grep -rn "known_offsets" $R/ | head
