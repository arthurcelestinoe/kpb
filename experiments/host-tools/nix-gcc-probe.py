#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Read-only NixOS host-tool experiment; not a production adapter or package validator."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time


HERE = Path(__file__).resolve().parent
STORE = re.compile(r"/nix/store/[a-z0-9]{32}-[^/]+")


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def store_root(path):
    require(len(path.parts) >= 4 and path.parts[:3] == ("/", "nix", "store"),
            f"No supported ownership provider for candidate: {path}")
    root = Path(*path.parts[:4])
    require(STORE.fullmatch(str(root)), f"Invalid store output: {root}")
    return root


def query_closure(nix, root):
    command = [nix, "path-info", "--store", "daemon", "--offline", "--json", "--json-format", "1", "--recursive", str(root)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=60, check=True)
    data = json.loads(result.stdout)
    require(isinstance(data, dict) and str(root) in data, "Output is not registered in local Nix metadata")
    require(all(STORE.fullmatch(path) and Path(path).is_dir() for path in data), "Invalid closure entry")
    for path, metadata in data.items():
        require(metadata.get("narHash"), f"No registered content hash: {path}")
        require(all(reference in data for reference in metadata["references"]), "Incomplete reference closure")
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tool", default="gcc", help="Candidate name found through PATH")
    parser.add_argument("--expected-version", required=True, help="Exact GCC upstream version for this experiment")
    parser.add_argument("--bwrap", required=True, type=Path, help="Preinstalled Bubblewrap executable")
    parser.add_argument("--nix", type=Path, default=Path("/run/current-system/sw/bin/nix"),
                        help="Trusted, preinstalled local Nix CLI; never discovered through candidate PATH")
    parser.add_argument("--workdir", required=True, type=Path, help="New private output directory")
    parser.add_argument("--run", action="store_true", help="Also execute the prepared sandbox experiment")
    args = parser.parse_args()
    require(os.getuid() != 0, "Run as an ordinary user, without sudo")
    require(os.uname().machine == "x86_64", "This experiment is limited to native x86_64 Linux")
    require(re.fullmatch(r"[A-Za-z0-9_.+-]+", args.tool), "--tool must be a command name")
    require(re.fullmatch(r"[0-9]+\.[0-9]+(?:\.[0-9]+)?", args.expected_version), "Expected a GCC version literal")
    require(args.bwrap.is_absolute() and args.bwrap.is_file() and os.access(args.bwrap, os.X_OK), "Bubblewrap must already exist")
    require(args.nix.is_absolute() and args.nix.is_file() and os.access(args.nix, os.X_OK),
            "The Nix provider requires an explicit, already installed trusted Nix CLI")
    nix = str(args.nix.resolve(strict=True))
    found = shutil.which(args.tool)
    require(found is not None, f"No candidate in PATH: {args.tool}")
    discovered = Path(found).absolute()
    candidate = discovered.resolve(strict=True)
    owner = store_root(candidate)  # Reject unowned PATH shadows before execution.
    require(candidate.relative_to(owner) == Path("bin/gcc"), "This probe supports the Nix GCC wrapper only")
    root = args.workdir.absolute()
    require(not root.exists(), "--workdir must not exist")
    closure = query_closure(nix, owner)
    require((owner / "nix-support/orig-cc").is_file(), "Expected explicit Nix wrapper metadata")
    compiler = Path((owner / "nix-support/orig-cc").read_text().strip())
    require(STORE.fullmatch(str(compiler)) and str(compiler) in closure, "Compiler is outside registered closure")
    require((compiler / "bin/gcc").is_file(), "Registered compiler executable is missing")

    # Package version is optional evidence; never parse a store basename into it.
    deriver = closure[str(owner)].get("deriver")
    package_version = None
    package_version_evidence = "Derivation is unavailable locally; store name is a hint only"
    if deriver and Path(deriver).is_file():
        process = subprocess.run([nix, "derivation", "show", "--store", "daemon", "--offline", deriver], capture_output=True,
                                 text=True, timeout=60, check=True)
        derivations = json.loads(process.stdout)
        environment = next(iter(derivations.values()))["env"]
        package_version = environment.get("version")
        package_version_evidence = f"Local derivation env.version: {deriver}"

    root.mkdir(mode=0o700)
    started = time.monotonic()
    with (root / "verify.log").open("w") as log:
        verify = subprocess.run([nix, "store", "verify", "--store", "daemon", "--offline", "--no-trust", "--recursive", str(owner)],
                                stdout=log, stderr=subprocess.STDOUT, timeout=120)
    require(verify.returncode == 0, f"Registered content verification failed; see {root / 'verify.log'}")
    inputs = root / "inputs"
    inputs.mkdir()
    for name in ("probe.sh", "probe.c"):
        shutil.copyfile(HERE / name, inputs / name)
    (inputs / "readonly-marker").write_text("read-only fixture\n")
    tools = root / "tools/bin"
    tools.mkdir(parents=True)
    tools.joinpath("gcc").symlink_to(candidate)

    # Helper executables must also belong to this verified closure. This is a
    # deliberately narrow Nix wrapper probe, not generic wrapper interpretation.
    with candidate.open() as stream:
        shebang = stream.readline().strip()
    require(shebang.startswith("#!"), "Expected a script wrapper")
    bash = Path(shebang[2:].strip())
    require(str(store_root(bash)) in closure and bash.is_file(), "Interpreter is outside verified closure")
    helpers = {"bash": bash}
    for command in ("id", "readlink", "timeout", "grep", "readelf"):
        matches = sorted({(Path(path) / "bin" / command).resolve() for path in closure
                          if (Path(path) / "bin" / command).is_file()})
        require(len(matches) == 1, f"Missing or ambiguous closure helper {command}: {matches}")
        helpers[command] = matches[0]
    for name, path in helpers.items():
        require(str(store_root(path.resolve())) in closure, f"Helper symlink escapes verified closure: {path}")
        tools.joinpath(name).symlink_to(path)
    hidden = root / "host-only-marker"
    hidden.write_text("synthetic host-only data\n")
    work = root / "workspace"
    work.mkdir()
    host_namespaces = {name: os.readlink(f"/proc/self/ns/{name}") for name in ("user", "mnt", "pid", "net", "ipc", "uts")}
    manifest = {
        "status": "plan prepared; sandbox execution pending", "provider": "nix-local-store",
        "discovery_path": str(discovered), "canonical_executable": str(candidate),
        "executable_sha256": sha256(candidate), "owner_id": str(owner),
        "package_version": package_version, "package_version_evidence": package_version_evidence,
        "expected_tool_version": args.expected_version, "compiler_output": str(compiler),
        "content_integrity": "verified against registered NAR hashes; signature trust not checked",
        "closure": closure, "closure_count": len(closure), "closure_nar_bytes": sum(x["narSize"] for x in closure.values()),
        "mount_granularity": "individual registered package output directories, read-only",
        "host_namespaces": host_namespaces, "payload_sha256": {name: sha256(inputs / name) for name in ("probe.sh", "probe.c")},
        "nix_cli": nix, "nix_cli_sha256": sha256(Path(nix)), "nix_store": "local daemon",
        "bwrap": str(args.bwrap), "host_runtime_allowed": True, "package_accepted": False,
    }
    manifest_path = root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Verified plan: {manifest_path}; {len(closure)} package outputs", flush=True)
    if not args.run:
        return

    command = [str(args.bwrap), "--unshare-user", "--unshare-pid", "--unshare-net", "--unshare-ipc", "--unshare-uts",
               "--cap-drop", "ALL", "--new-session", "--die-with-parent", "--clearenv", "--dir", "/nix", "--dir", "/nix/store"]
    for path in sorted(closure):
        command += ["--ro-bind", path, path]
    command += ["--ro-bind", str(root / "tools"), "/tools", "--ro-bind", str(inputs), "/inputs",
                "--bind", str(work), "/work", "--tmpfs", "/tmp", "--dir", "/tmp/home", "--dir", "/etc",
                "--proc", "/proc", "--remount-ro", "/proc", "--dev", "/dev", "--remount-ro", "/dev",
                "--symlink", str(bash), "/bin/sh", "--remount-ro", "/",
                "--setenv", "PATH", "/tools/bin", "--setenv", "HOME", "/tmp/home",
                "--setenv", "TMPDIR", "/tmp", "--setenv", "LC_ALL", "C",
                "--setenv", "KPB_EXPECTED_VERSION", args.expected_version,
                "--setenv", "KPB_HIDDEN_MARKER", str(hidden), "--chdir", "/work", "--",
                str(bash), "--noprofile", "--norc", "/inputs/probe.sh"]
    environment = dict(os.environ, CPATH="/must-not-enter", GCC_EXEC_PREFIX="/must-not-enter/", KPB_HOST_ONLY="must-not-enter")
    with (root / "sandbox.log").open("w") as log:
        result = subprocess.run(command, env=environment, stdout=log, stderr=subprocess.STDOUT, timeout=60)
    if result.returncode != 0:
        manifest.update(status="sandbox experiment failed", sandbox_exit_code=result.returncode)
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    require(result.returncode == 0, f"Bubblewrap experiment failed ({result.returncode}); inspect {root / 'sandbox.log'}; no fallback used")
    for line in (work / "namespaces.tsv").read_text().splitlines():
        name, value = line.split("\t")
        require(value != host_namespaces[name], f"Namespace did not change: {name}")
    require((work / "tool-version.txt").read_text().strip() == args.expected_version, "Tool version mismatch")
    require((work / "target.txt").read_text().strip().startswith("x86_64-"), "Unexpected compiler target")
    require("PASS: installed host compiler" in (work / "result.txt").read_text(), "Compiled fixture did not run")
    require(discovered.resolve(strict=True) == candidate and sha256(candidate) == manifest["executable_sha256"],
            "Candidate changed during experiment")
    after = query_closure(nix, owner)
    require({p: m["narHash"] for p, m in closure.items()} == {p: m["narHash"] for p, m in after.items()},
            "Registered closure changed during experiment")
    manifest.update(status="host GCC experiment passed", effective_tool_version=args.expected_version,
                    target=(work / "target.txt").read_text().strip(),
                    elapsed_seconds=round(time.monotonic() - started, 3),
                    artifact_sha256=sha256(work / "probe"),
                    runtime_policy_result="validated host/Nix runtime permitted; complete package acceptance is not implemented",
                    checks=["registered ownership", "NAR content integrity", "exact tool version", "separate namespaces",
                            "cleared environment", "read-only mounts", "no host paths", "unreachable network",
                            "compile object", "link and execute host-runtime fixture", "identity recheck"])
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print((work / "result.txt").read_text().strip())
    print(f"PASS: controlled host tool reuse; manifest: {manifest_path}")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"Host-tool experiment failed: {error}", file=sys.stderr)
        sys.exit(1)
