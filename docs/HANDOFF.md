# HANDOFF — GhostLock (CVE-2026-43499) port to Samsung SM-G970W / 4.14.190

Ngày: 2026-10-09. Mục tiêu: root máy S10 (SM-G970W, bootloader khóa cứng) bằng
GhostLock (root KHÔNG cần mở BL, tạm thời). Exploit nguồn: `JoinChang/ghostlock-oneplus`.

## 0. Tóm tắt trạng thái (đọc trước)
Exploit đã **port được cho 4.14 tới TẬN pha ghi (CFI / ashmem fops-redirect)**.
- ✅ Trigger CVE, leak `mm_struct`, heap spray, đặt waiter giả, fake_fops đúng hàm 4.14.
- ⚠️ **Blocker hiện tại:** `cfi write ret=-1 errno=22 (EINVAL)` — PI write chưa ghi được
  vào `ashmem_misc.fops` ⇒ không redirect. Và route signal `success` **flaky** (lúc 1 lúc 0).
- Đây là "last mile" cần nhiều vòng thử; mỗi lần thử = kernel panic → **reboot**.

## 1. Đường dẫn & công cụ
- adb: `E:\Library\Desktop\platform-tools-latest-windows\platform-tools\adb.exe`
- Scripts/phân tích (Windows): `E:\Library\Desktop\ghostlock\` (xem §6)
- Repo exploit (WSL, ĐÃ SỬA): `~/ghostlock/ghostlock-oneplus`
- Kernel source 4.14 (WSL): `~/ghostlock/src/g9700` (+ overlay `~/ghostlock/src/g970w`)
- Kallsyms/Image (WSL): `~/ghostlock/kernel/kallsyms_fixed.txt`, `~/ghostlock/kernel/Image`
- Parser kallsyms tự viết: `E:\Library\Desktop\ghostlock\kallsyms_parse.py` + `gen_target.py`
- Profile 4.14: `E:\Library\Desktop\ghostlock\beyond0q_4.14.h`; spec: `.../PORT_4.14.md`

## 2. Build (trong WSL Debian)
```
cd ~/ghostlock/ghostlock-oneplus
SRC="src/core/main.c src/core/util.c src/core/slide.c src/core/fops.c \
     src/core/pipe_physrw.c src/core/root.c src/core/miniadb.c src/core/umh_root.c"
aarch64-linux-gnu-gcc -O2 -w -include stddef.h -DKERNELSNITCH_THRESHOLD_MULT=30 \
  -Isrc/core -Isrc/devices -DTARGET_CONFIG_H='"target.h"' $SRC \
  -o /tmp/ghostlock -static -pthread
cp /tmp/ghostlock /mnt/e/Library/Desktop/ghostlock/ghostlock_a64
```
(app được build bằng gcc/glibc static; chạy được trên Android vì chỉ dùng syscall.)
Điều kiện tiên quyết đã làm sẵn: WSL có `aarch64-linux-gnu-gcc`, và
`~/ghostlock/src/g9700` đã `make prepare` (out/ có autoconf.h) — cần cho build probe.

## 3. Chạy trên máy
```
$adb = "E:\Library\Desktop\platform-tools-latest-windows\platform-tools\adb.exe"
& $adb push E:\Library\Desktop\ghostlock\ghostlock_a64 /data/local/tmp/ghostlock
& $adb shell chmod 755 /data/local/tmp/ghostlock
& $adb shell "PSELECT_SHIFT=8 timeout 90 /data/local/tmp/ghostlock"
# nếu panic/reboot: & $adb wait-for-device ; chờ ~30s máy lên lại
```
Đọc log: tìm `KernelSnitch bruteforce: state=4 found=1 mm_struct=...` (leak OK),
`cfi write ret=`, `errno=`.

## 4. Các FIX ĐÃ ÁP (đều suy từ source 4.14, KHÔNG tune mù)
| # | Vấn đề | Fix | File |
|---|---|---|---|
|1| **Memory layout** (OnePlus→4.14 VA_BITS=39) | `PAGE_OFFSET=0xffffffc000000000`, `KIMAGE_TEXT_BASE=0xffffff8008000000`, `IDENTITY_START/END`, `DIRECT_MAP_*`, `VMEMMAP_START` | `src/core/target.h` |
|2| **Symbol offsets** (28 hằng OnePlus→4.14) | INIT_TASK/CRED/…/ASHMEM_*/SLIDE_*/CONFIGFS_*/SPLICE/NOOP | `src/core/target.h` (từ `beyond0q_4.14.h`) |
|3| **`MM_STRUCT_SZ`** | `0x500`→`0x380` (stride slab `/proc/slabinfo`; cache align) | `src/core/common.h:52` |
|4| **pselect geometry** | `shift=8` (đo disasm) + đặt `lock/prio/deadline` qua **`res_in`** (vùng byte 120+, ngoài cửa sổ 120B) | `src/core/fops.c` (prepare_pselect_fdsets), timerfd arm |
|5| **fake waiter compact** | `pi_tree_entry@0x18` (không phải 0x28 của 6.x); task@0x30 lock@0x38 prio@0x40 deadline@0x48 | `src/core/util.c` (prepare_skb_payload) |
|6| **`struct cred`** | uid 4, securebits 0x24, caps 0x28, security 0x78 | `src/core/target.h` |
|7| **waiter lock off** | `WAITER_LOCK_OFF`/`FAKE_WAITER_LOCK_OFF` 0x58→0x38 | `src/core/target.h` |
|8| **`P0_KERNEL_PHYS_LOAD`** | 0xa8000000→0x80000000 (CHƯA CHẮC đúng; đang test) | `src/core/target.h:11` |
|9| **`ASHMEM_MISC_FOPS_OFF`** | `ashmem_misc (0x2bb1750)` → **`ashmem_misc+0x10` (0x2bb1760)** = field `.fops` (comment main.c:638) | `src/core/target.h:40` |
|10| stdout unbuffered (để bắt log trước panic) | `setvbuf(_IONBF)` trong main() | `src/core/main.c:850` |
|11| verbose/timing KernelSnitch (debug) | `REPEAT_MEASUREMENT 256`, `AVERAGE 16`, in `approx_time`/`heavy_time` | `src/core/kernelsnitch/kernelsnitch.h` |

LƯU Ý: `P0_KERNEL_PHYS_LOAD` / `KPHYS=` env **KHÔNG** đổi được `data_addr` — vì
`P0_DATA_ALIAS_CONST` là macro **compile-time**; muốn đổi phải sửa `target.h` + rebuild.

## 5. Vì sao biết đúng — dữ liệu đo được
- `linux_banner` khớp → kallsyms parser đúng (verify).
- Struct offsets: build-light (probe `offsetof`, dump .rodata) với ĐÚNG `config.gz` của máy.
- Leak `mm_struct` (state=4) chỉ thành công SAU khi sửa `IDENTITY_START` về linear map ⇒ chứng minh memory-layout là bug thật.
- `pselect cannot place lock global_word=15` (shift=8) ⇒ chứng minh cửa sổ 120B hụt 1 word; `res_in` khắc phục được.
- `cfi ... ioctl=0xffffff8009043f9c` = ASHMEM_IOCTL 4.14 của ta ⇒ chứng minh target.h fix ăn.

## 6. Audit BACKLOG (chưa sửa) — ưu tiên giảm dần
1. **SLIDE route geometry** (`SLIDE_PSELECT_WORD_SHIFT=2`, `SLIDE_USE_SELECT=1` trong target.h)
   — giống hệt pselect; nếu sai ⇒ **KASLR base sai** ⇒ mọi `data_addr()` sai. ĐO BẰNG DISASM
   (như đã làm pselect: SyS_select/SyS_pselect6 vs do_futex). **Ưu tiên #1, 0 reboot.**
2. `struct rt_mutex` (fake lock tại `LOCK_OFF`) — probe field `wait_lock/waiters/owner` 4.14.
3. `struct configfs_buffer` (`CFG_PAGE_OFF`=16, `CFG_NEEDS_READ_FILL_OFF`=80, `CFG_BIN_BUFFER_OFF`=88,
   `CFG_BIN_BUFFER_SIZE_OFF`=96, `CFG_CB_MAX_SIZE_OFF`=100) — probe 4.14.
4. `struct page` (`compound_head@0x08`, `page_type/slab_cache@0x30`) — probe.
5. `struct kmem_cache` / `off_kmalloc_caches` — probe (pipe/physrw).
6. `struct ashmem_area` — probe.
7. SELinux policy struct (reload/disable) — probe.
8. **`struct pipe_inode_info`** — 4.14 KHÁC HẲN 5.x: `nrbufs@0x40,curbuf@0x44,buffers@0x48,
   readers@0x4C,writers@0x50,files@0x54,waiting_writers@0x58,tmp_page@0x68,bufs@0x80,user@0x88,
   sizeof 0x90`. target.h dùng `head/tail/ring_size` (KHÔNG TỒN TẠI ở 4.14) ⇒ **PHẢI PORT CODE**
   (`pipe_physrw.c`) chứ không chỉ sửa số.
9. **`SKB_DATA_DELTA (-0xe80)`** — vị trí fake-page trong skb spray; **empirical**, khó suy source.
10. `pipe_buffer`: page@0 offset@8 len@0xC ops@0x10 flags@0x18 private@0x20 sizeof@0x28 (đã khớp).

## 7. Probe struct mẫu (cách rút offset từ source — 0 reboot)
```
cd ~/ghostlock/src/g9700
cat > kernel/probe_x.c <<'EOF'
#include <linux/sched.h>
const unsigned long p[] = { offsetof(TYPE,FIELD), ... };
EOF
export ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu-
make O=out CC=aarch64-linux-gnu-gcc kernel/probe_x.o
aarch64-linux-gnu-objcopy -O binary --only-section=.rodata out/kernel/probe_x.o /tmp/x.bin
python3 -c "import struct;d=open('/tmp/x.bin','rb').read();print([hex(struct.unpack_from('<Q',d,i)[0]) for i in range(0,len(d)//8*8,8)])"
```

## 8. Giới hạn đã biết (không phải bug)
- `MODULE_SIG_FORCE=y` ⇒ không load được `kernelsu.ko` chưa ký ⇒ trần là **root tạm**, không KernelSU.
- `CONFIG_CHECKPOINT_RESTORE` off ⇒ không dùng được vehicle `prctl(PR_SET_MM_MAP)`.
- `PANIC_ON_OOPS=y` ⇒ mỗi lần sai = reboot.
- Không có clang10/python2 ⇒ **không build full kernel** (chỉ build-light probe). Offset struct KHÔNG phụ thuộc compiler nên vẫn đúng.

## 9. Việc kế tiếp đề xuất
1. Audit **SLIDE geometry** (disasm) — có thể là mảnh chặn cuối (KASLR base).
2. Probe `struct rt_mutex` + `configfs_buffer`.
3. Chạy lặp để bắt 1 lần `success=1` rồi kiểm `ASHMEM_MISC_FOPS+0x10` có hết EINVAL không.
4. Nếu vẫn EINVAL → xem §6.2/6.3/6.8/6.9.

## 10. PHÁT HIỆN MỚI (audit #1 — SLIDE geometry) — nghi là nguyên nhân EINVAL
SLIDE leak (`slide.c`) dùng **`select()`** (`SLIDE_USE_SELECT` defined) → **CÙNG geometry với
main route** (cùng `SyS_select`/`core_sys_select`), nên cần **shift = 8** — NHƯNG `target.h`
để `SLIDE_PSELECT_WORD_SHIFT 2` (giá trị máy khác: "pselect vs select diff 16B"). Và
`prepare_slide_pselect_fdsets()` **CHƯA có fix `res_in`** (mình mới vá `prepare_pselect_fdsets`
của MAIN route). ⇒ `kaslr_base` (từ SLIDE leak) **không lấy được** ⇒ `data_addr()` (dùng
`kaslr_base + p0_alias_image_offset(...)`, xem `util.c:298,318`) **sai** ⇒ mọi địa chỉ ghi
(ASHMEM_MISC_FOPS, fake_fops, …) **sai** ⇒ `cfi write EINVAL`. **Rất khớp hiện tượng.**

### Cách sửa (làm tiếp)
1. `target.h`: `SLIDE_PSELECT_WORD_SHIFT 2 → 8` (giống `PSELECT_WAITER_WORD_SHIFT`).
   (hoặc set `-DSLIDE_PSELECT_WORD_SHIFT=8` khi build.)
2. `slide.c::prepare_slide_pselect_fdsets()`: thêm placement `lock/prio/deadline` qua `res_in`
   (copy cách đã làm ở `fops.c::prepare_pselect_fdsets`), và arm timerfd như `slide_pselect_stack_copy`.
3. Rebuild + chạy; xem log `slide boot_id_leaked_nfulnl_logger ... value=... stext=...`
   (đã có sẵn trong `slide_read_stext`) — nếu `stext` khớp base runtime thì SLIDE OK.
4. Sau đó `data_addr()` mới đúng ⇒ kỳ vọng `cfi write` hết EINVAL.

### Bằng chứng phụ
- Main route: `cfi ... ioctl=ffffff8009043f9c` = base compile-time + 0x1043F9C (KHÔNG có slide)
  ⇒ `kaslr_base` chưa được áp ⇒ đúng nghi vấn.
- `slide_read_stext()` đọc `/proc/sys/kernel/random/boot_id` sau khi ghi đè `sysctl_bootid`
  (SLIDE_RANDOM_BOOT_ID_DATA) ⇒ technique leak pointer qua boot_id.

### Ghi chú build nhanh (SLIDE shift qua -D)
```
aarch64-linux-gnu-gcc ... -DPSELECT_WAITER_WORD_SHIFT=8 -DSLIDE_PSELECT_WORD_SHIFT=8 ...
```
(nhớ vẫn phải patch res_in cho slide.c bằng tay — không phải macro).

### 10b. SLIDE dùng layout NESTED (6.x) — sai cho 4.14
`slide.c::prepare_slide_pselect_fdsets()` words[] = layout NESTED: task@word10, lock@word11,
wake_state@12, ww_ctx@13, pi0..2@5,6,7. Nhưng 4.14 là COMPACT: pi_tree@words 3,4,5; task@6;
lock@7; prio@8; deadline@9. ⇒ phải viết lại words[] theo compact (như `words_compact` ở
`fops.c`), KHÔNG dùng nested. Đây là lý do SLIDE leak sai.
Gợi ý words[] compact cho slide:
```
{0, SLIDE_LOGGERS_0_1, "tree_pc"}, {1,0,"tree_r"}, {2, SLIDE_RANDOM_BOOT_ID_DATA,"tree_l"},
{3, SLIDE_LOGGERS_0_1,"pi_pc"},    {4,0,"pi_r"},    {5, SLIDE_RANDOM_BOOT_ID_DATA,"pi_l"},
{6, SLIDE_INIT_TASK,"task"},       {7, fake_lock,"lock"},
{8, FAKE_WAITER_PRIO,"prio"},      {9, 0,"deadline"}
```
+ shift=8 + res_in cho lock/prio/deadline (copy từ fops.c) + arm timerfd.

## 11. Trạng thái cuối phiên (CHỐT)
- Đã áp ~11 fix (xem §4). Build mới nhất: `ghostlock13_a64`.
- **Blocker:** `cfi write EINVAL`; nghi #1 = SLIDE geometry (kaslr_base sai → data_addr sai), §10/10b.
- **Việc kế tiếp NGAY (0 reboot):** sửa SLIDE (shift=8 + compact words + res_in) → build → chạy →
  xem `slide boot_id_leaked_nfulnl_logger ... stext=...` có ra không.
- Nếu vẫn EINVAL: làm §6.2 (`struct rt_mutex`) và §6.3 (`configfs_buffer`).
- File này là nguồn sự thật; `PORT_4.14.md` là spec layout.
