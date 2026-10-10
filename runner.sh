#!/system/bin/sh
# file-driven command runner: executes whatever is in /data/local/tmp/rcmd,
# writes output to /data/local/tmp/rout. Meant to be made root via cred repoint.
while :; do
  if [ -s /data/local/tmp/rcmd ]; then
    sh /data/local/tmp/rcmd > /data/local/tmp/rout 2>&1
    : > /data/local/tmp/rcmd
  fi
  sleep 1
done
