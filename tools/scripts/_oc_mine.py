import os, re, glob
ROOT = r"E:\Library\Desktop\ghostlock-beyond0q\recovered"
OUT = r"E:\Library\Desktop\ghostlock-beyond0q\_oc_out.txt"
pat = re.compile(r"uid\s*=\s*0|uid 0|umh_uid|complete=1|retval=0|uid_after|root shell|127\.0\.0\.1:2223|getuid\(\)\s*==\s*0|uid==0|đã root|root rồi|thành root|euid=0", re.I)
f = open(OUT, "w", encoding="utf-8", errors="replace")
for fn in sorted(glob.glob(os.path.join(ROOT, "*", "notes.md")) + glob.glob(os.path.join(ROOT, "*", "commands.md"))):
    s = open(fn, encoding="utf-8", errors="replace").read()
    hits = [(i, l) for i, l in enumerate(s.splitlines()) if pat.search(l)]
    if not hits: continue
    f.write("################ %s  (%d hits)\n" % (os.path.relpath(fn, ROOT), len(hits)))
    for i, l in hits[:25]:
        f.write("  %s\n" % l.strip()[:200])
f.close(); print("ok")
