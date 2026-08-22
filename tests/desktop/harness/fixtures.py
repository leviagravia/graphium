from __future__ import annotations
from pathlib import Path


def write_text(path: Path, text: str) -> Path:
    path.write_text(text, encoding='utf-8')
    return path


def realistic_text(size=1_048_576):
    line = 'alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu\n'
    return (line * ((size // len(line)) + 1))[:size]


def visible_verdict(prompt='Visible behavior correct? [PASS/FAIL]: '):
    while True:
        value = input(prompt).strip().upper()
        if value == 'PASS':
            return True
        if value == 'FAIL':
            return False
