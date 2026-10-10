#!/bin/bash
set -e
R=/mnt/e/Library/Desktop/ghostlock-beyond0q
cd "$R"
git add docs/KSU_ROOT_FINDINGS.md src/core/main.c src/core/target.h \
        src/core/fops.c src/primitives/rootshell.c \
        tools/mphelper.c tools/_build_mphelper.sh
echo "== staged =="
git status --short | head -30
git commit -q -m "feat(modprobe_path): root shell via modprobe_path + SELinux-off (verified on device)

- fops.c: MP_PATH hook writes modprobe_path (data_addr) + selinux_enforcing=0
- target.h: MODPROBE_PATH_OFF (0x29B93C0, from kallsyms_fixed.txt)
- main.c: KMI fallback android\$(getprop ro.build.version.release)
- rootshell.c: daemon handler diagnostics / read-line + sh -c
- tools/mphelper.c: modprobe helper (root daemon)
- docs/KSU_ROOT_FINDINGS.md: session findings (UMH write-cripple, cred wedge,
  gcc module build works, MODULE_SIG_FORCE blocks unsigned LKM, symbols table)"
git log --oneline -3
