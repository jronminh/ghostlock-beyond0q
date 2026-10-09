#!/usr/bin/env python3
"""kallsyms parser v5 - raw arm64 Image, 4.14 BASE_RELATIVE.
Self-locating; offsets table anchored on linux_banner -> 'Linux version' string."""
import struct, sys, array

IMG = sys.argv[1] if len(sys.argv) > 1 else 'kernel/Image'
out = sys.argv[2] if len(sys.argv) > 2 else 'kernel/kallsyms_fixed.txt'
data = open(IMG, 'rb').read()
N = len(data)
u16arr = array.array('H'); u16arr.frombytes(data[: (N//2)*2])
s32arr = array.array('i'); s32arr.frombytes(data[: (N//4)*4])

def u16(o): return struct.unpack_from('<H', data, o)[0]
def s32(o): return struct.unpack_from('<i', data, o)[0]
def u64(o): return struct.unpack_from('<Q', data, o)[0]

def tlen(s, lim):
    i = s
    while i < lim:
        if data[i] == 0:
            return i - s
        if not (32 <= data[i] < 127):
            return None
        i += 1
    return None

# ---- 1. token_index/table ----
found = None
for zi, v0 in enumerate(u16arr):
    if v0 != 0:
        continue
    p = 2*zi
    if p + 512 > N or data[p-1] != 0:
        continue
    prev = 0; asc = True
    for i in range(1, 256):
        v = u16arr[zi+i]
        if v <= prev:
            asc = False; break
        prev = v
    if not asc:
        continue
    tmax = u16arr[zi+255]
    if not (400 <= tmax <= 4000):
        continue
    for delta in range(1, 400):
        S = p - tmax - delta
        if S < 0 or p - S > 4096:
            break
        good = True; toks = []
        for i in range(256):
            st = S + u16arr[zi+i]
            if st >= p or (i > 0 and data[st-1] != 0):
                good = False; break
            L = tlen(st, p)
            if L is None:
                good = False; break
            if i < 255 and st + L != S + u16arr[zi+i+1] - 1:
                good = False; break
            toks.append(bytes(data[st:st+L]))
        if good and len(set(toks)) >= 200:
            found = (p, S); break
    if found:
        break
if not found:
    print("FAIL token_index"); sys.exit(1)
p_ti, S_tt = found
print("[1] token_table @0x%x  token_index @0x%x" % (S_tt, p_ti))

def tok(i):
    st = S_tt + u16(p_ti + 2*i)
    return data[st:st+tlen(st, p_ti)].decode('latin1')

# ---- 2. markers ----
markers_start = mvals = None
for ms in range(S_tt - 8, max(0, S_tt - 300000), -8):
    if u64(ms) != 0:
        continue
    vals = [0]; o = ms + 8
    while o < S_tt and len(vals) < 5000:
        v = u64(o)
        if v <= vals[-1] or v > 400_000_000:
            break
        vals.append(v); o += 8
    if len(vals) >= 400:
        markers_start, mvals = ms, vals; break
if markers_start is None:
    print("FAIL markers"); sys.exit(1)
print("[2] markers @0x%x count=%d" % (markers_start, len(mvals)))

# ---- 3. names_start ----
names_start = None
for d in range(0, 120000):
    ns = markers_start - mvals[-1] - d
    if ns < 0:
        break
    pos = ns
    for i in range(256):
        if pos >= markers_start:
            break
        pos += 1 + data[pos]
    if pos - ns == mvals[1]:
        names_start = ns; break
if names_start is None:
    print("FAIL names_start"); sys.exit(1)
print("[3] names_start @0x%x" % names_start)

# ---- 4. decode names ----
pos = names_start; names = []
while pos < markers_start:
    l = data[pos]
    if l == 0 or pos + 1 + l > markers_start:
        break
    q = pos + 1; s = []
    for k in range(l):
        s.append(tok(data[q])); q += 1
    full = ''.join(s); names.append((full[1:], full[0])); pos = q
num_syms = len(names)
nameidx = {n: i for i, (n, _) in enumerate(names)}
print("[4] names: %d  first=%r last=%r" % (num_syms, names[0][0], names[-1][0]))

# ---- 5. offsets table anchored on linux_banner ----
num_pos = next((q for q in range(names_start-8, max(0, names_start-0x4000), -8)
                if u64(q) == num_syms), names_start - 8)
rel_base = u64(num_pos - 8)
lv = data.find(b'Linux version ')
k = nameidx.get('linux_banner')
off_start = None
if k is not None and lv >= 0:
    for p in range(max(0, num_pos - num_syms*4 - 0x100000), num_pos + 0x2000, 4):
        if s32(p) != lv:
            continue
        cand = p - 4*k
        if cand < 0 or s32(cand) != 0:
            continue
        prev = 0; ok = True
        for i in range(1, num_syms):
            v = s32arr[cand//4 + i]
            if v < prev:
                ok = False; break
            prev = v
        if ok:
            off_start = cand; break
if off_start is None:
    print("FAIL offsets"); sys.exit(1)
offs = list(s32arr[off_start//4: off_start//4 + num_syms])
print("[5] num_syms @0x%x  offsets @0x%x  last=0x%x" % (num_pos, off_start, offs[-1]))

# ---- 6. verify + write ----
syms = [(names[i][0], names[i][1], offs[i]) for i in range(num_syms)]
for name in ('linux_banner', '_etext', 'do_futex', 'futex_wait', 'core_sys_select',
             'remove_waiter', 'init_task', 'init_cred', 'selinux_state'):
    h = next((x for x in syms if x[0] == name), None)
    print("      %-18s %s" % (name, ("%s 0x%x" % (h[1], h[2])) if h else "(not found)"))
lb = next(x[2] for x in syms if x[0] == 'linux_banner')
print("      linux_banner bytes: %r" % data[lb:lb+22])

with open(out, 'w') as f:
    BASE = 0xffffff8008000000
    for name, typ, off in syms:
        f.write("%016x %s %s\n" % ((BASE + off) & 0xffffffffffffffff, typ, name))
print("[6] wrote %s (%d symbols, VA base 0x%x)" % (out, len(syms), BASE))
