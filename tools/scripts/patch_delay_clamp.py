#!/usr/bin/env python3
"""patch_delay_clamp.py

Bug của mình: route clamp `if (delay_usec < 20000) delay_usec = 20000;` nên
PSELECT_ROUTE_DELAY_USEC=0 KHÔNG bao giờ thành 0 => mọi thử nghiệm "delay=0"
thực chất là 20 ms.  Clamp này chỉ cần cho route cũ dựa trên select (consumer
phải bắn sau khi T parked).  Với spin-park, consumer nên bắn NGAY để cửa sổ
clobber (IRQ ở EL0 khi T spin) nhỏ nhất.
"""
F = "/root/ghostlock/ghostlock-oneplus/src/core/fops.c"
s = open(F).read()
old = """    int delay_usec = route_delay_usec(attempt);
    if (delay_usec < 20000) delay_usec = 20000;"""
new = """    int delay_usec = route_delay_usec(attempt);
    /* Allow 0: with the spin-park hold the consumer must fire ASAP to keep the
     * clobber window (IRQ at EL0 while T spins) as small as possible.  (The old
     * 20 ms floor was needed only by the select-based route.) */
    if (delay_usec < 0) delay_usec = 0;"""
assert s.count(old) == 1, ("clamp", s.count(old))
s = s.replace(old, new, 1)
open(F, "w").write(s)
print("fops.c: delay floor 20000 -> 0 (env override now effective)")
