#!/usr/bin/env python3
"""Graphium exact FIRST_EDITABLE benchmark using an inherited pipe handshake."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import select
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


def make_file(path: Path, size: int) -> None:
    line = b"Graphium quick edit benchmark line 0123456789 abcdefghijklmnopqrstuvwxyz\n"
    with path.open("wb") as f:
        left = size
        while left:
            chunk = line[: min(left, len(line))]
            f.write(chunk)
            left -= len(chunk)


def _read_ready_line(fd: int, proc: subprocess.Popen, timeout: float = 15.0) -> bytes:
    deadline = time.monotonic() + timeout
    data = bytearray()
    # Pipe readability is the synchronization oracle.  Do not inspect process exit before
    # draining the pipe: a very fast child may have exited after publishing a complete READY
    # record while those bytes are still waiting in the kernel pipe buffer.
    while time.monotonic() < deadline:
        ready, _, _ = select.select([fd], [], [], min(0.05, max(0.0, deadline - time.monotonic())))
        if not ready:
            if proc.poll() is not None:
                raise RuntimeError(
                    f"Graphium exited without a complete FIRST_EDITABLE record rc={proc.returncode}"
                )
            continue
        chunk = os.read(fd, 256)
        if not chunk:
            rc = proc.poll()
            raise RuntimeError(
                "FIRST_EDITABLE pipe reached EOF before a complete newline record"
                + (f" rc={rc}" if rc is not None else "")
            )
        data.extend(chunk)
        if b"\n" in data:
            return bytes(data.split(b"\n", 1)[0])
    raise RuntimeError(f"Graphium did not emit a complete FIRST_EDITABLE handshake within {timeout:g}s")


def parse_ready_line(line: bytes) -> tuple[int, int]:
    parts = line.decode("ascii", errors="strict").split()
    if len(parts) != 3 or parts[0] != "READY":
        raise RuntimeError(f"invalid FIRST_EDITABLE handshake: {line!r}")
    pid, stamp = int(parts[1]), int(parts[2])
    if pid <= 0 or stamp <= 0:
        raise RuntimeError("invalid FIRST_EDITABLE pid/timestamp")
    return pid, stamp


def one_run(launcher: Path, arg: Path | None, env: dict[str, str]) -> tuple[float, float]:
    rfd, wfd = os.pipe()
    os.set_inheritable(wfd, True)
    run_env = dict(env)
    run_env["GRAPHIUM_BENCHMARK_READY_FD"] = str(wfd)
    cmd = [str(launcher)] + ([str(arg)] if arg is not None else [])
    start = time.monotonic_ns()
    proc = subprocess.Popen(
        cmd,
        env=run_env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        pass_fds=(wfd,),
    )
    os.close(wfd)
    try:
        child_pid, stamp = parse_ready_line(_read_ready_line(rfd, proc))
        if child_pid != proc.pid:
            raise RuntimeError(f"FIRST_EDITABLE came from unexpected pid {child_pid}, expected {proc.pid}")
        if stamp < start:
            raise RuntimeError("FIRST_EDITABLE timestamp predates parent start")
        latency_ms = (stamp - start) / 1_000_000.0
        memory = rss_mib(proc.pid)
        return latency_ms, memory
    finally:
        os.close(rfd)
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=3)
        time.sleep(0.04)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--receipt", type=Path, required=True)
    ap.add_argument("--runs", type=int, default=7)
    ap.add_argument("--state-root", type=Path, required=True)
    args = ap.parse_args()
    if args.runs < 7:
        raise SystemExit("PERFORMANCE_FAIL: at least 7 measured runs required")
    launcher = args.root / "bin/graphium"
    if not launcher.is_file():
        raise SystemExit("PERFORMANCE_FAIL: Graphium launcher missing")
    env = dict(os.environ)
    if not env.get("DISPLAY"):
        raise SystemExit("PERFORMANCE_BLOCKED: X11 DISPLAY required for the G04 desktop baseline")
    env["GDK_BACKEND"] = "x11"
    state = args.state_root.resolve()
    state.mkdir(parents=True, exist_ok=True)
    for sub in ("config", "data", "cache", "state"):
        (state / sub).mkdir(exist_ok=True)
    env.update({
        "HOME": str(state),
        "XDG_CONFIG_HOME": str(state / "config"),
        "XDG_DATA_HOME": str(state / "data"),
        "XDG_CACHE_HOME": str(state / "cache"),
        "XDG_STATE_HOME": str(state / "state"),
    })

    with tempfile.TemporaryDirectory(prefix="graphium-g04-perf-") as td:
        t = Path(td)
        workloads = {
            "empty": None,
            "5KiB": t / "5k.txt",
            "1MiB": t / "1m.txt",
            "10MiB": t / "10m.txt",
        }
        make_file(workloads["5KiB"], 5 * 1024)
        make_file(workloads["1MiB"], 1024 * 1024)
        make_file(workloads["10MiB"], 10 * 1024 * 1024)
        hashes = {k: (hashlib.sha256(v.read_bytes()).hexdigest() if v else None) for k, v in workloads.items()}
        result = {}
        for name, sample in workloads.items():
            one_run(launcher, sample, env)  # uncounted priming
            times: list[float] = []
            rss: list[float] = []
            for _ in range(args.runs):
                ms, mem = one_run(launcher, sample, env)
                times.append(ms)
                rss.append(mem)
            result[name] = {
                "times_ms": times,
                "median_ms": statistics.median(times),
                "p90_ms": p90(times),
                "rss_mib": rss,
                "median_rss_mib": statistics.median(rss),
            }
            print(
                f"GRAPHIUM_FIRST_EDITABLE {name} "
                f"median_ms={result[name]['median_ms']:.3f} "
                f"p90_ms={result[name]['p90_ms']:.3f} "
                f"median_rss_mib={result[name]['median_rss_mib']:.2f}"
            )

        gates = {
            "empty_absolute_750ms": result["empty"]["median_ms"] <= 750.0,
            "5KiB_absolute_900ms": result["5KiB"]["median_ms"] <= 900.0,
            "idle_rss_200MiB": result["empty"]["median_rss_mib"] <= 200.0,
        }
        payload = {
            "work_item": "G04",
            "metric": "FIRST_EDITABLE",
            "oracle": "single atomic inherited-pipe READY record emitted after requested Open, map and TextView focus",
            "cross_product_comparable": False,
            "runs_measured": args.runs,
            "priming_runs": 1,
            "safety_disabled": False,
            "desktop_backend": "x11",
            "isolated_state_root": str(state),
            "samples_sha256": hashes,
            "workloads": result,
            "g04_absolute_admission_gates": gates,
        }
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        if not all(gates.values()):
            print("G04_ABSOLUTE_FIRST_EDITABLE_GATE=FAIL")
            raise SystemExit(2)
        print("G04_ABSOLUTE_FIRST_EDITABLE_GATE=PASS")
        print("FINAL_PHASE=G04_FIRST_EDITABLE_PERFORMANCE_PASS")


if __name__ == "__main__":
    main()
