#!/bin/bash
cd "$HOME/ghostlock/src/g9700/kernel"
for f in probe_offsets.c probe_pipe.c probe_skb.c probe_mm.c probe_cred.c probe_misc.c probe_miscdev.c; do
  echo "########## $f ##########"
  cat -n "$f"
done
