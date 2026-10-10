#!/bin/bash
set -e
R=/mnt/e/Library/Desktop/ghostlock-beyond0q
cd "$R"
git add docs/KSU_ROOT_FINDINGS.md src/core/root.c src/core/fops.c \
        src/core/target.h src/core/common.h runner.sh
git status --short | head
git commit -q -m "feat(rw): exercise arbitrary-R/W capabilities (data side)

- root.c: repoint_task_cred() — configfs task-list walk, write task->real_cred
  and task->cred = canonical init_cred -> makes any process uid 0 (verified).
  (configfs_* primitives only; pipe_read64 is not set up in configfs-only mode.)
- fops.c: MP_PATH hook now also writes kptr_restrict=0 + core_pattern, and runs
  repoint_task_cred when CRED_TGID is set.
- target.h: CORE_PATTERN_OFF; common.h: repoint_task_cred decl.
- docs: R/W capability matrix (§6), code/rodata frontier (§7), repo changes (§8),
  correction that the real call_usermodehelper writes /data fine."
git log --oneline -3
