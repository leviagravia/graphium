#!/usr/bin/env python3
"""Audit Graphium G09 accelerators against active Cinnamon/GNOME global keybindings."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) in sys.path:
    sys.path.remove(str(ROOT))
sys.path.insert(0, str(ROOT))

from graphium.application.commands import accelerator_map

if "--bootstrap-only" in sys.argv:
    amap = accelerator_map()
    if amap.get("move-lines-up") != "<Alt>Up" or amap.get("move-lines-down") != "<Alt>Down":
        raise SystemExit("G09_SHORTCUT_BOOTSTRAP=FAIL")
    print(f"G09_SHORTCUT_BOOTSTRAP=PASS root={ROOT}")
    raise SystemExit(0)


def normalize(value: str) -> str:
    value = value.strip().replace("<Primary>", "<Control>")
    mods = [m.lower() for m in re.findall(r"<([^>]+)>", value)]
    aliases = {"ctrl": "control", "control": "control", "primary": "control"}
    mods = [aliases.get(m, m) for m in mods]
    key = re.sub(r"<[^>]+>", "", value).strip().lower()
    return "+".join(sorted(mods) + [key]) if key else ""


def main() -> None:
    proc = subprocess.run(
        ["gsettings", "list-recursively"], text=True, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, check=False,
    )
    if proc.returncode != 0:
        raise SystemExit(f"G09_SHORTCUT_AUDIT_FAIL: gsettings rc={proc.returncode}: {proc.stderr.strip()}")
    active: dict[str, list[str]] = {}
    token_re = re.compile(r"<[^'\"]+>[^'\",\]\s]*")
    for line in proc.stdout.splitlines():
        if not (line.startswith("org.cinnamon") or line.startswith("org.gnome.desktop")):
            continue
        for token in token_re.findall(line):
            n = normalize(token)
            if n:
                active.setdefault(n, []).append(line)

    amap = accelerator_map()
    required = {"move-lines-up": "<Alt>Up", "move-lines-down": "<Alt>Down"}
    for action, expected in required.items():
        if amap.get(action) != expected:
            raise SystemExit(f"G09_SHORTCUT_AUDIT_FAIL: {action} expected {expected}, found {amap.get(action)}")

    collisions = []
    print("GRAPHIUM_G09_ACCELERATORS:")
    for action, accel in amap.items():
        n = normalize(accel)
        print(f"  {action}={accel} normalized={n}")
        if n in active:
            collisions.append((action, accel, active[n]))
    if collisions:
        for action, accel, lines in collisions:
            print(f"COLLISION action={action} accel={accel}")
            for line in lines[:5]:
                print(f"  {line}")
        raise SystemExit("G09_SHORTCUT_COLLISION_GATE=FAIL")

    print("G09_ALT_UP_DOWN_CINNAMON_COLLISION=PASS")
    print("G09_SHORTCUT_COLLISION_GATE=PASS")
    print("FINAL_PHASE=G09_SHORTCUT_AUDIT_PASS")


if __name__ == "__main__":
    main()
