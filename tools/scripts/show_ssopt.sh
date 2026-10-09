#!/bin/bash
sed -n '/do_setsockopt_fake_lock_route(void) {/,/^}/p' /root/ghostlock/ghostlock-oneplus/src/core/fops.c
