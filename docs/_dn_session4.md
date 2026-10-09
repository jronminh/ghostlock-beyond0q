# GhostLock SM-G970W — Phiên 4 (hướng B) — ghi chú

Mục tiêu không đổi: root tạm SM-G970W (S10e, 4.14.190, BL khoá) qua port GhostLock,
không mở bootloader, không KernelSU (MODULE_SIG_FORCE).

## Kết quả then chốt
- **fops redirect (mode-4) + configfs arbitrary R/W: OK** (như phiên 3).
- **UMH (`call_usermodehelper`) chạy `/data/local/tmp/a/e --umh` bằng uid 0 THẬT**:
  `umh: result complete=1 retval=0`, `umh_uid_0_euid_0_gid_0`, `/sys/fs/selinux/enforce='0'`.
- Hạn chế UMH: tiến trình do kernel sinh **không có keyring của /data (FBE)** nên
  `open()` trong `/data/local/tmp` có thể trả `ENOKEY (126)` ⇒ không dùng được làm root shell.

## Vì sao (B) từng tường ở `page_base`
`pipe_physrw.c` cần `page_base` là vùng kmalloc-2k slab. Hướng B **bỏ hẳn pipe**: cho
physrw chạy trên chính primitive configfs (`CFG_PHYSRW=1`, mặc định) — configfs read/write
thực chất là arbitrary R/W **không giới hạn độ dài** (đọc: `simple_read_from_buffer(...,buffer->page,buffer->count)`;
ghi: `configfs_write_bin_file` → `simple_write_to_buffer(bin_buffer,...)`, `cb_max_size=0`).

## Hằng số/offset đã sửa (đo bằng probe trên chính header/config máy)
- `struct page`: `slab_cache=0x30`, `compound_head=0x20`, `page_type=0x18` (target.h cũ 0x08/0x08/0x30 SAI).
- kmalloc: enum chỉ `NORMAL=0, RECLAIM=1, DMA=2` (ZONE_DMA=y), **không có cgroup**; pipe_buffer (GFP_KERNEL_ACCOUNT) → kmalloc-2k NORMAL (index 11).
- `struct kmem_cache`: cpu_slab 0x00, size 0x18, oo 0x28, node 0x140; `kmem_cache_cpu`: page 0x10, partial 0x18.
- Workqueue 4.14 (từ DWARF của OSRC): `wq->dfl_pwq=0xa8`; pwq: pool 0x00, wq 0x08, work_color 0x10, refcnt 0x18, nr_in_flight 0x1c, nr_active 0x58, max_active 0x5c; worker_pool: worklist 0x20, nr_idle 0x34; WORK_NR_COLORS=15.
- `struct subprocess_info` 4.14: work 32B, tổng **96** (không phải 112).
- **`selinux_enforcing` = offset `0x02DC8CE8`** (không phải 0x02DC8CC8 = `selinux_state`). `enforcing_enabled()` của Samsung đọc biến global `int selinux_enforcing`.
- **task_struct (máy này lệch +8 so với OSRC)**: `real_cred=0x850, cred=0x858, comm=0x860` (pid/tgid/tasks giữ nguyên: 0x6A8/0x6AC/0x5A8).

Công cụ đo: `_dn_kmem.sh`, `_dn_umhprobe.sh`, `_dn_wqcompile.sh` + `_dn_wqdump.py`, `_dn_tcprobe.sh`.

## Cờ mới (mặc định hướng B)
- `CFG_PHYSRW=1` (default): physrw qua configfs, bỏ qua pipe slab.
- `SKIP_UMH=1`: bỏ UMH, đi thẳng nhánh patch cred (`install_android_root`).
- `SKIP_CRED=1`: bỏ nhánh cred (chỉ test UMH).
- `FORCE_REDIRECT=1`: vẫn làm fops redirect dù SELinux đã tắt (tiện test, khỏi reboot).

## An toàn (đã sửa)
- Dời UMH scratch vào **trong trang 4 KB** (`UMH_WORK_OFF=0x400`, `UMH_DATA_OFF=0x480`) — trước đây ghi ~500B ra ngoài trang (trang vật lý bất kỳ).
- Dời target test CFI vào trong trang (`binwrite_target = page_base+0x700`) — trước là `page_base-0x680`.
- Không đụng bootloader/partition/flash ở mọi bước.

## Lệnh chạy
```
# build
wsl -e bash /mnt/e/Library/Desktop/ghostlock/build14.sh /tmp/ghostlockXX
# push + slide
adb push ghostlockXX_a64 /data/local/tmp/ghostlockXX
adb shell "chmod 755 /data/local/tmp/ghostlockXX; cp -f /data/local/tmp/ghostlockXX /data/local/tmp/a/e; chmod 755 /data/local/tmp/a/e"
adb shell "cd /data/local/tmp && timeout 40 ./slideprobe > sp.log 2>&1; grep -a -m1 bd4 sp.log"   # slide=(IP-0xffffff8008000000)-0x3bd4
# run (nhánh cred + daemon root shell)
adb shell "cd /data/local/tmp && nohup sh -c 'ONLY_FOPS=1 SKIP_UMH=1 SSOPT_EMPTY=1 SSOPT_FAKE_TASK=1 SSOPT_PEEK=1 SSOPT_HOLD=0 SSOPT_OWNER0=0 PSELECT_ROUTE_DELAY_USEC=0 ROUTE_SETSOCKOPT=1 SLIDE=0x... timeout 150 ./ghostlockXX > gl.log 2>&1' >/dev/null 2>&1 & echo STARTED"
```
Root shell (khi cred patch chạy): `adb forward tcp:2223 tcp:2223; nc 127.0.0.1 2223`.

## Dump panic (không cần root)
`adb shell` ở group `log` ⇒ đọc được `/data/log/dumpstate_lastkmsg_*.gz`;
`wsl python3 kp_scan.py <dump>` / `_dn_faultB14.py` / `_dn_block.py`.

## Còn mở
- Nhánh cred: xác nhận ghi được vào `cred` (KDP có thể chặn) + làm root shell dùng được.
- Walk flaky ~50% (`rt_mutex_adjust_prio_chain`) — vấn đề riêng, cần retry/vá.

## ROOT CAUSE cái "ngẫu nhiên" (đã chốt bằng monitor thread)
Monitor (in mỗi 250 ms, pin core 2) + trace quanh `sched_setattr` cho thấy lần máy reset:

```
MON t=4124 ... own_s=1 own_d=0 route=0 go=1 cc=1 succ=0 psel=1 walk=0
waiter: wrp_ret ret=-1 errno=110
consumer: walk begin tid=12593        <-- KHÔNG có "walk end"
<reset>
```

⇒ **Luồng chính KHÔNG kẹt** (configfs read chạy trước/sau fork OK, tìm đúng task con).
Máy reset vì **`sched_setattr_tid()` trong `consumer_thread`** — tức `rt_mutex_adjust_prio_chain`
— bắt đầu (`cc=1`) mà không kết thúc (`succ=0 walk=0`) ⇒ watchdog `sec_debug_hw_reset`.

Trong `kernel/locking/rtmutex.c:rt_mutex_adjust_prio_chain` (4.14) chỉ có **2 vòng vô hạn**:
1. `[5]` `retry`: `raw_spin_trylock(&lock->wait_lock)` fail mãi → `cpu_relax(); goto retry;` (không bound).
2. `[7]/[11]` thao tác **rb-tree trên cây giả của ta** (`rt_mutex_dequeue/enqueue`, `rb_erase_cached`):
   cây cyclic ⇒ `rb_erase`/`____rb_erase_color` quay vô hạn.
(`goto again` có bound bởi `max_lock_depth`.)

⇒ ~50% phụ thuộc **trạng thái cây RB giả** tại thời điểm walk (race với timing/IRQ). Khi dice
rơi đúng thì walk thoát (B7/B14/B17) và chạy trọn vẹn.

*   `SSOPT_OWNER0=1` (walk dừng sớm ở `[9]`) **vẫn stall** → không phải riêng `[11]`; walk nói chung vẫn nguy.

**Hướng vá:** ép `[11]` dùng `pi_waiters` **cây rỗng hợp lệ** (root=NULL,`rb_leftmost`=NULL) để
`dequeue_pi/enqueue_pi` thành no-op; hiệu chỉnh `WAITER_LO14` để `[7]` đi đúng `RB_EMPTY_NODE`
(đọc `x25` từ panic khi sai); thử combo `SSOPT_OWNER0`/`SSOPT_FAKE_TASK`/`RBROOT_OFF`/`RBLEFT_OFF`.
Lưu ý: bản thân đường ghi mode-4 cần `rb_erase` trên cây giả (không thể rỗng hoá hoàn toàn).

### Bằng chứng dump (chốt hơn)
Panic kiểu A từ dump SCAN2/B21:
```
pc : rb_erase_cached+0x20/0x3f8
lr : rt_mutex_adjust_prio_chain+0x310/0x830
x25: ffffff8011c9bd10   <-- địa chỉ waiter (leak)
x0 : ffffff8011c9bd10   <-- node truyền vào rb_erase (== waiter) => offset ĐÚNG
x9 : 64e716f4e0b07ba4   <-- địa chỉ fault (rb_right rác)
```
low14(x25) = `0x3d10` = `WAITER_LO14` ⇒ leak/paint đúng offset. Vậy `RB_EMPTY_NODE` mất do
**giá trị `parent_color` bị đè** (IRQ ở EL0), không phải offset.

### `SSOPT_HOLD`
- `HOLD=0` (lệnh bàn giao dùng): T **spin ở EL0** ⇒ IRQ đè paint ⇒ ~50% `rb_erase_cached` rác.
- `HOLD=1` (mặc định): T block trong `select(64, empty-pipe, 1s)` (trong kernel) — nhưng **thử vẫn fail**;
  cần điều tra thêm (có thể frame select/frame thoát vẫn đè, hoặc walk vào state khác).
Lệnh bàn giao §3 truyền `SSOPT_HOLD=0` — nghi vấn: đổi thành `HOLD=1` + timing khác.
