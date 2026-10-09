#!/bin/bash
G="$HOME/ghostlock/src/g9700/security/selinux"
echo "=== definitions / uses of selinux_enforcing ==="
grep -rn "selinux_enforcing" "$G" | head -20
echo
echo "=== enforcing_enabled / selinux_state.enforcing ==="
grep -rn -e "enforcing_enabled" -e "state->enforcing" -e "selinux_state.enforcing" "$G" | head -20
echo
echo "=== struct selinux_state ==="
awk '/^struct selinux_state \{/{f=1} f{print} f&&/^\};/{exit}' "$G"/include/*.h "$G"/ss/*.h 2>/dev/null | head -40
grep -rn "struct selinux_state {" "$G" | head
