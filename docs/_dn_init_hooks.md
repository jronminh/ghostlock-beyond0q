# Nghiên cứu autostart/init — SM-G970W (Android 12, BL khoá)

## Kết luận
**Không có hook init data-only** để tự chạy payload root lúc boot. Muốn "init tự khởi động root"
phải sửa partition **ro** (`/`) = L3, và **`ro.boot.veritymode=enforcing` + fstab có `avb`** ⇒
sửa `/` gần như chắc **bootloop/wipe**.

## Bằng chứng
- init chỉ `import`/`exec` từ đường ro:
  - `/system/etc/init/hw/init.rc`: `import /init.environ.rc`, `/init.${ro.hardware}.rc`,
    `/init.container.rc` … (đều ở `/`, ro)
  - `/vendor/etc/init/hw/init.qcom.rc|init.target.rc|init.samsung.rc` (ro)
  - `init.rilcommon.rc`: `import /init.rilmptcp.rc`, `/init.rilmcpsd.rc` (ở `/`, **hiện thiếu file** — log boot báo)
- `/` = `/dev/root` **ext4 ro**; ghi thử `/init.dntest.rc` → `Read-only file system`.
- `/vendor`, `/product` = `dm-1`/`dm-2` (verity). `/dev/block/dm-0` tồn tại.
- fstab: `system / ext4 ro,barrier=1,discard wait,slotselect,avb`.
- `ro.boot.veritymode=enforcing`, `ro.boot.flash.locked=1`, `ro.boot.verifiedbootstate=green`.
- Các partition **rw**: `/cache` (0770 system:cache), `/efs`, `/omr`, `/carrier`, `/keydata`,
  `/keyrefuge`, `/mnt/vendor/persist`, `/data`. **Không** rc nào `import`/`exec`/service trỏ vào đây.
- Không có `exec` nào chạy binary/script từ `/data`.
- `/prism` **không tồn tại** (dù `scs.rc` có `import /prism/etc/init/init.rc`).

## Các mức rủi ro
| Mức | Cách | Hệ quả |
|---|---|---|
| L1 | adb (`persist.adb.tcp.port`) hoặc app `BOOT_COMPLETED` → **re-exploit mỗi boot** | an toàn, gỡ sạch |
| L2 | + `su` daemon / root adbd | như root hệ thống (mỗi boot) |
| L3 | `mount -o remount,rw /` + thêm `/init.rilmptcp.rc` (init sẵn import) | **verity enforcing** → nguy cơ bootloop/wipe; có thể đốt Knox |
| L4 | ghi `boot`/`init_boot` | AVB reject → gần như chắc brick; cứu bằng Odin stock |

## Ghi chú
- `import /init.${ro.hardware}.rc` — hardware là read-only, không đổi được.
- Inject vào init đang chạy (`/proc/1/mem`, userspace không bị KDP) là RAM-only ⇒ reboot mất,
  nên không giải quyết "tự khởi động"; chỉ hữu ích trong phiên.
