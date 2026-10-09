#!/bin/bash
R=/root/ghostlock/ghostlock-oneplus/src/core
echo "###### __do_increase + __increase (thread futex wait) ######"
sed -n '105,160p' $R/kernelsnitch/kernelsnitch.h
echo
echo "###### nơi gọi __increase / pthread_detach / join ######"
grep -nE '__increase|pthread_detach|pthread_join|pthread_create' $R/kernelsnitch/kernelsnitch.h
echo
echo "###### KS_PAGE_SIZE / FUTEX_SZ/MMAP_SZ / MULITPLE / thread_cnt ######"
grep -nE '#define (KS_PAGE_SIZE|FUTEX_SZ|FUTEX_MMAP_SZ|MULITPLE|KSNITCH)' $R/kernelsnitch/*.h $R/common.h | head
