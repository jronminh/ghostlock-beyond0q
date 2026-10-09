#!/bin/bash
G="$HOME/ghostlock/src/g9700"
echo "=== who uses system_unbound_wq ==="
grep -rn "system_unbound_wq" "$G/kernel" "$G/drivers/tty" "$G/fs" "$G/drivers" 2>/dev/null | grep -v "extern" | head -40
echo
echo "=== tty_buffer / flip schedule ==="
grep -rn -e "system_unbound_wq" -e "system_wq" "$G/drivers/tty/tty_buffer.c" | head
echo
echo "=== umh.c complete / exec_async ==="
grep -n -e "umh_complete" -e "complete(" -e "kernel_thread" "$G/kernel/umh.c" | head
