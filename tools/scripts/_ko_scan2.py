#!/usr/bin/env python3
"""_ko_scan2.py <dump...> — rut (Process, pc:sym+off, PC-code-addr, Kernel Offset) moi panic."""
import zipfile, sys, re, os

KMSG = "dumpstate_lastkmsg.lst"
re_boot = re.compile(r"Booting Linux|Linux version .*#\d+ SMP PREEMPT")
re_proc = re.compile(r"Process (\S+) \(pid: (\d+)")
re_pc_sym = re.compile(r"pc : ([\w.]+)\+0x([0-9a-fA-F]+)")
re_PC = re.compile(r"PC: (0x[0-9a-fA-F]+):")
re_code = re.compile(r"Code: ((?:[0-9a-fA-F]{8} ){4})\(([0-9a-fA-F]{8})\)")
re_ko = re.compile(r"Kernel Offset: (0x[0-9a-fA-F]+) from (0x[0-9a-fA-F]+)")

def dump(p):
    z = zipfile.ZipFile(p)
    name = KMSG if KMSG in z.namelist() else z.namelist()[0]
    return z.read(name).decode("utf-8", "replace").splitlines()

for p in sys.argv[1:]:
    L = dump(p)
    print("=====", os.path.basename(p), "lines", len(L))
    # find boot boundaries
    boots = [i for i, l in enumerate(L) if re_boot.search(l)]
    # find panic points
    panics = [i for i, l in enumerate(L) if re_proc.search(l)]
    for pi in panics:
        proc = re_proc.search(L[pi]).group(1)
        # nearest preceding Kernel Offset AFTER this panic (dump prints at end of panic)
        ko = None
        for j in range(pi, min(len(L), pi + 400)):
            m = re_ko.search(L[j])
            if m:
                ko = m.group(1); break
        # bound: next boot
        nb = next((b for b in boots if b > pi), len(L))
        # pc symbol within block
        syms = []
        for j in range(pi, min(nb, pi + 200)):
            m = re_pc_sym.search(L[j])
            if m:
                syms.append((m.group(1), int(m.group(2), 16)))
        # PC code blocks
        pcs = []
        for j in range(pi, min(nb, pi + 200)):
            m = re_PC.search(L[j])
            if m:
                # next line holds bytes
                pcs.append(int(m.group(1), 16))
        codes = []
        for j in range(pi, min(nb, pi + 200)):
            m = re_code.search(L[j])
            if m:
                codes.append((int(m.group(2), 16), j))
        print("  proc=%s ko=%s boot_boundary=%s" % (proc, ko, nb))
        print("    pc:sym=%s" % (syms[:4],))
        print("    PC blocks=%s" % ([hex(x) for x in pcs[:6]],))
        print("    codes=%s" % ([hex(c[0]) for c in codes[:4]],))
