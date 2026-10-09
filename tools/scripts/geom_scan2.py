#!/usr/bin/env python3
"""geom_scan2.py - like geom_scan.py but also estimates the copy length L and
checks true coverage of the waiter's task(+0x30=SP0-0x180) and lock(+0x38=SP0-0x178).
Buffer spans [X_s-L, X_s] (X = bytes below SP0). Coverage needs X_s>=0x188 and X_s-L<=0x178."""
import re, subprocess, bisect

BASE = 0xffffff8008000000
IMG = '/root/ghostlock/kernel/Image'
KS  = '/root/ghostlock/kernel/kallsyms_fixed.txt'

_syms = []
for line in open(KS):
    m = re.match(r'([0-9a-f]+)\s+(\w)\s+(\S+)', line)
    if m: _syms.append((int(m.group(1),16), m.group(2), m.group(3)))
_syms.sort(); _addrs = [a for a,_,_ in _syms]
def func_end(a):
    i = bisect.bisect_right(_addrs, a)
    return _syms[i][0]-a if i < len(_syms) else 0x400

# sink name -> (dstreg_idx, lenreg_idx, len_scale)   reg idx: 0=x0/w0 ...
SINKS = {
 'copy_from_user': (0,2,1), '_copy_from_user': (0,2,1), '__copy_from_user': (0,2,1),
 'raw_copy_from_user': (0,2,1), '__arch_copy_from_user': (0,2,1),
 'move_addr_to_kernel': (2,1,1),
 'copy_msghdr_from_user': (0,None,1), 'get_compat_msghdr': (0,None,1),
 'import_iovec': (4,2,16), '__import_iovec': (4,2,16), 'rw_copy_check_uvector': (4,2,16),
}
_sink = {}
for a,t,n in _syms:
    if n in SINKS: _sink.setdefault(a,(n,)+SINKS[n])

_cache={}
def disasm(a):
    if a in _cache: return _cache[a]
    ln=max(func_end(a),0x40)
    out=subprocess.run(['aarch64-linux-gnu-objdump','-D','-b','binary','-m','aarch64',
        '--adjust-vma='+hex(BASE),IMG,'--start-address='+hex(a),'--stop-address='+hex(a+ln)],
        capture_output=True,text=True).stdout or ''
    ins=[]
    for l in out.splitlines():
        m=re.match(r'\s*([0-9a-f]+):\s+[0-9a-f ]+\t(\S+)\s*(.*)',l)
        if m: ins.append((int(m.group(1),16),m.group(2),m.group(3)))
    _cache[a]=ins; return ins

def fmtsz(ins):
    fr=0;n=0
    for a,m,o in ins:
        if m=='sub' and re.match(r'sp, sp, #',o): fr+=int(re.search(r'#(0x[0-9a-f]+|\d+)',o).group(1),16);n+=1
        elif m in ('stp','str') and re.search(r'\[sp, #-(0x[0-9a-f]+|\d+)\]!',o): fr+=int(re.search(r'#-(0x[0-9a-f]+|\d+)',o).group(1),16);n+=1
        if n>=6: break
    return fr

def val_of(ins,idx,reg64):
    """return ('sp',off)/( 'const',v ) of reg64 at ins[idx]."""
    r=reg64
    for j in range(idx-1,max(-1,idx-14),-1):
        _,m,o=ins[j]
        m1=re.match(re.escape(r)+r', sp, #(0x[0-9a-f]+|\d+)$',o)
        if m1: return ('sp',int(m1.group(1),16))
        if m=='mov' and re.match(re.escape(r)+r', sp$',o): return ('sp',0)
        w=r.replace('x','w',1); w2=r.replace('x','w',1)
        m2=re.match(re.escape(w2)+r', #(0x[0-9a-f]+|\d+)$',o)
        if m2: return ('const',int(m2.group(1),16))
        m3=re.match(re.escape(w2)+r', wzr, #(0x[0-9a-f]+|\d+)$',o)
        if m3: return ('const',int(m3.group(1),16))
    return (None,None)

res={}
def walk(a,off,depth,seen,name):
    if depth>4 or a in seen: return
    seen=seen|{a}
    ins=disasm(a); fr=fmtsz(ins); cur=off+fr
    for i,(ia,m,o) in enumerate(ins):
        if m!='bl': continue
        t=re.search(r'0x([0-9a-f]+)',o)
        if not t: continue
        tgt=int(t.group(1),16)
        if tgt in _sink:
            sn,dr,lr,sc=_sink[tgt]
            drv=val_of(ins,i,'x%d'%dr)
            Lv=val_of(ins,i,'w%d'%lr) if lr is not None else (None,None)
            if drv[0]=='sp':
                Xs=cur-drv[1]
                L=(Lv[1]*sc) if Lv[0]=='const' else -1
                res.setdefault(name,[]).append((Xs,L,sn))
        elif 0<(tgt-BASE)<0x2000000:
            walk(tgt,cur,depth+1,seen,name)

entries=[];sd=set()
for a,t,n in _syms:
    if (n.startswith('SyS_') or n.startswith('compat_SyS_')) and a not in sd:
        sd.add(a); entries.append((a,n))

WAIT_LO=0x178; WAIT_HI=0x188
usable=[]; unk=[]
for a,n in entries:
    res.pop(n,None); walk(a,0,0,set(),n)
    best=None
    for Xs,L,sn in res.get(n,[]):
        if L>0 and Xs>=WAIT_HI and Xs-L<=WAIT_LO:
            if best is None or Xs<best[0]: best=(Xs,L,sn)
        if Xs>=0x180 and L<0:
            unk.append((n,Xs,sn))
    if best: usable.append((n,)+best)

print('usable (buffer covers task+lock, L known):')
for n,Xs,L,sn in sorted(usable,key=lambda r:-r[1]):
    print('  %-38s Xs=0x%03x L=0x%03x span=[0x%03x,0x%03x] %s' % (n,Xs,L,Xs-L,Xs,sn))
print()
print('candidates Xs>=0x180 with UNKNOWN L (need manual L):')
for n,Xs,sn in sorted(set(unk),key=lambda r:-r[1])[:30]:
    print('  %-38s Xs=0x%03x L=? %s' % (n,Xs,sn))
