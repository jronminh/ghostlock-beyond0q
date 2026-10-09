#!/usr/bin/env python3
"""
geom_scan.py - offline (pure disassembly) search for syscalls whose userspace->
kernel-stack copy can reach the residual rt_mutex_waiter fields.

Waiter (fixed by do_futex):  rt_waiter = SP0 - 0x1b0  (0x50 bytes)
    task @ +0x30 = SP0-0x180      lock @ +0x38 = SP0-0x178
(SP0 = sp on entry to the syscall wrapper; same for 32-bit and 64-bit on arm64.)

For every syscall wrapper we walk the call graph, accumulate the stack frame,
and record the SP0-relative offset of each user->stack copy destination.  A
destination covering [0x178,0x190) can paint task+lock.

Sinks (dst register):
  copy_from_user/_copy_from_user/raw_copy_from_user   x0
  move_addr_to_kernel                                 x2
  copy_msghdr_from_user/get_compat_msghdr             x0
  import_iovec/__import_iovec                         x4 (the iov out ptr)
  rw_copy_check_uvector                               x4
"""
import re, subprocess, sys, bisect

BASE = 0xffffff8008000000
IMG = '/root/ghostlock/kernel/Image'
KS  = '/root/ghostlock/kernel/kallsyms_fixed.txt'

_syms = []
for line in open(KS):
    m = re.match(r'([0-9a-f]+)\s+(\w)\s+(\S+)', line)
    if m:
        _syms.append((int(m.group(1), 16), m.group(2), m.group(3)))
_syms.sort()
_addrs = [a for a, _, _ in _syms]
def name_of(a):
    i = bisect.bisect_right(_addrs, a) - 1
    return _syms[i][2] if i >= 0 else '?'
def func_end(a):
    i = bisect.bisect_right(_addrs, a)
    return _syms[i][0] - a if i < len(_syms) else 0x400

SINKS = {
 'copy_from_user': 0, '_copy_from_user': 0, '__copy_from_user': 0,
 'raw_copy_from_user': 0, '__arch_copy_from_user': 0,
 'move_addr_to_kernel': 2,
 'copy_msghdr_from_user': 0, 'get_compat_msghdr': 0,
 'import_iovec': 4, '__import_iovec': 4, 'rw_copy_check_uvector': 4,
}
# map sink function address -> (name, dstreg)
_sink_by_addr = {}
for a, t, n in _syms:
    if n in SINKS:
        _sink_by_addr.setdefault(a, (n, SINKS[n]))

_insn_cache = {}
def disasm(a):
    if a in _insn_cache:
        return _insn_cache[a]
    ln = max(func_end(a), 0x40)
    out = subprocess.run(['aarch64-linux-gnu-objdump', '-D', '-b', 'binary',
                          '-m', 'aarch64', '--adjust-vma=' + hex(BASE), IMG,
                          '--start-address=' + hex(a),
                          '--stop-address=' + hex(a + ln)],
                         capture_output=True, text=True).stdout or ''
    ins = []
    for l in out.splitlines():
        m = re.match(r'\s*([0-9a-f]+):\s+[0-9a-f ]+\t(\S+)\s*(.*)', l)
        if m:
            ins.append((int(m.group(1), 16), m.group(2), m.group(3)))
    _insn_cache[a] = ins
    return ins

def frame_and_fp(ins):
    fr = 0; fpoff = None; n = 0
    for a, m, o in ins:
        if m == 'sub' and re.match(r'sp, sp, #', o):
            fr += int(re.search(r'#(0x[0-9a-f]+|\d+)', o).group(1), 16); n += 1
        elif m in ('stp', 'str') and re.search(r'\[sp, #-(0x[0-9a-f]+|\d+)\]!', o):
            fr += int(re.search(r'#-(0x[0-9a-f]+|\d+)', o).group(1), 16); n += 1
        elif m == 'add' and re.match(r'x29, sp, #', o) and fpoff is None:
            fpoff = int(re.search(r'#(0x[0-9a-f]+|\d+)', o).group(1), 16)
        if n >= 6:
            break
    return fr, fpoff

def local_of(ins, idx, reg):
    """value (sp-relative offset) of `reg` at ins[idx], or None."""
    for j in range(idx - 1, max(-1, idx - 12), -1):
        _, m, o = ins[j]
        m1 = re.match(re.escape(reg) + r', sp, #(0x[0-9a-f]+|\d+)$', o)
        if m1:
            return int(m1.group(1), 16)
        if m == 'mov' and re.match(re.escape(reg) + r', sp$', o):
            return 0
        if (m in ('add','sub') and re.match(re.escape(reg) + r', x29, #', o)):
            return None  # handled by caller with fpoff
    return None

results = {}  # name -> set of dst offsets
def walk2(a, off, depth, seen, name):
    if depth > 4 or a in seen:
        return
    seen = seen | {a}
    ins = disasm(a)
    fr, fpoff = frame_and_fp(ins)
    curoff = off + fr
    for i, (ia, m, o) in enumerate(ins):
        if m != 'bl':
            continue
        t = re.search(r'0x([0-9a-f]+)', o)
        if not t:
            continue
        tgt = int(t.group(1), 16)   # VA
        if tgt in _sink_by_addr:
            sn, dr = _sink_by_addr[tgt]
            reg = {0:'x0',1:'x1',2:'x2',3:'x3',4:'x4',5:'x5'}[dr]
            off2 = local_of(ins, i, reg)
            if off2 is None and fpoff is not None:
                for j in range(i-1, max(-1,i-12), -1):
                    mm = re.match(re.escape(reg) + r', x29, #(0x[0-9a-f]+|\d+)$', ins[j][2])
                    if mm:
                        off2 = fpoff - int(mm.group(1),16); break
            if off2 is not None:
                results.setdefault(name, []).append((curoff - off2, sn))
        elif 0 < (tgt - BASE) < 0x2000000:
            walk2(tgt, curoff, depth + 1, seen, name)

entries = []
seen_addr = set()
for a, t, n in _syms:
    if (n.startswith('SyS_') or n.startswith('compat_SyS_')) and a not in seen_addr:
        seen_addr.add(a); entries.append((a, n))
print('syscall entries:', len(entries))

WAITER_TASK = 0x180   # SP0 - 0x180
WAITER_LOCK = 0x178   # SP0 - 0x178
rows = []
for a, n in entries:
    results.pop(n, None)
    walk2(a, 0, 0, set(), n)
    dsts = results.get(n, [])
    for off, sn in dsts:
        if off is None:
            continue
        # a destination buffer of unknown length; report its start
        rows.append((n, off, sn))

# feasibility: a copy dest starting in [0x168, 0x190) can cover task/lock
def feas(off):
    return 0x168 <= off <= 0x190

rows.sort(key=lambda r: (not feas(r[1]), r[0]))
print('%-42s %-8s %-22s %s' % ('syscall', 'off(SP0-)', 'sink', 'feasible(task/lock)'))
for n, off, sn in rows:
    print('%-42s -0x%04x  %-22s %s' % (n, off, sn, 'YES' if feas(off) else ''))
