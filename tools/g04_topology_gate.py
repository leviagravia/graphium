#!/usr/bin/env python3
"""Desktop topology gate: one Graphium invocation/process/window/document."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import tempfile
import time


def root_windows() -> set[str]:
    p = subprocess.run(["xprop", "-root", "_NET_CLIENT_LIST"], text=True,
                       stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False)
    return set(re.findall(r"0x[0-9a-fA-F]+", p.stdout)) if p.returncode == 0 else set()


def window_pid(wid: str) -> int | None:
    p = subprocess.run(["xprop", "-id", wid, "_NET_WM_PID"], text=True,
                       stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False)
    m = re.search(r"=\s*(\d+)", p.stdout)
    return int(m.group(1)) if m else None


def window_title(wid: str) -> str:
    p = subprocess.run(["xprop", "-id", wid, "_NET_WM_NAME"], text=True,
                       stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False)
    m = re.search(r'=\s*"(.*)"\s*$', p.stdout)
    return m.group(1) if m else p.stdout.strip()


def wait_window(pid: int, before: set[str], expected: str, timeout: float = 8.0) -> str:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        for wid in root_windows() - before:
            if window_pid(wid) == pid and expected in window_title(wid):
                return wid
        time.sleep(0.02)
    raise RuntimeError(f"no Graphium window for pid={pid} title~{expected!r}")


def wait_named_windows(before: set[str], expected_names: set[str], timeout: float = 8.0) -> dict[str, tuple[str, int]]:
    found: dict[str, tuple[str, int]] = {}
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        for wid in root_windows() - before:
            pid = window_pid(wid)
            if not pid:
                continue
            title = window_title(wid)
            for name in expected_names - found.keys():
                if name in title:
                    found[name] = (wid, pid)
        if found.keys() >= expected_names:
            return found
        time.sleep(0.02)
    raise RuntimeError(f"missing Graphium windows: expected={expected_names}, found={found}")


def isolated_env(root: Path) -> dict[str, str]:
    env = dict(os.environ)
    env["GDK_BACKEND"] = "x11"
    for name in ("config", "data", "cache", "state"):
        (root / name).mkdir(parents=True, exist_ok=True)
    env.update({
        "HOME": str(root),
        "XDG_CONFIG_HOME": str(root / "config"),
        "XDG_DATA_HOME": str(root / "data"),
        "XDG_CACHE_HOME": str(root / "cache"),
        "XDG_STATE_HOME": str(root / "state"),
    })
    return env


def terminate_pids(pids: set[int]) -> None:
    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    deadline = time.monotonic() + 2.0
    while pids and time.monotonic() < deadline:
        pids = {p for p in pids if Path(f"/proc/{p}").exists()}
        time.sleep(0.03)
    for pid in pids:
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--state-root", type=Path, required=True)
    args = ap.parse_args()
    if not os.environ.get("DISPLAY") or shutil.which("xprop") is None:
        raise SystemExit("G04_TOPOLOGY_BLOCKED: X11 DISPLAY/xprop required")
    launcher = args.root / "bin/graphium"
    if not launcher.is_file():
        raise SystemExit("G04_TOPOLOGY_FAIL: launcher missing")

    args.state_root.mkdir(parents=True, exist_ok=True)
    env = isolated_env(args.state_root)
    with tempfile.TemporaryDirectory(prefix="graphium-g04-topology-") as td:
        td = Path(td)
        a = td / "alpha.txt"; b = td / "beta.txt"
        a.write_text("alpha\n", encoding="utf-8")
        b.write_text("beta\n", encoding="utf-8")

        # Two independent invocations must produce two independent mapped processes.
        before = root_windows()
        p1 = subprocess.Popen([str(launcher), str(a)], env=env,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        p2 = None
        try:
            w1 = wait_window(p1.pid, before, a.name)
            before2 = root_windows()
            p2 = subprocess.Popen([str(launcher), str(b)], env=env,
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            w2 = wait_window(p2.pid, before2, b.name)
            if p1.pid == p2.pid or w1 == w2:
                raise RuntimeError("independent invocations did not produce independent process/window")
            if a.name not in window_title(w1):
                raise RuntimeError("second invocation hijacked first window title/document")
            print(f"G04_NON_UNIQUE_TWO_INVOCATIONS=PASS pids={p1.pid},{p2.pid}")
        finally:
            terminate_pids({p1.pid} | ({p2.pid} if p2 else set()))

        # One invocation with two files must fan out to two one-document processes.
        before = root_windows()
        parent = subprocess.Popen([str(launcher), str(a), str(b)], env=env,
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        found: dict[str, tuple[str, int]] = {}
        try:
            found = wait_named_windows(before, {a.name, b.name})
            pids = {entry[1] for entry in found.values()}
            if len(pids) != 2:
                raise RuntimeError(f"multi-file invocation did not fan out to two processes: {found}")
            if parent.pid not in pids:
                raise RuntimeError(f"original invocation owns no document window: parent={parent.pid}, found={found}")
            print(f"G04_MULTI_FILE_PROCESS_FANOUT=PASS pids={sorted(pids)}")
        finally:
            terminate_pids({parent.pid} | {entry[1] for entry in found.values()})

    print("G04_ONE_PROCESS_ONE_WINDOW_ONE_DOCUMENT=PASS")
    print("FINAL_PHASE=G04_TOPOLOGY_GATE_PASS")


if __name__ == "__main__":
    main()
