# Bootstrap tools in Bubblewrap

## Implemented validation

[scripts/check-bootstrap-sandbox.sh](../scripts/check-bootstrap-sandbox.sh) and its [Python payload](../scripts/bootstrap-sandbox-probe.py) provide a reproducible, synthetic host check for the tools supplied by the [bootstrap flake](bootstrap-flake.md). This is a validation harness, not KPB's recipe executor or a finalized production sandbox policy.

The harness does not read recipes, inspect real credentials, install into the system, or modify Nix configuration/profiles. It creates disposable fixtures under `/tmp`, exposes only the recipe tools' runtime closure and synthetic inputs to the payload, and removes its temporary directory on exit. The Python file is trusted test code, using the already selected bootstrap Python; KPB's implementation language remains Rust.

Run as an ordinary user, without sudo. The selected Bubblewrap 0.12.0 and the host must support unprivileged user, mount, PID, network, IPC, and UTS namespaces. The check stops on setup or payload failure and never retries with weaker protection.

## Prototype layout

| Sandbox path | Source and access |
|---|---|
| `/nix/store/<path>` | Individual entries from `nix path-info --recursive` on the recipe bundle, each read-only. The host store as a whole is not mounted. |
| `/tools` | Recipe tool bundle, read-only; its symlinks resolve through the mounted runtime closure. |
| `/opt/kpb` | A synthetic dependency directory, read-only. No real packages or host prefix are used. |
| `/recipe` | Synthetic recipe input directory, read-only; contains no executable recipe. |
| `/checks` | Trusted payload and generated host namespace metadata, read-only. |
| `/work` | The harness's disposable workspace, writable; contains `src`, `build`, and `pkg`. |
| `/tmp` | Private writable tmpfs, with a private `/tmp/home`. |
| `/home`, `/etc` | Empty directories on the read-only sandbox root. |
| `/bin/sh`, `/bin/bash` | Links to the selected bootstrap Bash, not host shells. |
| `/proc` | New PID-namespace procfs, remounted read-only. |
| `/dev` | Bubblewrap's minimal device view, remounted read-only; no host device directory bind. |
| `/` | Synthetic root, remounted read-only after setup. |

The orchestration bundle, host `/usr`, `/run`, home contents, and Nix daemon socket are not mounted. Bootstrap runtime libraries remain available because the tools need them; they are not final KPB package dependencies.

The prototype uses explicit namespace isolation, `--cap-drop ALL`, `--new-session`, `--die-with-parent`, and `--clearenv`. Its payload runs as a non-root UID with no effective capabilities and `no_new_privs` enabled. It receives the controlled PATH `/opt/kpb/bin:/tools/bin`, C locale, private HOME/TMPDIR, and recipe directory variables. No host PATH, startup files, SSH-agent setting, loader settings, or session bus address are imported.

These arguments are specific to the validation prototype. They demonstrate a feasible baseline on the tested host, not identical support on every distribution. See the [Bubblewrap security model](https://github.com/containers/bubblewrap#sandbox-security).

## Running the check

Build the selected bundles from the existing lock and pass their store paths explicitly:

```sh
kpb_recipe_tools=$(nix build --no-update-lock-file --no-link --print-out-paths .#bootstrap-recipe-tools)
kpb_orchestration_tools=$(nix build --no-update-lock-file --no-link --print-out-paths .#bootstrap-orchestration-tools)
bash scripts/check-bootstrap-sandbox.sh "$kpb_recipe_tools" "$kpb_orchestration_tools"
```

For untracked flake files, use the two-file temporary source workflow in [bootstrap-flake.md](bootstrap-flake.md#requirements-and-commands) and its `path:` reference for the build commands. The harness and payload stay in the workspace.

Nix must already be available to query the local runtime closure; the harness neither updates the lock nor resolves a channel. Its setup uses the selected bundles, while the payload runs under the selected Bash/Python with a cleared environment. It does not expose the Nix command or daemon to that payload.

An agent runner, container, LSM, or other outer sandbox may itself prevent namespace creation or netlink operations. Diagnose that restriction in the test output; do not disable network/user isolation, use `--unshare-*-try`, or treat an unexecuted payload as a pass. Running this check outside an agent sandbox still runs its payload inside Bubblewrap and does not mean running as root or changing host policy.

## What is checked

- User, mount, PID, network, IPC, and UTS namespace identifiers differ from the invoking process; the payload is non-root, capability-free, and has `no_new_privs`.
- Directory variables and PATH have the expected values; synthetic host environment values and common credential/session/loader settings are absent.
- A real disposable host marker and Unix socket node are inaccessible, as are the orchestration bundle and host-only paths. No real user credential or session socket is opened.
- Inputs and root/proc/device mounts are read-only. Attempts to write the synthetic recipe/dependency markers or sandbox root fail, while workspace, staging, and private temporary writes work.
- Only the private loopback interface may exist. After namespace/interface checks, a numeric TEST-NET connection attempt fails with an unreachable-network error; it does not rely on DNS or a public service being available.
- A representative command for each of the 18 selected recipe tool entries executes, and Gawk performs the MPFR precision check.
- Make and GCC compile a synthetic C function to an ELF64 x86_64 object, readelf inspects it, and `install` copies a synthetic file under `$pkgdir/opt/kpb`.

The compilation deliberately stops at an object file. It does not claim to link or run an executable against a KPB-built glibc, or prove independence from Nix at runtime.

## Executed result and remaining work

On 2026-11-07, the full harness passed on the current native x86_64 NixOS host with the pinned bundles and Bubblewrap 0.12.0. An initial minimal probe inside the agent's outer sandbox was denied creation of a netlink route socket. The same namespace probe and the full harness passed outside that restriction, without changing host configuration or reducing the Bubblewrap protections. Syntax checks were also run for the Bash harness and Python payload.

This check is separate from `nix flake check`, whose build sandbox may restrict nested user namespaces. A passing flake tool check is not a substitute for this host capability/execution check.

The production executor, per-stage write permissions, namespace nesting policy, resource limits, syscall filtering, interruption handling, real dependency composition, and final runtime validation still need implementation or decisions. In particular, this harness gives all tested actions the same writable workspace; it does not enforce the narrower `package()` contract per recipe stage. The kernel is shared with the host, and successful synthetic tests are not a proof against every escape or denial of service.
