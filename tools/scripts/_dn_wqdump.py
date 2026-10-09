#!/usr/bin/env python3
import re, subprocess

out = subprocess.run(["readelf", "--debug-dump=info", "/tmp/workqueue.o"],
                     capture_output=True, text=True).stdout

want_structs = {"workqueue_struct", "worker_pool", "pool_workqueue"}
results = {}
cur_struct = None
cur_member = None
cur_size = {}

DIE = re.compile(r'^\s*<\d+><([0-9a-f]+)>:\s*Abbrev Number:.*\((DW_TAG_[a-z_]+)\)')
NAME = re.compile(r'DW_AT_name\s*:\s*(?:\(indirect string[^)]*\):\s*)?(.+?)\s*$')
LOC = re.compile(r'DW_AT_data_member_location:\s*(\d+)')
SIZE = re.compile(r'DW_AT_byte_size\s*:\s*(\d+)')

for line in out.splitlines():
    m = DIE.match(line)
    if m:
        tag = m.group(2)
        if tag in ("DW_TAG_structure_type", "DW_TAG_union_type", "DW_TAG_class_type"):
            cur_struct = None
            cur_member = None
        elif tag == "DW_TAG_member":
            cur_member = None
        continue
    nm = NAME.search(line)
    if nm:
        name = nm.group(1)
        if cur_struct is None:
            cur_struct = name
        elif cur_member is None:
            cur_member = name
        continue
    sz = SIZE.search(line)
    if sz and cur_struct is not None and cur_member is None:
        cur_size[cur_struct] = int(sz.group(1))
        continue
    lc = LOC.search(line)
    if lc and cur_struct is not None and cur_member:
        results.setdefault(cur_struct, []).append((cur_member, int(lc.group(1))))
        cur_member = None

for s in ["workqueue_struct", "pool_workqueue", "worker_pool"]:
    if s not in results:
        continue
    print("== struct %s (size=%s) ==" % (s, cur_size.get(s, "?")))
    for name, off in results[s]:
        print("   %-22s 0x%x (%d)" % (name, off, off))
