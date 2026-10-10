/* Diagnostic-only runner: exercise root_shell_daemon() in a NORMAL (shell)
 * process, to isolate whether the daemon handler works vs the UMH-spawned
 * environment. Not part of the product build. */
#include "common.h"
#include <stdlib.h>

void root_shell_daemon(void);

int main(int argc, char **argv) {
  if (argc > 1) setenv("ROOTSHELL_PORT", argv[1], 1);
  root_shell_daemon();
  return 0;
}
