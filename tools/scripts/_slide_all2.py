#!/usr/bin/env python3
"""_slide_all2.py — tinh slide = runtime_pc - (KIMAGE + sym_off) va so voi Kernel Offset."""
import zipfile, sys, re, os

KMSG = "dumpstate_lastkmsg.lst"
KIMAGE = 0xffffff8008000000
SYMS = {
    "rb_erase_cached": 0x16e7a6c,
    "rt_mutex_adjust_prio_chain": 0x0b2eec,
    "rt_mutex_adjust_pi": 0x0b2e34,
    "__sched_setscheduler": 0x06f39c,
    "SyS_sched_setattr": 0x06feac,
    "SyS_setsockopt": 0x1428f54,
    "sock_setsockopt": 0x142eafc,
    "_raw_spin_trylock": 0x16f99c4,
}
re_proc = re.compile(r"Process (\S+) \(pid: (\d+)")
re_pc_sym = re.compile(r"pc : ([\w.]+)\+0x([0-9a-fA-F]+)/")
re_PCblock = re.compile(r"PC: (0x[0-9a-fA-F]+):")
re_code_fault = re.compile(r"Code: .*\(([0-9a-fA-F]{8})\)")
re_ko = re.compile(r"Kernel Offset: (0x[0-9a-fA-F]+) from")

def parse_block(L, i0):
    """From index of 'PC: 0xADDR:' line, gather {addr: 'word'} from following code lines."""
    m = re_PCblock.search(L[i0])
    start = int(m.group(1), 16)
    words = {}
    for j in range(i0+1, min(len(L), i0+40)):
        tail = L[j].rsplit("]",1)[-1].strip()
        mm = re.match(r"([0-9a-f]{3,6})\s+((?:[0-9a-f]{8}\s*){4,})", tail)
        if not mm: 
            if words: break
            continue
        a = int(mm.group(1),16)
        for k,w in enumerate(mm.group(2).split()):
            words[a+4*k] = w
    return start, words

for p in sys.argv[1:]:
    L = zipfile.ZipFile(p).read(KMSG).decode("utf-8","replace").splitlines()
    for i,l in enumerate(L):
        if not re_proc.search(l): continue
        proc = re_proc.search(l).group(1)
        # Code fault word
        fault=None; cidx=None
        for j in range(i, min(len(L), i+90)):
            m=re_code_fault.search(L[j])
            if m: fault=m.group(1).lower(); cidx=j; break
        # pc sym
        sym=None; off=None
        for j in range(max(0,i-8), min(len(L), i+90)):
            m=re_pc_sym.search(L[j])
            if m: sym=m.group(1); off=int(m.group(2),16); break
        # nearest PC block at or before cidx
        runtime=None
        if fault:
            blocks=[j for j in range(max(0,i-40), min(len(L), (cidx or i)+2)) if re_PCblock.search(L[j])]
            # choose the block whose window contains the fault word
            for bj in blocks:
                start, words = parse_block(L,bj)
                for a,w in words.items():
                    if w.lower()==fault:
                        runtime = (start & ~0xffff) | (a & 0xffff)
                        if (a & 0xffff) < (start & 0xffff): runtime += 0x10000
                        break
                if runtime: break
        ko=None
        for j in range(i, min(len(L), i+700)):
            m=re_ko.search(L[j])
            if m: ko=int(m.group(1),16); break
        slide=None
        if runtime and sym in SYMS:
            slide = runtime - off - (KIMAGE + SYMS[sym])
        print("%-46s %-13s %-27s sym_off=%#09x runt=%#011x KO=%s slide=%s  KO+0x80000=%s" % (
            os.path.basename(p), proc, sym, off or 0, runtime or 0,
            (hex(ko) if ko else "?"), (hex(slide) if slide is not None else "?"),
            (hex(ko+0x80000) if ko else "?")))
