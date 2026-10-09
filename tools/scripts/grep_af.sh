#!/bin/bash
R=/root/ghostlock/ghostlock-oneplus/src/core
grep -nE 'APPENDED_FUTEXES|WAIT\(|#define WAIT|#define ID' $R/kernelsnitch/kernelsnitch.h $R/common.h | head -20
