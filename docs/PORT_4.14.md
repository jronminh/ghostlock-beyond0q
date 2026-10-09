# PORT 4.14 — GhostLock cho Samsung SM-G970W (beyond0qltecs, SD855)

Namespace: mọi giá trị dưới đây **suy từ source 4.14.190 của chính máy** (G9700+G970W OSRC,
build-light với `config.gz` thật), KHÔNG tune mù.

## 1. Memory layout (VA_BITS=39, PAGE_SHIFT=12)  — từ arch/arm64/include/asm/memory.h
```
VA_START     = ~0 - (1<<VA_BITS)   + 1 = 0xffffff8000000000
PAGE_OFFSET  = ~0 - (1<<(VA_BITS-1)) + 1 = 0xffffffc000000000   # LINEAR MAP
MODULES_VADDR= VA_START (+KASAN=0)      = 0xffffff8000000000
MODULES_END  = +SZ_128M                 = 0xffffff8008000000
KIMAGE_VADDR = MODULES_END              = 0xffffff8008000000   # = _text base ✅ (khớp tool)
VMEMMAP_SIZE = 1<<(VA_BITS-PAGE_SHIFT-1+STRUCT_PAGE_MAX_SHIFT=6) = 0x100000000 (4GB)
VMEMMAP_START= PAGE_OFFSET - VMEMMAP_SIZE = 0xffffffbf00000000
DIRECT_MAP   = [PAGE_OFFSET, 2^64)        = [0xffffffc000000000, top)
STRUCT_PAGE_SIZE = 0x40
```
target.h hiện là của OnePlus → SAI các mục: KIMAGE_TEXT_BASE, P0_PAGE_OFFSET,
KERNELSNITCH_IDENTITY_*, DIRECT_MAP_BASE/END, VMEMMAP_START.

## 2. Symbol offsets  — từ kallsyms (parser tự viết, verify `linux_banner`)
Xem `beyond0q_4.14.h` (đầy đủ): init_task/init_cred/selinux_state/... ashmem/configfs/splice/
slide(nfulnl_logger,loggers,sysctl_bootid)/system_unbound_wq/call_usermodehelper_exec_work.

## 3. Struct offsets  — build probe từ source+config
task_struct: pid 0x6A8, comm 0x858, cred 0x850, tasks 0x5A8, prio 0xA8, normal_prio 0xB0,
  sched_task_group 0x400, pi_lock 0x91C, pi_waiters 0x928, pi_top_task 0x938,
  pi_blocked_on 0x940, mm 0x5F8, real_parent 0x6B0, atomic_flags 0x670, seccomp 0x8F8,
  thread 0xB70, sizeof 0xF80
mm_struct: owner 0x328, sizeof(cache, `/proc/slabinfo`) = 0x380, order 3 (8 pages)
file_operations: llseek 0x8, read 0x10, write 0x18, read_iter 0x20, write_iter 0x28,
  ioctl 0x48, compat_ioctl 0x50, mmap 0x58, open 0x60, release 0x70, splice_read 0xB8, show_fdinfo 0xD0

## 4. rt_mutex_waiter (kernel/locking/rtmutex_common.h)
tree_entry@0x00, pi_tree_entry@0x18, task@0x30, lock@0x38, prio@0x40, deadline@0x48
=> 10 words = COMPACT. task=word6, lock=word7.  (`waiter_compact=1`)

## 5. pselect geometry  — disasm Image
do_futex frame 0x210 (stp-96 + sub#0x1b0), rt_waiter @ sp+0xd0  (confirmed: rt_mutex_init_waiter(x0=sp+0xd0))
SyS_futex frame 0x70 ; core_sys_select frame 0x1c0, stack_fds @ sp+0x50 ; SyS_select frame 0x80
SyS_* gọi thẳng do_futex / core_sys_select (no intermediate) ; dispatch cùng depth
=> waiter = S0-0x1b0 ; stack_fds = S0-0x1f0  =>  **shift = 8**
⚠️ Cửa sổ select(): NFDS max = 320 (kernel dùng stack khi n<=320; >320 → kmalloc) => control = 120 byte.
   waiter @ stack_fds+0x40 => lock @ byte 120 = hụt ĐÚNG 1 byte => pselect route (NFDS=320) BẤT KHẢ
   trừ khi geometry thật là +0x38 (shift=7). Đây là điểm cần chốt.
   => Cần SỬA CÁCH ĐẶT (byte-precise) hoặc đổi vehicle.

## 6. KernelSnitch (leak)  — phân tích theo source
- futex_hash: `jhash2((u32*)key, off(both.offset)/4, key->both.offset)` = y hệt kernel.
- key layout + get_futex_key: khớp.
- futex_hashsize = 256*num_possible_cpus = 2048 ; khớp.
- rdtsc = cntvct_el0 (common.h define __ARM).
- IDENTITY range PHẢI là linear map (0xffffffc000000000), KHÔNG phải 0xffffff8000000000.
- futex_wake(val=0): bucket RỖNG → về sớm (nhanh); bucket có waiter → đi tới entry khớp.
  ⇒ collision đúng = address cùng bucket target, KHÔNG có waiter ⇒ đi hết bucket (chậm).
  ⚠️ Trên Android nhiều process, nhiều bucket khác cũng nặng ⇒ tiêu chí `> baseline*MULT` bắt NHẦM.
  => CẦN SỬA LOGIC: chọn address có thời gian khớp với "full-walk của bucket target"
     (hoặc làm bucket target áp đảo), KHÔNG so baseline*MULT.

## 7. Còn thiếu / chưa suy được
- P0_KERNEL_PHYS_LOAD (SD855): địa chỉ vật lý kernel load — cần /proc/iomem (khi có root) hoặc DT.
- SKB_DATA_DELTA (-0xe80): layout sk_buff frag của 4.14 — cần kiểm theo source.
- Pipe/physrw offsets (struct pipe_buffer, struct page, kmalloc caches): suy từ source 4.14.
