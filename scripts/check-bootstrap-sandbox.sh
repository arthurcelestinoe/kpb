#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Validation harness only: this is not KPB's recipe executor.
set -euo pipefail

if [[ $# != 2 ]]; then
    printf 'Usage: bash %s RECIPE_TOOLS_STORE_PATH ORCHESTRATION_TOOLS_STORE_PATH\n' "$0" >&2
    exit 2
fi

recipe_tools=$1
orchestration_tools=$2
for bundle in "$recipe_tools" "$orchestration_tools"; do
    if [[ ! "$bundle" =~ ^/nix/store/[a-z0-9]{32}-[^/]+$ || ! -d "$bundle" ]]; then
        printf 'Expected an existing Nix store output directory: %s\n' "$bundle" >&2
        exit 2
    fi
done

for executable in "$recipe_tools/bin/bash" "$recipe_tools/bin/python3" \
    "$recipe_tools/bin/mktemp" "$orchestration_tools/bin/bwrap"; do
    if [[ ! -x "$executable" ]]; then
        printf 'Required bootstrap executable is missing: %s\n' "$executable" >&2
        exit 2
    fi
done
if [[ $("$recipe_tools/bin/id" -u) == 0 ]]; then
    printf 'Run the sandbox validation as an ordinary user, without sudo.\n' >&2
    exit 2
fi
if ! nix_binary=$(command -v nix); then
    printf 'Nix with nix-command support must already be available.\n' >&2
    exit 2
fi

script_dir=$(cd -- "$("$recipe_tools/bin/dirname" -- "${BASH_SOURCE[0]}")" && pwd -P)
probe="$script_dir/bootstrap-sandbox-probe.py"
if [[ ! -f "$probe" ]]; then
    printf 'Missing validation payload: %s\n' "$probe" >&2
    exit 2
fi

check_root=$("$recipe_tools/bin/mktemp" -d /tmp/kpb-bwrap-check.XXXXXXXX)
trap '"$recipe_tools/bin/rm" -rf -- "$check_root"' EXIT
"$recipe_tools/bin/mkdir" -p "$check_root"/{recipe,dependencies,private,workspace/{src,build,pkg}}
printf 'read-only recipe\n' > "$check_root/recipe/marker"
printf 'read-only dependency\n' > "$check_root/dependencies/marker"
printf 'synthetic host-only data\n' > "$check_root/private/host-marker"

# Only synthetic host metadata and a disposable socket are used as fixtures.
"$recipe_tools/bin/python3" - "$check_root" "$orchestration_tools" <<'PY'
import json
import os
from pathlib import Path
import socket
import sys

root = Path(sys.argv[1])
metadata = {
    "namespaces": {
        name: os.readlink(f"/proc/self/ns/{name}")
        for name in ("user", "mnt", "pid", "net", "ipc", "uts")
    },
    "hidden_marker": str(root / "private/host-marker"),
    "hidden_socket": str(root / "private/session.sock"),
    "orchestration_bundle": sys.argv[2],
}
(root / "host.json").write_text(json.dumps(metadata), encoding="utf-8")
with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as fixture:
    fixture.bind(str(root / "private/session.sock"))
PY

if ! "$nix_binary" path-info --recursive "$recipe_tools" > "$check_root/closure"; then
    printf 'Cannot query the recipe tools runtime closure; no sandbox payload was run.\n' >&2
    exit 1
fi
mapfile -t store_paths < "$check_root/closure"
if [[ ${#store_paths[@]} == 0 ]]; then
    printf 'Nix returned an empty runtime closure.\n' >&2
    exit 1
fi

bwrap_args=(
    --unshare-user --unshare-pid --unshare-net --unshare-ipc --unshare-uts
    --cap-drop ALL --new-session --die-with-parent
    --clearenv
    --dir /nix --dir /nix/store
)
for store_path in "${store_paths[@]}"; do
    if [[ ! "$store_path" =~ ^/nix/store/[a-z0-9]{32}-[^/]+$ ]]; then
        printf 'Unexpected runtime closure entry: %s\n' "$store_path" >&2
        exit 1
    fi
    bwrap_args+=(--ro-bind "$store_path" "$store_path")
done
bwrap_args+=(
    --ro-bind "$recipe_tools" /tools
    --ro-bind "$check_root/recipe" /recipe
    --ro-bind "$check_root/dependencies" /opt/kpb
    --ro-bind "$probe" /checks/probe.py
    --ro-bind "$check_root/host.json" /checks/host.json
    --bind "$check_root/workspace" /work
    --tmpfs /tmp
    --dir /tmp/home
    --dir /home --dir /etc
    --symlink /tools/bin/bash /bin/sh
    --symlink /tools/bin/bash /bin/bash
    --proc /proc --remount-ro /proc
    --dev /dev --remount-ro /dev
    --remount-ro /
    --setenv PATH /opt/kpb/bin:/tools/bin
    --setenv HOME /tmp/home
    --setenv TMPDIR /tmp
    --setenv LANG C --setenv LC_ALL C
    --setenv recipedir /recipe
    --setenv srcdir /work/src
    --setenv builddir /work/build
    --setenv pkgdir /work/pkg
    --setenv prefix /opt/kpb
    --chdir /work/src
)

# These fake session values must be removed by --clearenv.
if ! KPB_CHECK_HOST_ONLY=must-not-enter SSH_AUTH_SOCK="$check_root/private/session.sock" \
    "$orchestration_tools/bin/bwrap" "${bwrap_args[@]}" -- \
    /tools/bin/bash --noprofile --norc -e -o pipefail -c 'exec python3 /checks/probe.py'; then
    printf 'Bubblewrap setup or its validation payload failed. Required isolation was not disabled.\n' >&2
    printf 'Check unprivileged user namespaces and host policy; do not rerun without isolation.\n' >&2
    exit 1
fi

printf 'Bootstrap tools passed the Bubblewrap validation.\n'
