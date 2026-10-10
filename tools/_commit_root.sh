#!/bin/bash
set -e
R=/mnt/e/Library/Desktop/ghostlock-beyond0q
cd "$R"
git add docs/KSU_ROOT_FINDINGS.md tools/mphelper.c
git status --short | head
git commit -q -m "feat(mphelper): file-driven root command runner -> usable full root

modprobe helper now runs a loop: read /data/local/tmp/rcmd -> 'sh -c' as root
-> output /data/local/tmp/rout. Verified: 'id' => uid=0(root) gid=0(root)
groups=0(root) context=u:r:kernel:s0; root can list /data/adb (shell EACCES).
Socket I/O in the kernel-spawned context was unreliable, so the channel is
file-based. docs: section 9."
git log --oneline -3
