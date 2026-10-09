#!/usr/bin/env python3
import sys, os
CORE = os.path.expanduser("~/ghostlock/ghostlock-oneplus/src/core")
F = os.path.join(CORE, "main.c")
s = open(F, encoding="utf-8").read()

# 1. monitor thread + start it
anchor = "void run_main_route_threads(void) {"
mon = '''static void *route_monitor_thread(void *arg __attribute__((unused))) {
  pin_to_core(2);
  for (;;) {
    pr_info("MON t=%.0f waiter_rdy=%d wait_wait=%d own_s=%d own_d=%d route=%d "
            "go=%d cc=%d succ=%d psel=%d walk=%d\\n",
            timer_ms(),
            atomic_load(&waiter_ready), atomic_load(&waiter_waiting),
            atomic_load(&owner_started), atomic_load(&owner_chain_done),
            atomic_load(&route_done), atomic_load(&punch_consume_go),
            atomic_load(&consumer_calls), atomic_load(&consumer_success),
            atomic_load(&pselect_select_done), atomic_load(&pselect_walk_done));
    fsync(1);
    usleep(250000);
  }
  return NULL;
}

'''
if s.count(anchor) != 1:
    print("FAIL anchor %d" % s.count(anchor)); sys.exit(1)
s = s.replace(anchor, mon + anchor)

old = """  SYSCHK(pthread_create(&consumer, NULL, consumer_thread, NULL));"""
new = """  SYSCHK(pthread_create(&consumer, NULL, consumer_thread, NULL));
  if (env_flag("ROUTE_MON", 0)) {
    pthread_t mon;
    pthread_create(&mon, NULL, route_monitor_thread, NULL);
    pthread_detach(mon);
  }"""
if s.count(old) != 1:
    print("FAIL mon-start %d" % s.count(old)); sys.exit(1)
s = s.replace(old, new)

# 2. trace around the consumer's walk (sched_setattr)
old2 = """        atomic_fetch_add(&consumer_calls, 1);
        errno = 0;
        long sched_ret = env_flag("NO_WALK", 0)
                             ? 0
                             : sched_setattr_tid(tid, PSELECT_CONSUMER_NICE);
        int sched_errno = errno;"""
new2 = """        atomic_fetch_add(&consumer_calls, 1);
        pr_info("consumer: walk begin tid=%d\\n", tid); fsync(1);
        errno = 0;
        long sched_ret = env_flag("NO_WALK", 0)
                             ? 0
                             : sched_setattr_tid(tid, PSELECT_CONSUMER_NICE);
        int sched_errno = errno;
        pr_info("consumer: walk end ret=%ld errno=%d\\n", sched_ret, sched_errno); fsync(1);"""
if s.count(old2) != 1:
    print("FAIL consumer %d" % s.count(old2)); sys.exit(1)
s = s.replace(old2, new2)

open(F, "w", encoding="utf-8").write(s)
print("ok")
