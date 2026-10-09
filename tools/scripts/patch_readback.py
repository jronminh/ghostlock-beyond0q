#!/usr/bin/env python3
# Readback oracle: after select() returns, set_fd_set() copies fds.res_in/res_out
# back into the user in/out bitmaps.  For shift=12 the waiter's task/lock live in
# res_in[3]/res_in[4] == in[3]/in[4], so printing them tells us whether the res_*
# paint actually landed (regardless of the PI walk).
p = 'src/core/fops.c'
s = open(p).read()
a = '''    pr_info("pselect post-select +%.0fms ret=%d walked=%d\\n",
            fops_elapsed_ms(&route_t0), ret, atomic_load(&pselect_walk_done));'''
b = '''    pr_info("pselect post-select +%.0fms ret=%d walked=%d\\n",
            fops_elapsed_ms(&route_t0), ret, atomic_load(&pselect_walk_done));
    pr_info("pselect RB in3=%016llx in4=%016llx out0=%016llx out1=%016llx "
            "(want task=%016zx lock=%016zx)\\n",
            (unsigned long long)fdset_get_word(&in, 3),
            (unsigned long long)fdset_get_word(&in, 4),
            (unsigned long long)fdset_get_word(&out, 0),
            (unsigned long long)fdset_get_word(&out, 1),
            fake_task, fake_lock);'''
assert s.count(a) == 1, s.count(a)
s = s.replace(a, b, 1)
open(p, 'w').write(s)
print('patched fops.c readback oracle')
