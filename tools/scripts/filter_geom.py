import re, sys
p = '/mnt/e/Library/Desktop/ghostlock/geom_out.txt'
rows = []
for line in open(p, errors='replace'):
    m = re.match(r'(\S+)\s+-0x([0-9a-f]+)\s+(\S+)\s*(\S*)', line)
    if m:
        rows.append((m.group(1), int(m.group(2), 16), m.group(3)))
print('total rows:', len(rows))
print('--- X_s >= 0x178 (can reach lock 0x178; task 0x180 iff X_s>=0x180) ---')
for n, x, s in sorted(rows, key=lambda r: -r[1]):
    if x >= 0x178:
        tag = 'BOTH' if x >= 0x180 else 'lock'
        print('%-40s 0x%04x %-10s %s' % (n, x, tag, s))
print('--- X_s in [0x160,0x178) (reach lock only if L>=..) ---')
for n, x, s in sorted(rows, key=lambda r: -r[1]):
    if 0x160 <= x < 0x178:
        print('%-40s 0x%04x %-10s %s' % (n, x, 'near', s))
