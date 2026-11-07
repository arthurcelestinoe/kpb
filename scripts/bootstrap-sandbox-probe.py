#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Trusted synthetic tests for the bootstrap sandbox; never executes recipes."""

import errno
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def run(*arguments):
    result = subprocess.run(arguments, capture_output=True, text=True, check=False)
    require(
        result.returncode == 0,
        f"Command failed: {arguments!r}\n{result.stdout}{result.stderr}",
    )
    return result.stdout


def require_write_denied(path):
    try:
        with path.open("a", encoding="utf-8") as output:
            output.write("unexpected write\n")
    except OSError as error:
        require(
            error.errno in (errno.EROFS, errno.EACCES, errno.EPERM),
            f"Unexpected write error for {path}: {error}",
        )
    else:
        raise RuntimeError(f"Write unexpectedly allowed: {path}")


def check_namespaces(host):
    for name, previous in host["namespaces"].items():
        require(
            os.readlink(f"/proc/self/ns/{name}") != previous,
            f"Host {name} namespace is still shared",
        )
    status = dict(
        line.split(":", 1) for line in Path("/proc/self/status").read_text().splitlines()
    )
    require(os.geteuid() != 0, "Payload must not run as root")
    require(status["NoNewPrivs"].strip() == "1", "no_new_privs is not enabled")
    require(int(status["CapEff"].strip(), 16) == 0, "Payload retains capabilities")
    print("PASS: namespaces, unprivileged identity, and privilege restrictions", flush=True)


def check_environment(host):
    expected = {
        "PATH": "/opt/kpb/bin:/tools/bin",
        "HOME": "/tmp/home",
        "TMPDIR": "/tmp",
        "LANG": "C",
        "LC_ALL": "C",
        "recipedir": "/recipe",
        "srcdir": "/work/src",
        "builddir": "/work/build",
        "pkgdir": "/work/pkg",
        "prefix": "/opt/kpb",
    }
    for name, value in expected.items():
        require(os.environ.get(name) == value, f"Unexpected environment setting: {name}")
    for name in (
        "KPB_CHECK_HOST_ONLY", "SSH_AUTH_SOCK", "DBUS_SESSION_BUS_ADDRESS",
        "LD_PRELOAD", "LD_LIBRARY_PATH", "PYTHONPATH", "BASH_ENV", "ENV",
    ):
        require(name not in os.environ, f"Host environment leaked: {name}")
    for path in (
        "/usr", "/run", "/nix/var/nix/daemon-socket/socket",
        host["hidden_marker"], host["hidden_socket"], host["orchestration_bundle"],
    ):
        require(not os.path.lexists(path), f"Host-only path is exposed: {path}")
    require(list(Path("/home").iterdir()) == [], "Unexpected home contents")
    for command in ("curl", "bwrap", "nix", "git", "tar", "gzip", "xz"):
        require(shutil.which(command) is None, f"Unexpected recipe PATH tool: {command}")
    print("PASS: environment, host paths, and recipe/orchestration separation", flush=True)


def check_filesystem():
    for path in ("/", "/tools", "/recipe", "/opt/kpb", "/nix/store", "/proc", "/dev"):
        require(os.statvfs(path).f_flag & os.ST_RDONLY, f"Mount is not read-only: {path}")
    require_write_denied(Path("/recipe/marker"))
    require_write_denied(Path("/opt/kpb/marker"))
    require_write_denied(Path("/root-write-probe"))
    for path in ("/work/src", "/work/build", "/work/pkg", "/tmp", "/tmp/home"):
        marker = Path(path) / "write-probe"
        marker.write_text("private writable data\n", encoding="utf-8")
        require(marker.read_text() == "private writable data\n", f"Cannot use {path}")
    print("PASS: read-only inputs and private writable work areas", flush=True)


def check_network():
    require(
        {name for _, name in socket.if_nameindex()} <= {"lo"},
        "An external network interface is exposed",
    )
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connection:
        connection.settimeout(1)
        try:
            connection.connect(("192.0.2.1", 9))
        except OSError as error:
            require(
                error.errno in (errno.ENETUNREACH, errno.EHOSTUNREACH),
                f"Expected an unreachable external network, got: {error}",
            )
        else:
            raise RuntimeError("External network connection unexpectedly succeeded")
    print("PASS: external networking is unreachable", flush=True)


def check_tools():
    commands = (
        ("bash", "--version"), ("cp", "--version"), ("find", "--version"),
        ("diff", "--version"), ("grep", "--version"), ("sed", "--version"),
        ("gawk", "--version"), ("make", "--version"), ("gcc", "--version"),
        ("ld", "--version"), ("bison", "--version"), ("m4", "--version"),
        ("python3", "--version"), ("perl", "-e", 'print "$^V\n";'),
        ("makeinfo", "--version"), ("msgfmt", "--version"),
        ("patch", "--version"), ("rsync", "--version"),
    )
    for command in commands:
        run(*command)
    run(
        "gawk", "-M", "-v", "PREC=256",
        'BEGIN { if (sprintf("%.0f", (2 ^ 100) + 1) != '
        '"1267650600228229401496703205377") exit 1 }',
    )
    print("PASS: all 18 bootstrap tool roles execute, including Gawk MPFR", flush=True)


def check_compilation_and_staging():
    Path("/work/src/probe.c").write_text(
        "int kpb_probe(void) { return 42; }\n", encoding="utf-8"
    )
    Path("/work/build/Makefile").write_text(
        "probe.o: ../src/probe.c\n\t$(CC) -c $< -o $@\n", encoding="utf-8"
    )
    run("make", "-C", "/work/build", "CC=cc", "probe.o")
    elf = Path("/work/build/probe.o").read_bytes()
    require(elf[:6] == b"\x7fELF\x02\x01", "Expected a little-endian ELF64 object")
    require(int.from_bytes(elf[18:20], "little") == 62, "Expected an x86_64 object")
    run("readelf", "--file-header", "/work/build/probe.o")
    staged = Path("/work/pkg/opt/kpb/share/kpb-check/probe.c")
    run("install", "-Dm644", "/work/src/probe.c", str(staged))
    require(staged.read_bytes() == Path("/work/src/probe.c").read_bytes(), "Staging failed")
    print("PASS: Make/GCC compile an x86_64 object and install writes only to staging", flush=True)


def main():
    host = json.loads(Path("/checks/host.json").read_text(encoding="utf-8"))
    check_namespaces(host)
    check_environment(host)
    check_filesystem()
    check_network()
    check_tools()
    check_compilation_and_staging()


if __name__ == "__main__":
    main()
