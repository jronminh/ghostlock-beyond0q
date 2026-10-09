#!/bin/bash
cd ~/ghostlock/src || exit 1
echo "=== original has these? (count) ==="
for s in "config XEN" "BEYOND0QLTE" "RKP" "KDP" "SAMSUNG_HYP" "RANDOMIZE_MODULE_REGION_FULL"; do
  printf "%-34s " "$s"
  grep -c "$s" orig/arch/arm64/Kconfig
done
echo
echo "=== orig BEYOND0 lines ==="
grep -n "BEYOND0" orig/arch/arm64/Kconfig | head
echo
echo "=== overlay Kconfig: lines / head / tail ==="
wc -l g970w/Kernel/arch/arm64/Kconfig
head -3 g970w/Kernel/arch/arm64/Kconfig
echo "..."
tail -6 g970w/Kernel/arch/arm64/Kconfig
echo
echo "=== orig: line of 'config XEN' and its tail head ==="
grep -n "^config XEN" orig/arch/arm64/Kconfig
echo
echo "=== diff original-tail (from config XEN) vs overlay ==="
L=$(grep -n "^config XEN" orig/arch/arm64/Kconfig | head -1 | cut -d: -f1)
tail -n +$L orig/arch/arm64/Kconfig > /tmp/orig_tail.txt
wc -l /tmp/orig_tail.txt g970w/Kernel/arch/arm64/Kconfig
diff /tmp/orig_tail.txt g970w/Kernel/arch/arm64/Kconfig | head -40
echo
echo "=== defconfig head ==="
head -15 g970w/Kernel/arch/arm64/configs/beyond0qlte_can_single_defconfig
