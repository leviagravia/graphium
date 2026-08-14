#!/usr/bin/env python3
"""Apples-to-apples FIRST_VISIBLE benchmark for Graphium and target comparators.

This metric intentionally ends at the first new mapped X11 top-level window for the exact
spawned PID. It is *not* FIRST_EDITABLE. The same external oracle is used for Graphium,
Leafpad, L3afpad, Mousepad and FeatherPad, so ratios within this receipt are methodologically valid.
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
    # Use only the conventional non-GUI --version probe.  Do not guess short options: in
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
    proc = subprocess.Popen(full, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        wid = find_new_window(proc, before, time.monotonic() + 15.0)
        if wid is None:
            raise RuntimeError(f"no new X11 top-level window for pid {proc.pid}: {full!r}")
        stamp = time.monotonic_ns()
        return (stamp - start) / 1_000_000.0, rss_mib(proc.pid)
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=3)
        time.sleep(0.05)


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
        raise SystemExit("FIRST_VISIBLE_BLOCKED: X11 DISPLAY required")
    if shutil.which("xprop") is None:
        raise SystemExit("FIRST_VISIBLE_BLOCKED: xprop missing")

    graphium = args.root / "bin/graphium"
    commands: dict[str, list[str]] = {"Graphium": [str(graphium)]}
    for name, exe in (("Leafpad", "leafpad"), ("L3afpad", "l3afpad"), ("Mousepad", "mousepad"), ("FeatherPad", "featherpad")):
        resolved = shutil.which(exe)
        if resolved is None:
            print(f"FIRST_VISIBLE_BLOCKED_MISSING={name}")
            raise SystemExit(3)
        commands[name] = [resolved]
    # The exact-spawned-PID oracle requires each comparator launch to own its
    # measured window. Mousepad can otherwise forward to its server; FeatherPad
    # is a single-instance application by default and can forward a new launch to
    # an already-running process. Keep the oracle strong: isolate the applications
    # instead of accepting a window owned by some unrelated/existing PID.
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
        raise SystemExit("FIRST_VISIBLE_BLOCKED: Mousepad running and installed build lacks --disable-server")

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
        raise SystemExit(
            "FIRST_VISIBLE_BLOCKED: FeatherPad build lacks --standalone; "
            "exact spawned-PID oracle requires process isolation"
        )

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
            "samples_sha256": hashes,
            "applications": {},
        }
        for name, cmd in commands.items():
            env = isolated_env(args.state_root, name)
            appres = {"command": cmd, "version": (graphium_version_from_source(args.root) if name == "Graphium" else version_text(cmd)), "workloads": {}}
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
                print(
                    f"FIRST_VISIBLE {name} {workload} "
                    f"median_ms={statistics.median(times):.3f} p90_ms={p90(times):.3f} "
                    f"rss_mib={statistics.median(memory):.2f}"
                )
            out["applications"][name] = appres

        graph = out["applications"]["Graphium"]["workloads"]
        mouse = out["applications"]["Mousepad"]["workloads"]
        gates = {
            "empty_le_2x_mousepad_or_750ms": graph["empty"]["median_ms"] <= 2 * mouse["empty"]["median_ms"] or graph["empty"]["median_ms"] <= 750.0,
            "5KiB_le_2x_mousepad_or_900ms": graph["5KiB"]["median_ms"] <= 2 * mouse["5KiB"]["median_ms"] or graph["5KiB"]["median_ms"] <= 900.0,
            "graphium_idle_rss_le_200MiB": graph["empty"]["median_rss_mib"] <= 200.0,
        }
        out["g04_first_visible_admission_gates"] = gates
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        if not all(gates.values()):
            print("G04_FIRST_VISIBLE_ADMISSION=FAIL")
            raise SystemExit(2)
        print("COMPARATOR_SET=Graphium,Leafpad,L3afpad,Mousepad,FeatherPad")
        print("COMPARATOR_METHOD=COMMON_EXTERNAL_FIRST_VISIBLE")
        print("G04_FIRST_VISIBLE_ADMISSION=PASS")
        print("FINAL_PHASE=G04_FIRST_VISIBLE_COMPARISON_PASS")


if __name__ == "__main__":
    main()
