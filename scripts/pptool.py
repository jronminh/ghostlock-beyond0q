#!/usr/bin/env python3
"""pptool.py - parse Android /data/property/persistent_properties (a protobuf of
concatenated `PersistentProperty { name=1; value=2 }` messages framed as field 1)
and emit the bytes that APPEND the Vietnam VoLTE persist props.

Usage:
  pptool.py dump <b64file>            # parse + list entries
  pptool.py mkapp <out.b64>           # write base64 of the append bytes
"""
import base64
import re
import sys

# the 6 override props to append
PROPS = [
    ("persist.dbg.volte_avail_ovr", "1"),
    ("persist.dbg.vt_avail_ovr", "1"),
    ("persist.dbg.wfc_avail_ovr", "1"),
    ("persist.dbg.ims_volte_enable", "1"),
    ("persist.radio.calls.on.ims", "1"),
    ("persist.radio.jbims", "1"),
]


def varint(n: int) -> bytes:
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def read_varint(buf: bytes, i: int):
    shift = 0
    val = 0
    while True:
        b = buf[i]
        i += 1
        val |= (b & 0x7F) << shift
        if not (b & 0x80):
            return val, i
        shift += 7


def parse(buf: bytes):
    """Yield (name, value) for each top-level field-1 length-delimited entry."""
    i = 0
    while i < len(buf):
        key, i = read_varint(buf, i)
        field, wire = key >> 3, key & 7
        if wire != 2:
            raise ValueError(f"unexpected wire type {wire} at {i}")
        ln, i = read_varint(buf, i)
        msg = buf[i:i + ln]
        i += ln
        if field != 1:
            continue
        # inner: name=1 (len-delim), value=2 (len-delim)
        j = 0
        name = value = None
        while j < len(msg):
            k, j = read_varint(msg, j)
            f, w = k >> 3, k & 7
            if w != 2:
                raise ValueError("inner non-len field")
            l, j = read_varint(msg, j)
            s = msg[j:j + l]
            j += l
            if f == 1:
                name = s
            elif f == 2:
                value = s
        yield (name.decode("utf-8", "replace"), (value or b"").decode("utf-8", "replace"))


def entry(name: str, value: str) -> bytes:
    nb, vb = name.encode(), value.encode()
    inner = b"\x0a" + varint(len(nb)) + nb + b"\x12" + varint(len(vb)) + vb
    return b"\x0a" + varint(len(inner)) + inner


def main():
    cmd = sys.argv[1]
    if cmd == "dump":
        raw = open(sys.argv[2], "r", errors="replace").read()
        # keep only lines that are pure base64 (skip the "uid=0 ..." line etc.)
        lines = [ln.strip() for ln in raw.splitlines()
                 if re.fullmatch(r"[A-Za-z0-9+/=]+", ln.strip() or "\n")]
        blob = "".join(lines)
        buf = base64.b64decode(blob)
        items = list(parse(buf))
        print(f"total bytes = {len(buf)}  entries = {len(items)}")
        for n, v in items:
            print(f"  {n} = {v!r}")
    elif cmd == "parsefile":
        buf = open(sys.argv[2], "rb").read()
        items = list(parse(buf))
        print(f"bytes = {len(buf)}  entries = {len(items)}")
        for n, v in items:
            if any(k in n for k in ("volte", "jbims", "calls.on.ims", "wfc", "vt_avail")):
                print(f"  {n} = {v!r}")
    elif cmd == "mkapp":
        blob = b"".join(entry(n, v) for n, v in PROPS)
        open(sys.argv[2], "w").write(base64.b64encode(blob).decode())
        print(f"append bytes = {len(blob)} -> {sys.argv[2]}")
        for n, v in PROPS:
            e = entry(n, v)
            print(f"  {n} = {v}  ({len(e)} bytes)")
    else:
        sys.exit("usage: dump <b64> | mkapp <out.b64>")


if __name__ == "__main__":
    main()
