#!/bin/bash
cd ~/ghostlock/ghostlock-oneplus
echo "=== rdtsc implementation (utils.h) ==="
grep -n 'rdtsc\|cntvct\|cntfrq\|pmccntr\|clock_gettime\|__builtin_readcyclecounter' src/core/kernelsnitch/utils.h
sed -n '/rdtsc_begin/,/^}/p' src/core/kernelsnitch/utils.h | head -40
echo
echo "=== find_collisions (300-345) ==="
sed -n '300,345p' src/core/kernelsnitch/kernelsnitch.h
echo
echo "=== threshold + constants ==="
grep -n 'THRESHOLD_MULT\|REPEAT_MEASUREMENT\|AVERAGE\|COARSE\|MULITPLE\|accept_times\|4096\|= 128' src/core/kernelsnitch/kernelsnitch.h | head -20
