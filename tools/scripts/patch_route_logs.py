p='src/core/main.c'
s=open(p).read()

a='''  if (futex_op(&f_pi_chain, FUTEX_LOCK_PI, 0, NULL, NULL, 0) != 0)
    pr_error("waiter lock chain errno=%d\\n", errno);
  atomic_store(&waiter_ready, 1);'''
b='''  { long r = futex_op(&f_pi_chain, FUTEX_LOCK_PI, 0, NULL, NULL, 0);
    pr_info("waiter: chain_lock ret=%ld errno=%d\\n", r, errno); }
  atomic_store(&waiter_ready, 1);'''
assert s.count(a)==1,('waiter chain',s.count(a)); s=s.replace(a,b,1)

a='''  atomic_store(&waiter_waiting, 1);
  futex_op(&f_wait, FUTEX_WAIT_REQUEUE_PI, 0, &timeout, &f_pi_target, 0);
  do_pselect_fake_lock_route();'''
b='''  atomic_store(&waiter_waiting, 1);
  pr_info("waiter: wrp_enter\\n");
  { long r = futex_op(&f_wait, FUTEX_WAIT_REQUEUE_PI, 0, &timeout, &f_pi_target, 0);
    pr_info("waiter: wrp_ret ret=%ld errno=%d\\n", r, errno); }
  do_pselect_fake_lock_route();'''
assert s.count(a)==1,('waiter wrp',s.count(a)); s=s.replace(a,b,1)

a='''  long lock_target = futex_op(&f_pi_target, FUTEX_LOCK_PI, 0, NULL, NULL, 0);
  if (lock_target != 0) pr_error("owner lock target errno=%d\\n", errno);
  while (!atomic_load(&waiter_ready)) usleep(1000);
  atomic_store(&owner_started, 1);
  futex_op(&f_pi_chain, FUTEX_LOCK_PI, 0, NULL, NULL, 0);
  atomic_store(&owner_chain_done, 1);'''
b='''  long lock_target = futex_op(&f_pi_target, FUTEX_LOCK_PI, 0, NULL, NULL, 0);
  pr_info("owner: target_lock ret=%ld errno=%d\\n", lock_target, errno);
  while (!atomic_load(&waiter_ready)) usleep(1000);
  atomic_store(&owner_started, 1);
  pr_info("owner: chain_lock_enter\\n");
  { long r = futex_op(&f_pi_chain, FUTEX_LOCK_PI, 0, NULL, NULL, 0);
    pr_info("owner: chain_lock_ret ret=%ld errno=%d\\n", r, errno); }
  atomic_store(&owner_chain_done, 1);'''
assert s.count(a)==1,('owner',s.count(a)); s=s.replace(a,b,1)

a='''  errno = 0;
  futex_op(&f_wait, FUTEX_CMP_REQUEUE_PI, 1, (void *)1, &f_pi_target, 0);
  while (!atomic_load(&route_done)) usleep(5000);'''
b='''  errno = 0;
  { long r = futex_op(&f_wait, FUTEX_CMP_REQUEUE_PI, 1, (void *)1, &f_pi_target, 0);
    pr_info("main: cmp_requeue ret=%ld errno=%d\\n", r, errno); }
  while (!atomic_load(&route_done)) usleep(5000);'''
assert s.count(a)==1,('cmp',s.count(a)); s=s.replace(a,b,1)

open(p,'w').write(s); print('route logs added')
