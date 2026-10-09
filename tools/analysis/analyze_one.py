#!/usr/bin/env python3
"""analyze_one.py <symbol-substr> [...] : print, for each matching syscall entry,
every user->stack copy reachable: function path, dest offset from SP0, sink, and
the length register's value if resolvable (const) else 'din'."""
import re, subprocess, bisect, sys
BASE=0xffffff8008000000; IMG='/root/ghostlock/kernel/Image'; KS='/root/ghostlock/kernel/kallsyms_fixed.txt'
SINKS={'copy_from_user':(0,2),'_copy_from_user':(0,2),'__copy_from_user':(0,2),'raw_copy_from_user':(0,2),
 '__arch_copy_from_user':(0,2),'move_addr_to_kernel':(2,1),'copy_msghdr_from_user':(0,None),
 'get_compat_msghdr':(0,None),'import_iovec':(4,2),'__import_iovec':(4,2),'rw_copy_check_uvector':(4,2)}
syms=[]
for line in open(KS):
    m=re.match(r'([0-9a-f]+)\s+(\w)\s+(\S+)',line)
    if m: syms.append((int(m.group(1),16),m.group(2),m.group(3)))
syms.sort(); addrs=[a for a,_,_ in syms]; nm={a:n for a,_,n in syms}
sink={}
for a,t,n in syms:
    if n in SINKS and a not in sink: sink[a]=(n,)+SINKS[n]
def fend(a):
    i=bisect.bisect_right(addrs,a); return syms[i][0]-a if i<len(syms) else 0x400
def name_at(a):
    i=bisect.bisect_right(addrs,a)-1; return syms[i][2]
_c={}
def disasm(a):
    if a in _c: return _c[a]
    out=subprocess.run(['aarch64-linux-gnu-objdump','-D','-b','binary','-m','aarch64','--adjust-vma='+hex(BASE),
        IMG,'--start-address='+hex(a),'--stop-address='+hex(a+max(fend(a),0x40))],capture_output=True,text=True).stdout or ''
    ins=[]
    for l in out.splitlines():
        m=re.match(r'\s*([0-9a-f]+):\s+[0-9a-f ]+\t(\S+)\s*(.*)',l)
        if m: ins.append((m.group(2),m.group(3)))
    _c[a]=ins; return ins
def fr(ins):
    f=0;n=0
    for m,o in ins:
        if m=='sub' and re.match(r'sp, sp, #',o): f+=int(re.search(r'#(0x[0-9a-f]+|\d+)',o).group(1),16);n+=1
        elif m in ('stp','str') and re.search(r'\[sp, #-(0x[0-9a-f]+|\d+)\]!',o): f+=int(re.search(r'#-(0x[0-9a-f]+|\d+)',o).group(1),16);n+=1
        if n>=6: break
    return f
def val(ins,idx,r,win=40):
    for j in range(idx-1,max(-1,idx-win),-1):
        m,o=ins[j]
        v=re.match(re.escape(r)+r', sp, #(0x[0-9a-f]+|\d+)$',o)
        if v: return ('sp',int(v.group(1),16))
        if m=='mov' and re.match(re.escape(r)+r', sp$',o): return ('sp',0)
        w=r.replace('x','w',1)
        v=re.match(re.escape(w)+r', #(0x[0-9a-f]+|\d+)$',o)
        if v: return ('c',int(v.group(1),16))
        v=re.match(re.escape(w)+r', wzr, #(0x[0-9a-f]+|\d+)$',o)
        if v: return ('c',int(v.group(1),16))
    return (None,None)
def walk(a,off,path,depth,seen):
    if depth>6: return
    ins=disasm(a); f=fr(ins); cur=off+f
    for i,(m,o) in enumerate(ins):
        if m!='bl': continue
        t=re.search(r'0x([0-9a-f]+)',o)
        if not t: continue
        tgt=int(t.group(1),16)
        if tgt in sink:
            sn,dr,lr=sink[tgt]
            dv=val(ins,i,'x%d'%dr)
            if dv[0]=='sp':
                lv=val(ins,i,'w%d'%lr) if lr is not None else (None,None)
                L=('0x%x'%lv[1] if lv[0]=='c' else 'din')
                print('  SP0-0x%03x  %-24s <- %s   L=%s' % (cur-dv[1], sn, '>'.join(path+[name_at(a)]), L))
        elif 0<(tgt-BASE)<0x2000000 and tgt not in seen:
            walk(tgt,cur,path+[name_at(a)],depth+1,seen|{tgt})
for pat in (sys.argv[1:] or ['setsockopt','ptrace']):
    for a,t,n in syms:
        if n==pat or n=='SyS_'+pat.replace('SyS_',''):
            if n.startswith('SyS_') or n.startswith('compat_SyS_'):
                print('====', n, hex(a))
                walk(a,0,[],0,set())
