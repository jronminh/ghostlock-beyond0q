#!/usr/bin/env python3
"""geom_scan3.py - fast: memoize per-function sink reachability, multithreaded objdump.

reach(F) = set of (offset_below_F_entry_sp, sink, L) for every user->stack copy
reachable from F, where offset is in bytes below F's ENTRY sp.  A sink local at
F_sp+imm has dest (fr-imm); a callee C contributes (fr + x) for x in reach(C).
For a syscall entry E (entry sp == SP0), reach(E) gives SP0-relative dest offsets.
"""
import re, subprocess, bisect, sys, threading
from concurrent.futures import ThreadPoolExecutor

BASE=0xffffff8008000000
IMG='/root/ghostlock/kernel/Image'; KS='/root/ghostlock/kernel/kallsyms_fixed.txt'
NW = 8

SINKS={'copy_from_user':(0,2,1),'_copy_from_user':(0,2,1),'__copy_from_user':(0,2,1),
 'raw_copy_from_user':(0,2,1),'__arch_copy_from_user':(0,2,1),'move_addr_to_kernel':(2,1,1),
 'copy_msghdr_from_user':(0,None,1),'get_compat_msghdr':(0,None,1),
 'import_iovec':(4,2,16),'__import_iovec':(4,2,16),'rw_copy_check_uvector':(4,2,16)}

syms=[]
for line in open(KS):
    m=re.match(r'([0-9a-f]+)\s+(\w)\s+(\S+)',line)
    if m: syms.append((int(m.group(1),16),m.group(2),m.group(3)))
syms.sort(); addrs=[a for a,_,_ in syms]
sink={}
for a,t,n in syms:
    if n in SINKS and a not in sink: sink[a]=(n,)+SINKS[n]
def fend(a):
    i=bisect.bisect_right(addrs,a); return syms[i][0]-a if i<len(syms) else 0x400

lock=threading.Lock(); _cache={}
def disasm(a):
    with lock:
        if a in _cache: return _cache[a]
    ln=max(fend(a),0x40)
    out=subprocess.run(['aarch64-linux-gnu-objdump','-D','-b','binary','-m','aarch64',
        '--adjust-vma='+hex(BASE),IMG,'--start-address='+hex(a),'--stop-address='+hex(a+ln)],
        capture_output=True,text=True).stdout or ''
    ins=[]
    for l in out.splitlines():
        m=re.match(r'\s*([0-9a-f]+):\s+[0-9a-f ]+\t(\S+)\s*(.*)',l)
        if m: ins.append((m.group(2),m.group(3)))
    with lock: _cache[a]=ins
    return ins
def fmtsz(ins):
    fr=0;n=0
    for m,o in ins:
        if m=='sub' and re.match(r'sp, sp, #',o): fr+=int(re.search(r'#(0x[0-9a-f]+|\d+)',o).group(1),16);n+=1
        elif m in ('stp','str') and re.search(r'\[sp, #-(0x[0-9a-f]+|\d+)\]!',o): fr+=int(re.search(r'#-(0x[0-9a-f]+|\d+)',o).group(1),16);n+=1
        if n>=6: break
    return fr
def val(ins,idx,r):
    for j in range(idx-1,max(-1,idx-14),-1):
        m,o=ins[j]
        m1=re.match(re.escape(r)+r', sp, #(0x[0-9a-f]+|\d+)$',o)
        if m1: return ('sp',int(m1.group(1),16))
        if m=='mov' and re.match(re.escape(r)+r', sp$',o): return ('sp',0)
        w=r.replace('x','w',1)
        m2=re.match(re.escape(w)+r', #(0x[0-9a-f]+|\d+)$',o)
        if m2: return ('c',int(m2.group(1),16))
        m3=re.match(re.escape(w)+r', wzr, #(0x[0-9a-f]+|\d+)$',o)
        if m3: return ('c',int(m3.group(1),16))
    return (None,None)

_memo={}
def reach(F,depth=0):
    if F in _memo: return _memo[F]
    if depth>8: return []
    ins=disasm(F); fr=fmtsz(ins); out=[]
    for i,(m,o) in enumerate(ins):
        if m!='bl': continue
        t=re.search(r'0x([0-9a-f]+)',o)
        if not t: continue
        tgt=int(t.group(1),16)
        if tgt in sink:
            sn,dr,lr,sc=sink[tgt]
            dv=val(ins,i,'x%d'%dr)
            if dv[0]=='sp':
                lv=val(ins,i,'w%d'%lr) if lr is not None else (None,None)
                L=lv[1]*sc if lv[0]=='c' else -1
                out.append((fr-dv[1],sn,L))
        elif 0<(tgt-BASE)<0x2000000:
            for (x,sn,L) in reach(tgt,depth+1):
                out.append((fr+x,sn,L))
    _memo[F]=out
    return out

entries=[];sd=set()
for a,t,n in syms:
    if (n.startswith('SyS_') or n.startswith('compat_SyS_')) and a not in sd:
        sd.add(a); entries.append((a,n))

def one(e):
    a,n=e; return (n, reach(a))
with ThreadPoolExecutor(max_workers=NW) as ex:
    allr=list(ex.map(one, entries))

LO,HI=0x178,0x188
usable=[]; unk=[]
for n,rows in allr:
    best=None
    for Xs,sn,L in rows:
        if L>0 and Xs>=HI and Xs-L<=LO and (best is None or Xs<best[0]): best=(Xs,L,sn)
        if Xs>=0x180 and L<0: unk.append((n,Xs,sn))
    if best: usable.append((n,)+best)
print('== USABLE (buffer covers task+lock, L known) ==')
for n,Xs,L,sn in sorted(usable,key=lambda r:(r[1],r[0])):
    print('  %-38s Xs=0x%03x L=0x%03x span=[0x%03x,0x%03x] %s'%(n,Xs,L,Xs-L,Xs,sn))
print('== Xs>=0x180 but L unknown (manual L needed) ==')
for n,Xs,sn in sorted(set(unk),key=lambda r:(r[1],r[0]))[:40]:
    print('  %-38s Xs=0x%03x L=? %s'%(n,Xs,sn))
