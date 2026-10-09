import re, subprocess
BASE = 0xffffff8008000000
IMG = '/root/ghostlock/kernel/Image'
KS  = '/root/ghostlock/kernel/kallsyms_fixed.txt'
sinknames=set(['copy_from_user','_copy_from_user','__copy_from_user','raw_copy_from_user','move_addr_to_kernel','copy_msghdr_from_user','get_compat_msghdr','import_iovec','__import_iovec','rw_copy_check_uvector'])
sink={}
for line in open(KS):
    m=re.match(r'([0-9a-f]+)\s+(\w)\s+(\S+)',line)
    if m and m.group(3) in sinknames: sink[int(m.group(1),16)]=m.group(3)
print('sinks found:', len(sink), {hex(k):v for k,v in list(sink.items())[:6]})
a=0xffffff800942960c  # SyS_sendmsg
out=subprocess.run(['aarch64-linux-gnu-objdump','-d','-b','binary','-m','aarch64','--adjust-vma='+hex(BASE),IMG,'--start-address='+hex(a),'--stop-address='+hex(a+0x2a0)],capture_output=True,text=True).stdout
print('objdump bytes:', len(out))
for l in out.splitlines()[:6]: print(repr(l))
print('--- bl targets ---')
for l in out.splitlines():
    if '\tbl\t' in l or ' bl ' in l or '\tbl ' in l:
        print(repr(l))
