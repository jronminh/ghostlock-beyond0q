#!/bin/bash
cd ~/ghostlock/ghostlock-oneplus || exit 1
python3 - <<'PY'
p='src/core/fops.c'
s=open(p).read()

# 1) place lock/prio/deadline into the 'in' set words 0..2 so res_in mirrors them (byte 120+)
anchor = """  struct pselect_waiter_word *active_words = compact ? words_compact : words;"""
assert anchor in s
inject = """  /* 4.14 geometry (shift=8): waiter base = stack_fds+0x40, so lock/prio/deadline
   * land at global words 15/16/17 = res_in bytes 120..144, PAST the 120-byte
   * in/out/ex window. res_in = in & ready, so mirror them into the 'in' set
   * words 0..2 (bytes 0..24, harmless, below the waiter) and rely on res_in. */
  if (compact) {
    fdset_put_word(in, 0, fake_lock);
    fdset_put_word(in, 1, 0);
    fdset_put_word(in, 2, 0);
  }

"""
s = s.replace(anchor, inject + anchor)

# 2) arm the timerfd so the 'in' fds become ready (res_in gets filled)
anchor2 = """    int high_read = fcntl(block_fd, F_DUPFD, PSELECT_ROUTE_NFDS + 16);"""
assert anchor2 in s
arm = """    if (block_fd >= 0 && block_fd != pipefd[0]) {
      struct itimerspec its; memset(&its, 0, sizeof its);
      its.it_value.tv_nsec = 1000;
      syscall(SYS_timerfd_settime, block_fd, 0, &its, NULL);
    }
"""
s = s.replace(anchor2, arm + anchor2)
open(p,'w').write(s)
print("patched fops.c")
PY
# need itimerspec + SYS_timerfd_settime
grep -q 'sys/timerfd.h' src/core/fops.c || sed -i 's/#include <sys\/time.h>/#include <sys\/time.h>\n#include <sys\/timerfd.h>/' src/core/fops.c
grep -n 'res_in\|timerfd_settime\|fdset_put_word(in, 0, fake_lock)' src/core/fops.c | head
echo "=== rebuild ==="
SRC="src/core/main.c src/core/util.c src/core/slide.c src/core/fops.c src/core/pipe_physrw.c src/core/root.c src/core/miniadb.c src/core/umh_root.c"
aarch64-linux-gnu-gcc -O2 -w -include stddef.h -DKERNELSNITCH_THRESHOLD_MULT=30 \
  -Isrc/core -Isrc/devices -DTARGET_CONFIG_H='"target.h"' $SRC -o /tmp/ghostlock9 -static -pthread 2>&1 | grep -iE 'error' | head
cp -f /tmp/ghostlock9 /mnt/e/Library/Desktop/ghostlock/ghostlock9_a64
ls -la /mnt/e/Library/Desktop/ghostlock/ghostlock9_a64
