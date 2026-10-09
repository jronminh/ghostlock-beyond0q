#!/usr/bin/env python3
"""_slide_all.py — voi moi panic trong dump: tim runtime PC (tu Code line) + symbol, tinh slide."""
import zipfile, sys, re, os, glob

KMSG = "dumpstate_lastkmsg.lst"
KIMAGE = 0xffffff8008000000
# kallsyms_fixed offsets (Image-relative) for symbols seen in panics
SYMS = {
    "rb_erase_cached": 0x16e7a6c,
    "rt_mutex_adjust_prio_chain": 0x0b2eec,
    "rt_mutex_adjust_pi": 0x0b2e34,
    "__sched_setscheduler": 0x06f39c,
    "SyS_sched_setattr": 0x06feac,
    "SyS_setsockopt": 0x1428f54,
    "sock_setsockopt": 0x142eafc,
}
re_pc_sym = re.compile(r"pc : ([\w.]+)\+0x([0-9a-fA-F]+)")
re_PCblock = re.compile(r"PC: (0x[0-9a-fA-F]+):")
re_code = re.compile(r"Code: ((?:[0-9a-fA-F]{8} )+)\(([0-9a-fA-F]{8})\)")
re_proc = re.compile(r"Process (\S+) \(pid: (\d+)")
re_ko = re.compile(r"Kernel Offset: (0x[0-9a-fA-F]+) from (0x[0-9a-fA-F]+)")

def run(p):
    L = zipfile.ZipFile(p).read(KMSG).decode("utf-8","replace").splitlines()
    for i,l in enumerate(L):
        if not re_proc.search(l): continue
        proc = re_proc.search(l).group(1)
        # find Code line within next 40 lines
        code_fault = None; ci=None
        for j in range(i, min(len(L), i+40)):
            m = re_code.search(L[j])
            if m: code_fault = m.group(2); ci=j; break
        # find pc : sym+off around
        sym=None; off=None
        for j in range(max(0,i-6), min(len(L), i+40)):
            m = re_pc_sym.search(L[j])
            if m: sym=m.group(1); off=int(m.group(2),16); break
        # find PC block address near ci
        block=None
        for j in range(max(0,(ci or i)-40), min(len(L),(ci or i)+2)):
            m = re_PCblock.search(L[j])
            if m and j <= (ci or i): block=int(m.group(1),16)
            elif m and block is None: block=int(m.group(1),16)
        # KO
        ko=None
        for j in range(i, min(len(L), i+600)):
            m=re_ko.search(L[j])
            if m: ko=m.group(1); break
        # runtime pc = block + offset of code_fault within printed blocks
        runtime=None
        if block and code_fault and ci is not None:
            # gather words from block lines (the lines after PC: line, each starts with 4-hex offset)
            words={}
            base_blk = block & ~0x3f  # not used
            for j in range(ci-16, ci+1):
                s=L[j]
                mm=re.match(r"\s*([0-9a-f]{4,})\s+([0-9a-f ]+)", s.strip("<>I4 ")) if False else None
            # simpler: parse lines that look like "  7a4c  w w w ..."
            for j in range(max(0,ci-20), ci+1):
                s=L[j]
                m2=re.search(r"\b([0-9a-f]{3,5})\s+((?:[0-9a-f]{8}\s*){6,})", s)
                if not m2: continue
                a=int(m2.group(1),16)
                ws=m2.group(2).split()
                for k,w in enumerate(ws):
                    words[a+4*k]=w
            # block address low 16 bits
            for a,w in words.items():
                if w.lower()==code_fault.lower():
                    # reconstruct full addr: high bits from block
                    runtime = (block & ~0xffff) | (a & 0xffff)
                    # handle carry if a low part < block low part
                    if (a & 0xffff) < (block & 0xffff): runtime += 0x10000
                    break
        slide=None; note=""
        if runtime and sym in SYMS:
            u = runtime - off
            slide = u - (KIMAGE + SYMS[sym])
        print("%-40s %-14s sym=%-28s off=%#x runt=%#x ko=%s slide=%s" % (
            os.path.basename(p), proc, sym, off or 0, runtime or 0, ko,
            (hex(slide) if slide is not None else "?")))

for p in sys.argv[1:]:
    run(p)
