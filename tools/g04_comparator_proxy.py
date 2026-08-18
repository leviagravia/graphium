#!/usr/bin/env python3
"""Apples-to-apples FIRST_VISIBLE benchmark for Graphium and target comparators.

This metric intentionally ends at the first new mapped X11 top-level window for the exact
spawned PID. It is *not* FIRST_EDITABLE. The same external oracle is used for Graphium,
Leafpad, L3afpad, Mousepad and FeatherPad, so ratios within a complete receipt are
methodologically valid.

Comparator launch/window failures are infrastructure blocks, not Graphium product failures.
A blocked run writes the partial receipt collected so far (including Graphium when available)
and exits 3. No failed comparator sample is silently retried or discarded.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import statistics
import subprocess
import tempfile
import time


class ComparatorBlocked(RuntimeError):
    pass


def p90(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[max(0, math.ceil(0.90 * len(ordered)) - 1)]


def rss_mib(pid: int) -> float:
    try:
        for line in Path(f"/proc/{pid}/status").read_text().splitlines():
            if line.startswith("VmRSS:"):
                return float(line.split()[1]) / 1024.0
    except OSError:
        pass
    return float("nan")


def root_windows() -> set[str]:
    p = subprocess.run(
        ["xprop", "-root", "_NET_CLIENT_LIST"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if p.returncode != 0:
        return set()
    return set(re.findall(r"0x[0-9a-fA-F]+", p.stdout))


def pid_for_window(wid: str) -> int | None:
    p = subprocess.run(
        ["xprop", "-id", wid, "_NET_WM_PID"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    m = re.search(r"=\s*(\d+)", p.stdout)
    return int(m.group(1)) if m else None


def windows_for_pid(pid: int) -> set[str]:
    return {wid for wid in root_windows() if pid_for_window(wid) == pid}


def wait_pid_windows_gone(pid: int, deadline: float) -> bool:
    """Wait for the WM/EWMH client list to quiesce after a measured process exits.

    Mature comparators have different process models, but once Graphium has forced a
    direct-owner/non-unique/standalone launch, the measured PID must own the measured window.
    We therefore keep the exact-PID oracle and make the inter-run X11 boundary explicit.
    """
    while time.monotonic() < deadline:
        if not windows_for_pid(pid):
            return True
        time.sleep(0.01)
    return not windows_for_pid(pid)


def find_new_window(proc: subprocess.Popen, before: set[str], deadline: float) -> str | None:
    while time.monotonic() < deadline:
        for wid in root_windows() - before:
            if pid_for_window(wid) == proc.pid:
                return wid
        if proc.poll() is not None:
            return None
        time.sleep(0.005)
    return None


def make_file(path: Path, size: int) -> None:
    line = b"Graphium comparator benchmark 0123456789 abcdefghijklmnopqrstuvwxyz\n"
    with path.open("wb") as f:
        left = size
        while left:
            chunk = line[: min(left, len(line))]
            f.write(chunk)
            left -= len(chunk)


def graphium_version_from_source(root: Path) -> str:
    # Avoid spawning the product merely to ask its version: G04 has not frozen a CLI
    # --version contract, and an unsupported option must not create/perturb benchmark windows.
    product = (root / "graphium" / "product.py").read_text(encoding="utf-8")
    match = re.search(r'^VERSION\s*=\s*["\']([^"\']+)["\']', product, re.MULTILINE)
    return f"Graphium {match.group(1)}" if match else "Graphium version unavailable"


def version_text(cmd: list[str]) -> str:
    # Use only the conventional non-GUI --version probe. Do not guess short options: in
    # small editors -v may mean something unrelated and may create a window, contaminating
    # the benchmark state.
    try:
        p = subprocess.run(
            [cmd[0], "--version"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=2,
            check=False,
        )
        if p.stdout.strip():
            return p.stdout.strip().splitlines()[0][:200]
    except Exception:
        pass
    return "version unavailable"


def run_once(cmd: list[str], sample: Path | None, env: dict[str, str]) -> tuple[float, float]:
    before = root_windows()
    full = cmd + ([str(sample)] if sample else [])
    start = time.monotonic_ns()
    with tempfile.TemporaryFile(mode="w+t", encoding="utf-8") as capture:
        proc = subprocess.Popen(full, env=env, stdout=capture, stderr=subprocess.STDOUT, text=True)
        result: tuple[float, float] | None = None
        block_reason: str | None = None
        try:
            wid = find_new_window(proc, before, time.monotonic() + 15.0)
            if wid is None:
                current = root_windows()
                owned = sorted(w for w in current if pid_for_window(w) == proc.pid)
                block_reason = (
                    f"no new X11 top-level window for exact spawned pid={proc.pid}; "
                    f"returncode_before_cleanup={proc.poll()!r}; command={full!r}; "
                    f"before_windows={len(before)} current_windows={len(current)} owned_windows={owned!r}"
                )
            else:
                stamp = time.monotonic_ns()
                result = ((stamp - start) / 1_000_000.0, rss_mib(proc.pid))
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=3)
            quiesced = wait_pid_windows_gone(proc.pid, time.monotonic() + 2.0)
            capture.flush()
            capture.seek(0)
            output = capture.read()[-2000:].strip()

        if not quiesced:
            raise ComparatorBlocked(
                f"X11 top-level(s) for exited pid={proc.pid} did not quiesce; "
                f"remaining={sorted(windows_for_pid(proc.pid))!r}; command={full!r}; output={output!r}"
            )
        if block_reason is not None:
            raise ComparatorBlocked(f"{block_reason}; output={output!r}")
        if result is None:
            raise ComparatorBlocked(f"no measurement result for pid={proc.pid}; command={full!r}")
        return result


def isolated_env(root: Path, name: str) -> dict[str, str]:
    env = dict(os.environ)
    env["GDK_BACKEND"] = "x11"
    home = root / name.lower().replace(" ", "-")
    home.mkdir(parents=True, exist_ok=True)
    for sub in ("config", "data", "cache", "state"):
        (home / sub).mkdir(exist_ok=True)
    env.update(
        {
            "HOME": str(home),
            "XDG_CONFIG_HOME": str(home / "config"),
            "XDG_DATA_HOME": str(home / "data"),
            "XDG_CACHE_HOME": str(home / "cache"),
            "XDG_STATE_HOME": str(home / "state"),
        }
    )
    return env


def write_receipt(path: Path, out: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--receipt", type=Path, required=True)
    ap.add_argument("--runs", type=int, default=7)
    ap.add_argument("--state-root", type=Path, required=True)
    args = ap.parse_args()
    if args.runs < 7:
        raise SystemExit("FIRST_VISIBLE_FAIL: need >=7 measured runs")
    if not os.environ.get("DISPLAY"):
        print("FIRST_VISIBLE_COMPARATOR_BLOCKED=X11_DISPLAY_MISSING")
        raise SystemExit(3)
    if shutil.which("xprop") is None:
        print("FIRST_VISIBLE_COMPARATOR_BLOCKED=XPROP_MISSING")
        raise SystemExit(3)

    graphium = args.root / "bin/graphium"
    commands: dict[str, list[str]] = {"Graphium": [str(graphium)]}
    preflight_blocks: dict[str, str] = {}
    for name, exe in (("Leafpad", "leafpad"), ("L3afpad", "l3afpad"), ("Mousepad", "mousepad"), ("FeatherPad", "featherpad")):
        resolved = shutil.which(exe)
        if resolved is None:
            preflight_blocks[name] = "executable missing"
        else:
            commands[name] = [resolved]

    # Direct mature-source ownership models; exact spawned-PID oracle requires process isolation:
    # - Leafpad/L3afpad: direct process owns GtkWindow; no server indirection.
    # - Mousepad: --disable-server switches GApplication to NON_UNIQUE.
    # - FeatherPad: --standalone guarantees a separate owning process/window.
    if "Mousepad" in commands:
        mouse_help = subprocess.run(
            [commands["Mousepad"][0], "--help-all"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=3,
            check=False,
        )
        if "--disable-server" in mouse_help.stdout:
            commands["Mousepad"].append("--disable-server")
        elif subprocess.run(["pgrep", "-x", "mousepad"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
            preflight_blocks["Mousepad"] = "running and installed build lacks --disable-server"
            commands.pop("Mousepad")

    if "FeatherPad" in commands:
        feather_help = subprocess.run(
            [commands["FeatherPad"][0], "--help"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=3,
            check=False,
        )
        if "--standalone" in feather_help.stdout:
            commands["FeatherPad"].append("--standalone")
        else:
            preflight_blocks["FeatherPad"] = "installed build lacks --standalone"
            commands.pop("FeatherPad")

    with tempfile.TemporaryDirectory(prefix="graphium-first-visible-") as td:
        temp = Path(td)
        workloads = {
            "empty": None,
            "5KiB": temp / "5k.txt",
            "1MiB": temp / "1m.txt",
            "10MiB": temp / "10m.txt",
        }
        make_file(workloads["5KiB"], 5 * 1024)
        make_file(workloads["1MiB"], 1024 * 1024)
        make_file(workloads["10MiB"], 10 * 1024 * 1024)
        hashes = {k: (hashlib.sha256(v.read_bytes()).hexdigest() if v else None) for k, v in workloads.items()}
        out = {
            "metric": "FIRST_VISIBLE",
            "oracle": "external process start -> first new X11 top-level mapped for exact spawned PID",
            "cross_product_comparable": True,
            "first_editable_claim": False,
            "runs_measured": args.runs,
            "priming_runs": 1,
            "inter_run_boundary": "wait until no X11 top-level remains for exited measured PID",
            "failed_samples_retried": False,
            "samples_sha256": hashes,
            "applications": {},
            "status": "RUNNING",
        }
        write_receipt(args.receipt, out)

        for name, cmd in commands.items():
            env = isolated_env(args.state_root, name)
            appres = {
                "command": cmd,
                "version": (graphium_version_from_source(args.root) if name == "Graphium" else version_text(cmd)),
                "workloads": {},
            }
            try:
                for workload, sample in workloads.items():
                    run_once(cmd, sample, env)
                    times: list[float] = []
                    memory: list[float] = []
                    for _ in range(args.runs):
                        ms, mem = run_once(cmd, sample, env)
                        times.append(ms)
                        memory.append(mem)
                    appres["workloads"][workload] = {
                        "times_ms": times,
                        "median_ms": statistics.median(times),
                        "p90_ms": p90(times),
                        "median_rss_mib": statistics.median(memory),
                    }
                    out["applications"][name] = appres
                    write_receipt(args.receipt, out)
                    print(
                        f"FIRST_VISIBLE {name} {workload} "
                        f"median_ms={statistics.median(times):.3f} p90_ms={p90(times):.3f} "
                        f"rss_mib={statistics.median(memory):.2f}"
                    )
            except ComparatorBlocked as exc:
                out["applications"][name] = appres
                out["status"] = "BLOCKED"
                out["blocked_application"] = name
                out["blocked_reason"] = str(exc)
                write_receipt(args.receipt, out)
                print(f"FIRST_VISIBLE_COMPARATOR_BLOCKED={name}")
                print(f"FIRST_VISIBLE_BLOCK_REASON={exc}")
                print("CLASSIFICATION=COMPARATOR_OR_X11_INFRASTRUCTURE_BLOCK_NOT_PRODUCT_FAIL")
                raise SystemExit(3)

        if preflight_blocks:
            out["status"] = "BLOCKED"
            out["preflight_blocks"] = preflight_blocks
            write_receipt(args.receipt, out)
            print("FIRST_VISIBLE_COMPARATOR_BLOCKED=PREFLIGHT")
            print(f"FIRST_VISIBLE_PREFLIGHT_BLOCKS={json.dumps(preflight_blocks, sort_keys=True)}")
            print("CLASSIFICATION=COMPARATOR_PREREQUISITE_BLOCK_NOT_PRODUCT_FAIL")
            raise SystemExit(3)

        required = ("Graphium", "Leafpad", "L3afpad", "Mousepad", "FeatherPad")
        missing = [name for name in required if name not in out["applications"]]
        if missing:
            out["status"] = "BLOCKED"
            out["missing_applications"] = missing
            write_receipt(args.receipt, out)
            print(f"FIRST_VISIBLE_COMPARATOR_BLOCKED=MISSING_RESULTS:{','.join(missing)}")
            raise SystemExit(3)

        graph = out["applications"]["Graphium"]["workloads"]
        mouse = out["applications"]["Mousepad"]["workloads"]
        gates = {
            "empty_le_2x_mousepad_or_750ms": graph["empty"]["median_ms"] <= 2 * mouse["empty"]["median_ms"] or graph["empty"]["median_ms"] <= 750.0,
            "5KiB_le_2x_mousepad_or_900ms": graph["5KiB"]["median_ms"] <= 2 * mouse["5KiB"]["median_ms"] or graph["5KiB"]["median_ms"] <= 900.0,
            "graphium_idle_rss_le_200MiB": graph["empty"]["median_rss_mib"] <= 200.0,
        }
        out["g04_first_visible_admission_gates"] = gates
        out["status"] = "PASS" if all(gates.values()) else "FAIL"
        write_receipt(args.receipt, out)
        if not all(gates.values()):
            print("G04_FIRST_VISIBLE_ADMISSION=FAIL")
            raise SystemExit(2)
        print("COMPARATOR_SET=Graphium,Leafpad,L3afpad,Mousepad,FeatherPad")
        print("COMPARATOR_METHOD=COMMON_EXTERNAL_FIRST_VISIBLE")
        print("G04_FIRST_VISIBLE_ADMISSION=PASS")
        print("FINAL_PHASE=G04_FIRST_VISIBLE_COMPARISON_PASS")


if __name__ == "__main__":
    main()
