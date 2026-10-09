#!/usr/bin/env python3
import os
F = os.path.expanduser("~/ghostlock/ghostlock-oneplus/src/core/umh_root.c")
s = open(F, encoding="utf-8").read()
s = s.replace('_uid%d_fsuid%d",\n             f, oe, (long)r, we, getuid(), (int)setfsuid(getuid()));',
              '_uid%d",\n             f, oe, (long)r, we, getuid());')
open(F, "w", encoding="utf-8").write(s)
print("ok")
