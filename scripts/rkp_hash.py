#!/usr/bin/env python3
"""rkp_hash.py - recover Samsung RKP hashed log tokens.

RKP binaries ship with log strings replaced by placeholders `RKP_<sha256(token)[:8]>`.
This tool extracts the placeholders from a dumped `hyp` image and matches them against
a dictionary of candidate tokens (article text + kernel source) by hashing each candidate
the same way.

Usage:  rkp_hash.py <hyp.bin> <candidate_file|dir> [more...]
"""
import hashlib
import os
import re
import sys

PH = re.compile(rb"RKP_([0-9a-f]{8})")


def sha8(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8", "replace")).hexdigest()[:8]


def placeholders(path: str):
    data = open(path, "rb").read()
    return set(m.decode() for m in PH.findall(data))


def tokens_from_text(path: str):
    try:
        txt = open(path, "r", errors="replace").read()
    except OSError:
        return
    # identifiers / words / dotted names / .c file names
    for m in re.finditer(r"[A-Za-z_][A-Za-z0-9_]*", txt):
        yield m.group(0)
        yield m.group(0).lower()
    # quoted string literals (whole) and their inner words
    for m in re.finditer(r'"([^"\\]{2,120})"', txt):
        s = m.group(1)
        yield s
        for w in re.findall(r"[A-Za-z_][A-Za-z0-9_.%]*", s):
            yield w


def walk(path: str):
    if os.path.isfile(path):
        yield from tokens_from_text(path)
    else:
        for root, _dirs, files in os.walk(path):
            for f in files:
                if f.endswith((".c", ".h", ".S", ".txt", ".md")):
                    yield from tokens_from_text(os.path.join(root, f))


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    phs = placeholders(sys.argv[1])
    print(f"[*] {len(phs)} unique RKP_ placeholders in {sys.argv[1]}")
    cands = set()
    for p in sys.argv[2:]:
        cands.update(walk(p))
    print(f"[*] {len(cands)} candidate tokens")
    found = {}
    for c in cands:
        hh = sha8(c)
        if hh in phs:
            found.setdefault(hh, set()).add(c)
    print(f"[+] recovered {len(found)} / {len(phs)} placeholders\n")
    for hh, names in sorted(found.items(), key=lambda kv: sorted(kv[1])[0].lower()):
        print(f"  RKP_{hh} = {sorted(names)}")
    # also dump unrecovered placeholders
    un = phs - set(found)
    open("tools/rkp_unrecovered.txt", "w").write("\n".join(sorted(un)))
    print(f"\n[*] {len(un)} unrecovered -> tools/rkp_unrecovered.txt")


if __name__ == "__main__":
    main()
