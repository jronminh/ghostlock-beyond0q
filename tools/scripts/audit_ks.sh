#!/bin/bash
R=/root/ghostlock/ghostlock-oneplus/src/core
echo "###### kernelsnitch_cleanup (full) ######"
sed -n '384,430p' $R/kernelsnitch/kernelsnitch.h
echo
echo "###### kernelsnitch thread func + stop flag + join ######"
grep -nE 'pthread_create|pthread_join|pthread_cancel|stop|atomic_store|shutdown|pthread_exit|futex' $R/kernelsnitch/kernelsnitch.h | head -50
echo
echo "###### struct kernelsnitch_shared_state (thread mgmt) ######"
sed -n '/struct kernelsnitch_shared_state {/,/^};/p' $R/kernelsnitch/kernelsnitch.h
