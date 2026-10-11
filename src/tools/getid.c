#include <stdio.h>
#include <unistd.h>
int main(void) {
  printf("uid=%d euid=%d gid=%d egid=%d\n", getuid(), geteuid(), getgid(), getegid());
  return 0;
}
