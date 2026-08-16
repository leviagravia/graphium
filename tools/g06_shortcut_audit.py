#!/usr/bin/env python3
"""Audit G06 Graphium accelerators against active Cinnamon/GNOME global keybindings."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_root = str(ROOT)
if _root in sys.path:
    sys.path.remove(_root)
sys.path.insert(0, _root)

from graphium.application.commands import accelerator_map
from graphium.product import WORK_ITEM

if "--bootstrap-only" in sys.argv:
    if WORK_ITEM != "G06":
        raise SystemExit(f"G06_SHORTCUT_BOOTSTRAP=FAIL work_item={WORK_ITEM}")
    print(f"G06_SHORTCUT_BOOTSTRAP=PASS root={ROOT}")
    raise SystemExit(0)


def normalize(value: str) -> str:
    value = value.strip().replace("<Primary>", "<Control>")
    mods = [m.lower() for m in re.findall(r"<([^>]+)>", value)]
    aliases = {"ctrl": "control", "control": "control", "primary": "control"}
    mods = [aliases.get(m, m) for m in mods]
    key = re.sub(r"<[^>]+>", "", value).strip().lower()
    return "+".join(sorted(mods) + [key]) if key else ""


def main() -> None:
    if WORK_ITEM != "G06":
        raise SystemExit(f"G06_SHORTCUT_AUDIT_FAIL: wrong work item {WORK_ITEM}")
    proc = subprocess.run(
        ["gsettings", "list-recursively"], text=True, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, check=False,
    )
    if proc.returncode != 0:
        raise SystemExit(
            f"G06_SHORTCUT_AUDIT_FAIL: gsettings rc={proc.returncode}: {proc.stderr.strip()}"
        )
    active: dict[str, list[str]] = {}
    token_re = re.compile(r"<[^'\"]+>[^'\",\]\s]*")
    for line in proc.stdout.splitlines():
        if not (line.startswith("org.cinnamon") or line.startswith("org.gnome.desktop")):
            continue
        for token in token_re.findall(line):
            n = normalize(token)
            if n:
                active.setdefault(n, []).append(line)

    collisions = []
    print("GRAPHIUM_ACCELERATORS:")
    for action, accel in accelerator_map().items():
        n = normalize(accel)
        print(f"  {action}={accel} normalized={n}")
        if n in active:
            collisions.append((action, accel, active[n]))
    if collisions:
        for action, accel, lines in collisions:
            print(f"COLLISION action={action} accel={accel}")
            for line in lines[:5]:
                print(f"  {line}")
        raise SystemExit("G06_SHORTCUT_COLLISION_GATE=FAIL")

    known = normalize("<Ctrl><Alt>L")
    print(f"KNOWN_MINT_RESERVED_CTRL_ALT_L_PRESENT={'YES' if known in active else 'NOT_OBSERVED'}")
    print("G06_SHORTCUT_COLLISION_GATE=PASS")
    print("FINAL_PHASE=G06_SHORTCUT_AUDIT_PASS")


if __name__ == "__main__":
    main()
