#!/usr/bin/env python3
"""ko_scan.py — quet 'Kernel Offset' + 'pc :'/'PC: 0x' trong cac dump ZIP."""
import zipfile, sys, re, glob, os

KMSG = "dumpstate_lastkmsg.lst"
pat_ko = re.compile(r"Kernel Offset: (0x[0-9a-fA-F]+)")
pat_proc = re.compile(r"Process (ghostlock\w+) \(pid: (\d+)")
pat_pc = re.compile(r"pc : ([0-9a-fA-Fx]+)(?:\+0x([0-9a-fA-F]+))?/(?:0x)?([0-9a-fA-F]+)?")
pat_PC = re.compile(r"PC: (0x[0-9a-fA-F]+):")
pat_sym = re.compile(r"^\s*([A-Za-z_][\w.]*)(?:\+0x([0-9a-fA-F]+))?/0x[0-9a-fA-F]+$")

for p in sys.argv[1:]:
    print("=====", os.path.basename(p))
    try:
        z = zipfile.ZipFile(p)
        name = KMSG if KMSG in z.namelist() else z.namelist()[0]
        L = z.read(name).decode("utf-8", "replace").splitlines()
    except Exception as e:
        print("  ERR", e); continue
    ko = pat_ko.findall("\n".join(L))
    procs = sorted(set(pat_proc.findall("\n".join(L))))
    print("  Kernel Offset:", ko[:3])
    print("  Process:", procs)
    # find panic pc and nearby PC: lines
    for i, l in enumerate(L):
        m = pat_pc.search(l)
        if m and ("ghostlock" in l or True):
            # only report if it is a panic-ish line (pc : with +off)
            if "+0x" in l:
                ctx = []
                for j in range(i, min(len(L), i + 80)):
                    mm = pat_PC.search(L[j])
                    if mm:
                        ctx.append(mm.group(1)); break
                print("   pc: %s   addr=%s" % (l.split("]")[-1].strip()[:70], ctx))
