#!/bin/bash
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq zstd >/dev/null 2>&1
echo "=== install vmlinux-to-elf ==="
pip3 install --break-system-packages -q vmlinux-to-elf 2>&1 | tail -3
echo "=== verify ==="
command -v vmlinux-to-elf && vmlinux-to-elf --version 2>&1 | head -1 || echo "vmlinux-to-elf NOT on PATH"
python3 - <<'PY'
try:
    import vmlinux_to_elf
    print("python import: vmlinux_to_elf OK")
except Exception as e:
    print("python import err:", e)
PY
command -v zstd && zstd --version
