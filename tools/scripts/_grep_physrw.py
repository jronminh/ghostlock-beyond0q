import re
p="/root/ghostlock/ghostlock-oneplus/src/core/pipe_physrw.c"
for i,l in enumerate(open(p,errors="ignore").read().splitlines(),1):
    if re.search(r"PIPE_BUFFER|pb\.|pipe_buffer|0x10|0x18|0x20|->ops|->flags|->private|->page|ops_off|PIPE_BUF_FLAG|ANON_PIPE_BUF_OPS", l):
        print("%4d %s" % (i, l.strip()[:140]))
