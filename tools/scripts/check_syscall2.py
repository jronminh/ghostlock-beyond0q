import struct
d = open('/root/ghostlock/kernel/Image', 'rb').read()
base = 0xffffff8008000000
va = 0xffffff8009781000
off = va - base
print('file offset of sys_call_table =', hex(off), 'file size =', hex(len(d)))
print('first 8 raw qwords at that offset:',
      [hex(struct.unpack_from('<Q', d, off + i*8)[0]) for i in range(8)])
# also try the vmlinux ELF if available
try:
    from elftools.elf.elffile import ELFFile
    f = open('/root/ghostlock/kernel/vmlinux.elf', 'rb')
    e = ELFFile(f)
    symtab = e.get_section_by_name('.symtab')
    syms = {s.name: s['st_value'] for s in symtab.iter_symbols()}
    for n in ('sys_call_table', 'sys_select', 'sys_pselect6'):
        print(n, hex(syms.get(n, 0)))
    sct = syms['sys_call_table']
    for sec in e.iter_sections():
        if sec['sh_addr'] <= sct < sec['sh_addr'] + sec['sh_size']:
            pos = sct - sec['sh_addr']
            data = sec.data()[pos:pos+8*1070]
            for nr in (72, 1067):
                print('  nr', nr, '->', hex(struct.unpack_from('<Q', data, nr*8)[0]))
            break
except Exception as ex:
    print('ELF read failed:', ex)
