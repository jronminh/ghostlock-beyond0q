txt = open('/mnt/e/Library/Desktop/ghostlock/lastkmsg_june.lst', 'r', encoding='utf-8', errors='replace').read()
lines = txt.splitlines()
for i in range(4355, min(len(lines), 4500)):
    print(i, lines[i])
