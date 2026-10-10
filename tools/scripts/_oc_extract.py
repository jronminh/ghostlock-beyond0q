import sqlite3, json, os, re, hashlib, html
DB = "file:C:/Users/jron/.local/share/opencode/opencode.db?mode=ro"
ROOT = r"E:\Library\Desktop\ghostlock-beyond0q\recovered"
db = sqlite3.connect(DB, uri=True); c = db.cursor()
def q(sql, a=()): return c.execute(sql, a).fetchall()

SESS = [
 ("ses_edefbadadffeWZZJZ53EDHXoZG", "bulk port SLIDE shift 8"),
 ("ses_edc7320bfffdQwPb3y1OEIvr0i", "root: chot KASLR slide"),
 ("ses_edbf99648ffdfG8zCHb7wE0wtJ", "root: go tuong page_base"),
 ("ses_edcfe2bafffeemezROUjpI2PT7", "port: blocker waiter"),
 ("ses_ede63f6b5ffeN3g00KsudH7VHD", "port len Galaxy S10e"),
 ("ses_edf7f7041ffeVunbqbIt64E3jW", "kiem tra dien thoai moi qua ADB"),
]

def san(p):
    p = p.replace("\\", "/")
    p = re.sub(r"^[A-Za-z]:/", "", p)
    return re.sub(r"[^A-Za-z0-9._/-]", "_", p)[-120:] or "x"

os.makedirs(ROOT, exist_ok=True)
idx = ["# Recovered session artifacts", "",
       "Extracted from opencode.db (session messages): every `write`/`edit`/`shell`/`execute`",
       "tool call and assistant/user text of the old ghostlock sessions.", ""]
tot = 0
for sid, label in SESS:
    d = os.path.join(ROOT, sid)
    wdir = os.path.join(d, "writes"); os.makedirs(wdir, exist_ok=True)
    notes = open(os.path.join(d, "notes.md"), "w", encoding="utf-8", errors="replace")
    edits = open(os.path.join(d, "edits.md"), "w", encoding="utf-8", errors="replace")
    cmds  = open(os.path.join(d, "commands.md"), "w", encoding="utf-8", errors="replace")
    wi = ["# writes (seq | time | path | bytes | sha1 | exists_now)"]
    nw = ne = nc = 0
    rows = q("select seq,type,time_created,data from session_message where session_id=? order by seq", (sid,))
    for seq, typ, t, data in rows:
        if typ == "user":
            try: j = json.loads(data); tx = j.get("text") or (j.get("metadata") or {}).get("displayText") or ""
            except: tx = ""
            if tx: notes.write("\n\n## [user seq=%s]\n\n%s\n" % (seq, tx))
            continue
        if typ != "assistant": continue
        try: j = json.loads(data)
        except: continue
        for part in (j.get("content") or []):
            pt = part.get("type")
            if pt == "text" and part.get("text"):
                notes.write("\n\n## [assistant seq=%s]\n\n%s\n" % (seq, part["text"]))
            elif pt == "tool":
                nm = part.get("name"); inp = (part.get("state") or {}).get("input") or {}
                if not isinstance(inp, dict):
                    continue
                if nm == "write" and "content" in inp:
                    p = inp.get("path", "?"); ct = inp.get("content") or ""
                    fn = "%06d__%s" % (seq, san(p).split("/")[-1])
                    with open(os.path.join(wdir, fn), "w", encoding="utf-8", errors="replace") as g:
                        g.write(ct)
                    tot += len(ct)
                    sha = hashlib.sha1(ct.encode("utf-8", "replace")).hexdigest()[:10]
                    ex = ""
                    if re.match(r"^[A-Za-z]:[\\/]", p): ex = "yes" if os.path.exists(p) else "NO"
                    wi.append("%6s | %s | %s | %d | %s | %s" % (seq, t, p, len(ct), sha, ex))
                    nw += 1
                elif nm == "edit":
                    edits.write("\n\n### edit seq=%s  path=%s\n--- OLD ---\n%s\n--- NEW ---\n%s\n"
                                % (seq, inp.get("path"), inp.get("oldString"), inp.get("newString")))
                    ne += 1
                elif nm in ("shell", "execute"):
                    cmd = inp.get("command") or inp.get("code") or ""
                    cmds.write("\n\n### %s seq=%s\n%s\n" % (nm, seq, cmd)); nc += 1
    with open(os.path.join(wdir, "INDEX.txt"), "w", encoding="utf-8") as g: g.write("\n".join(wi))
    for g in (notes, edits, cmds): g.close()
    idx.append("- `%s` (%s): writes=%d edits=%d cmds=%d" % (sid, label, nw, ne, nc))
    print(sid, "writes", nw, "edits", ne, "cmds", nc)
open(os.path.join(ROOT, "INDEX.md"), "w", encoding="utf-8").write("\n".join(idx) + "\n")
print("total written bytes:", tot)
