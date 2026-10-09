#include <linux/skbuff.h>
#include <linux/mm_types.h>
#include <linux/sched.h>
const unsigned long p[] = {
  sizeof(struct skb_shared_info),
  __builtin_offsetof(struct skb_shared_info, dataref),
  __builtin_offsetof(struct skb_shared_info, frags),
  __builtin_offsetof(struct skb_shared_info, destructor_arg),
  sizeof(struct skb_frag_struct),
  sizeof(struct mm_struct),
  SMP_CACHE_BYTES,
};
