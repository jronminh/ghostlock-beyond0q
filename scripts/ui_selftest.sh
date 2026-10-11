#!/system/bin/sh
# ui_selftest.sh — run ON THE DEVICE (after arming) to verify the root UI.
#   adb push scripts/ui_selftest.sh /data/local/tmp/; adb shell sh /data/local/tmp/ui_selftest.sh
# Exits non-zero if any check fails.
R=/data/local/tmp
fail=0
ok(){ echo "ok   - $1"; }
bad(){ echo "FAIL - $1"; fail=1; }

echo "== file channel =="
printf 'echo CHAN_OK\n' > $R/rcmd
sleep 1
case "$(cat $R/rout)" in *CHAN_OK*) ok "file channel (rcmd->rout)";; *) bad "file channel";; esac

echo "== HTTP page =="
P=$(curl -s -m5 http://127.0.0.1:8080/)
case "$P" in
  *ghostlock*) ok "page served";;
  *) bad "page not served";;
esac
T=$(printf '%s' "$P" | tr -d '\r' | awk -F'"' '/TOKEN =/{print $2; exit}')
[ -n "$T" ] && ok "token extracted" || bad "no token"

echo "== /api/status =="
S=$(curl -s -m5 -H "X-GL-Token: $T" http://127.0.0.1:8080/api/status)
case "$S" in *'"uid":0'*) ok "uid=0";; *) bad "status: $S";; esac
case "$S" in *Permissive*) ok "selinux permissive";; *) bad "selinux";; esac
case "$S" in *'"ctx":"u:r:kernel:s0"'*) ok "ctx u:r:kernel:s0";; *) bad "ctx";; esac

echo "== /api/exec =="
X=$(curl -s -m8 -X POST -H "X-GL-Token: $T" --data 'cmd=/system/bin/id' http://127.0.0.1:8080/api/exec)
case "$X" in *'uid=0(root)'*) ok "root exec";; *) bad "exec: $X";; esac

echo "== /api/prop =="
PR=$(curl -s -m8 -X POST -H "X-GL-Token: $T" --data 'op=set&name=debug.gl.uitest&value=hello' http://127.0.0.1:8080/api/prop)
case "$PR" in *'"value":"hello"'*) ok "setprop read-back";; *) bad "prop: $PR";; esac

echo "== token enforcement =="
PB=$(curl -s -m5 -o /dev/null -w '%{http_code}' -H 'X-GL-Token: bad' http://127.0.0.1:8080/api/status)
[ "$PB" = "403" ] && ok "bad token -> 403" || bad "token not enforced ($PB)"

echo "== done: fail=$fail =="
exit $fail
