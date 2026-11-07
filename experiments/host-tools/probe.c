/* SPDX-License-Identifier: GPL-3.0-or-later */
#include <gnu/libc-version.h>
#include <stdio.h>

int main(void)
{
    printf("PASS: installed host compiler; glibc %s\n", gnu_get_libc_version());
    return 0;
}
