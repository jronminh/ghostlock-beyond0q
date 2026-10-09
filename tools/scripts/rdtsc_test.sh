#!/bin/bash
cd ~/ghostlock/ghostlock-oneplus || exit 1
echo "=== any '#define __ARM' in repo? ==="
grep -rn '#define __ARM\b\|D__ARM\|D__INTEL\|D__AMD' src tools Makefile 2>/dev/null | head
echo
echo "=== compile a tiny caller of rdtsc_begin (which arch branch?) ==="
cat > /tmp/t.c <<'EOF'
#include <stddef.h>
#include "timeutils.h"
size_t f(void){ return rdtsc_begin() + rdtsc_end(); }
EOF
aarch64-linux-gnu-gcc -I src/core/kernelsnitch -O2 -c /tmp/t.c -o /tmp/t.o 2>&1 | head
echo "rc=$?"
if [ -f /tmp/t.o ]; then
  echo "compiled OK; disasm:"; aarch64-linux-gnu-objdump -d /tmp/t.o 2>/dev/null | sed -n '6,20p'
fi
echo
echo "=== preprocessed: which rdtsc branch ==="
aarch64-linux-gnu-gcc -I src/core/kernelsnitch -E /tmp/t.c 2>/dev/null | grep -nE 'mfence|rdtsc|cntvct_el0|RDPRU' | head