# SESSION_RECOVERY.md — old ghostlock sessions, recovered code + the uid=0 story

This document records what was recovered from the **opencode session store**
(`opencode.db`, SQLite) for the ghostlock/beyond0q work, and the key finding about
**uid=0**.

## Sessions found (opencode.db → `session_v2`)

| session id | title | msgs | write | edit | shell |
|---|---|---|---|---|---|
| `ses_edefbadadffeWZZJZ53EDHXoZG` | Tiếp tục port GhostLock SM-G970W SLIDE shift 8 | 857 | 117 | 22 | 488 |
| `ses_edc7320bfffdQwPb3y1OEIvr0i` | GhostLock root SM-G970W: chốt KASLR slide | 436 | 86 | 10 | 287 |
| `ses_edbf99648ffdfG8zCHb7wE0wtJ` | GhostLock root SM-G970W: gỡ tường page_base | 604 | 100 | 4 | 376 |
| `ses_edcfe2bafffeemezROUjpI2PT7` | GhostLock port SM-G970W: thảo luận blocker waiter | 329 | 44 | 26 | 230 |
| `ses_ede63f6b5ffeN3g00KsudH7VHD` | Port GhostLock CVE-2026-43499 lên Galaxy S10e | 214 | 19 | 3 | 139 |
| `ses_edf7f7041ffeVunbqbIt64E3jW` | Kiểm tra điện thoại mới qua ADB | 562 | 111 | 13 | 234 |

(The bulk of the **uid=0** work is in `ses_edbf99648ffdfG8zCHb7wE0wtJ`.)

## What was recovered (`recovered/`)

For every session, all tool calls and text are extracted:

```
recovered/<session-id>/
  writes/                # every `write` call snapshot (seq-numbered) + INDEX.txt
  edits.md               # every `edit` call (path + old + new)
  commands.md            # every `shell`/`execute` command (incl. heredocs)
  notes.md               # assistant + user text
recovered/INDEX.md
```

Recovered: **477 `write` snapshots**, ~1750 shell commands, all edits and notes.
Only **7** written paths no longer exist on disk (mostly `_syntax_check.sh`,
`_kp_scan.py` scratch). Extraction tooling: `tools/scripts/_oc_extract.py`,
`tools/scripts/_oc_mine.py`.

> `notes.md` / `commands.md` are in the original language (mostly Vietnamese);
> `writes/*` are the raw code.

## The uid=0 story (from `ses_edbf…`, recovered notes)

1. **UMH reached uid=0 for real.** The UMH child (kernel-spawned
   `call_usermodehelper`) ran as uid 0 — proven by the marker file
   **`/data/local/tmp/umh_uid_0_euid_0_gid_0`** plus `umh: result … complete=1
   retval=0`. (The filename-encoded proof was introduced by `_dn_patchB11.py`
   precisely because `open()` worked but `write()` did not.)
2. **But the UMH child cannot write to `/data`.** `open(O_TRUNC)` fails with
   **`ENOKEY` (126)** — the kernel-spawned process lacks the `/data` **fscrypt
   keyring**. `/dev/null` writes work (returns 18); regular-file writes never land.
   ⇒ UMH gives uid 0 but **not a usable root shell** by itself. Defex LSM
   (SIGKILL paths) was noted as another suspect.
3. **Decision taken in that session:** the UMH path is **clean, no reset**
   (uptime 29 min observed): `cfi fops_before == want`, `umh: step1 selinux write
   ok`, `umh: result complete=1 retval=0`. The **reset only happens on the `cred`
   path**. So: use **UMH as the root vehicle**, and have the uid-0 UMH child open a
   **root shell daemon** (with an open-retry to warm the ENOKEY keyring first).
   The `cred` path was kept only as a fallback.
4. **The real recurring blocker is the walk.** Quote: "The B18 run hit the ~50%
   flaky walk crash (reboot)." Retries were automated to win the walk lottery.

## Consequence for "why uid=0 is not reproducible now"

- uid=0 was reached via the **UMH** path (B9-B11) and again kernel-side at B18
  (`_dn_e2e.log`: `retval=0`).
- The **current build (`glA5`) resets at the walk** in our runs (last log line
  `consumer: walk begin`, no `walk end`), so it never reaches UMH. The walk is
  ~50%-flaky; the likely-vs-B18 regression is unresolved.
- Even when UMH runs, the child's **ENOKEY** write failure blocks a file-based root
  script; the code now retries `open()` then forks the daemon, but the daemon has
  **never been confirmed working** (no `.ghostlock_rootshell` marker in any saved
  log).

## Where to look next

- Reproduce uid=0 directly: run the **B9/B10/B11** binaries with the UMH flags and
  look for the `umh_uid_0_euid_0_gid_0` / `umh_root_proof` marker.
- Settle the walk regression: run `glA5` vs `ghostlockB18` redirect-only
  (`ONLY_FOPS=1 CFI_STOP_VERIFY=1`) and count success vs reset.
- Fix the usable-root problem: either warm/replace the keyring for the UMH child,
  or make the `cred` path (a normal process, correct keyring) not reset.
