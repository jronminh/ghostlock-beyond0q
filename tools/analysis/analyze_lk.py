import zipfile, sys, glob, os

files = sys.argv[1:] or glob.glob('/mnt/e/Library/Desktop/ghostlock/kp/*.gz')
for p in sorted(files):
    try:
        z = zipfile.ZipFile(p)
        data = z.read('dumpstate_lastkmsg.lst')
    except Exception as e:
        print('==', os.path.basename(p), 'ERR', e)
        continue
    t = data.decode('utf-8', 'replace').splitlines()
    crash = None
    for i, l in enumerate(t):
        if 'Unable to handle kernel' in l or 'Kernel panic' in l or 'Internal error' in l:
            crash = i
            break
    print('=====', os.path.basename(p), 'lines=%d' % len(t), 'crash@%s' % crash)
    if crash is None:
        continue
    for l in t[crash:crash+45]:
        # trim timestamp
        if '] ' in l:
            l = l.split('] ', 1)[1]
        if any(k in l for k in ('Unable', 'Internal error', 'Process', 'pc :', 'lr :',
                                'x0 :', 'x19:', 'x20:', 'x24:', 'x25:', 'x26:', 'Call trace:',
                                'rt_mutex', 'futex', 'sched', 'spin', 'BUG', 'Code:', 'Comm:')):
            print('   ', l)
        elif 'Call trace:' in l:
            print(l)
