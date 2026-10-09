#!/bin/bash
S=/root/ghostlock/src/g9700
R=/root/ghostlock/ghostlock-oneplus/src/core
echo "###### target.h: CFG_* (configfs_buffer) ######"
grep -nE '#define CFG_[A-Z_]+' $R/target.h
echo
echo "###### target.h: PIPE_* / cred / mm ######"
grep -nE '#define (PIPE_|CRED_|MM_|STRUCT_PAGE_|TASK_|ASHMEM_)' $R/target.h | head -40
echo
echo "###### source: struct configfs_buffer ######"
f=$(grep -rl "struct configfs_buffer {" $S/fs/ 2>/dev/null | head -1); echo "file: $f"
[ -n "$f" ] && awk '/^struct configfs_buffer {/,/^};/' "$f"
echo
echo "###### source: struct pipe_inode_info ######"
f=$(grep -rl "struct pipe_inode_info {" $S/include/ $S/fs/ 2>/dev/null | head -1); echo "file: $f"
[ -n "$f" ] && awk '/^struct pipe_inode_info {/,/^};/' "$f"
