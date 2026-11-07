#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Trusted, NixOS-specific investigation payload; not a recipe executor.
set -euo pipefail
[[ $(id -u) != 0 ]]
for variable in CPATH C_INCLUDE_PATH CPLUS_INCLUDE_PATH COMPILER_PATH LIBRARY_PATH \
    GCC_EXEC_PREFIX LD_PRELOAD LD_LIBRARY_PATH SSH_AUTH_SOCK KPB_HOST_ONLY; do
    [[ ! -v $variable ]]
done
for path in /usr /run /home /nix/var/nix/daemon-socket/socket /etc/ld.so.cache \
    "$KPB_HIDDEN_MARKER"; do
    [[ ! -e $path ]]
done
for name in user mnt pid net ipc uts; do
    printf '%s\t%s\n' "$name" "$(readlink "/proc/self/ns/$name")"
done > /work/namespaces.tsv
while IFS=: read -r key value; do
    case $key in
        CapEff) [[ ${value//[[:space:]]/} == 0000000000000000 ]] ;;
        NoNewPrivs) [[ ${value//[[:space:]]/} == 1 ]] ;;
    esac
done < /proc/self/status

# Verify mount modes without writing into host-managed package files.
while read -r mount_id parent device filesystem_root mountpoint options rest; do
    if [[ $mountpoint == / || $mountpoint == /tools || $mountpoint == /inputs \
        || $mountpoint == /nix/store/* ]]; then
        [[ ,$options, == *,ro,* ]]
    fi
done < /proc/self/mountinfo
if printf forbidden > /inputs/readonly-marker 2>/work/readonly.stderr; then
    printf 'Read-only fixture was writable\n' >&2
    exit 1
fi
if timeout 2 bash -c 'echo probe > /dev/tcp/192.0.2.1/9' 2>/work/network.stderr; then
    printf 'Unexpected external network access\n' >&2
    exit 1
else
    status=$?
    [[ $status != 124 ]]
    grep -q 'Network is unreachable' /work/network.stderr
fi

actual=$(gcc -dumpfullversion -dumpversion)
printf '%s\n' "$actual" > /work/tool-version.txt
if [[ $actual != "$KPB_EXPECTED_VERSION" ]]; then
    printf 'Tool version mismatch: required %s, actual %s\n' "$KPB_EXPECTED_VERSION" "$actual" >&2
    exit 1
fi
gcc --version > /work/tool-banner.txt
gcc -dumpmachine > /work/target.txt
gcc -print-search-dirs > /work/search-dirs.txt
gcc -O2 -Wall -Wextra -Werror -c /inputs/probe.c -o /work/probe.o
gcc -O2 -Wall -Wextra -Werror /inputs/probe.c -Wl,-Map,/work/probe.map -o /work/probe
readelf -h /work/probe.o > /work/object-elf.txt
readelf -l -d /work/probe > /work/runtime-elf.txt
/work/probe > /work/result.txt
