#!/bin/bash
F="$HOME/ghostlock/src/g9700/drivers/tty/tty_buffer.c"
echo "=== 55..85 ==="; sed -n '55,85p' "$F"
echo "=== 390..415 ==="; sed -n '390,415p' "$F"
echo "=== 585..610 ==="; sed -n '585,610p' "$F"
