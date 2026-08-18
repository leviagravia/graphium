#!/usr/bin/env python3
"""Fresh-process pure Statistics performance gate for Graphium G07."""
from __future__ import annotations

import json
import os
from pathlib import Path
import resource
import statistics
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) in sys.path: sys.path.remove(str(ROOT))
sys.path.insert(0,str(ROOT))

from graphium.product import WORK_ITEM

CASES=((1024*1024,1000.0),(10*1024*1024,1500.0))
RSS_MAX_MIB=260.0


def _g07_or_later():
    return WORK_ITEM.startswith('G') and WORK_ITEM[1:].isdigit() and int(WORK_ITEM[1:])>=7


def worker(size: int) -> None:
    from graphium.application.text_statistics import count_text_statistics
    unit='Graphium αβ quick edit words 0123456789\n'
    text=(unit*((size//len(unit))+2))[:size]
    t0=time.perf_counter_ns(); result=count_text_statistics(text); elapsed=(time.perf_counter_ns()-t0)/1_000_000
    rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024.0
    print(json.dumps({'size':size,'elapsed_ms':elapsed,'rss_mib':rss,'chars':result.characters,'words':result.words,'lines':result.lines},separators=(',',':')))


def sample(size: int):
    proc=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--worker',str(size)],capture_output=True,text=True,timeout=10)
    if proc.returncode!=0: raise RuntimeError(proc.stderr or proc.stdout)
    return json.loads(proc.stdout.strip().splitlines()[-1])


def main():
    if not _g07_or_later(): raise SystemExit(f'G07_STATISTICS_PERFORMANCE_FAIL wrong work item {WORK_ITEM}')
    for size,budget in CASES:
        sample(size)  # uncounted priming process
        values=[sample(size) for _ in range(7)]
        med=statistics.median(v['elapsed_ms'] for v in values)
        p90=sorted(v['elapsed_ms'] for v in values)[-1]  # conservative n=7 ceiling
        rss=max(v['rss_mib'] for v in values)
        if any(v['chars']!=size for v in values):
            raise SystemExit(f'G07_STATISTICS_PERFORMANCE_FAIL character count size={size}')
        if med>budget: raise SystemExit(f'G07_STATISTICS_PERFORMANCE_FAIL size={size} median_ms={med:.3f} budget={budget:.3f}')
        if rss>RSS_MAX_MIB: raise SystemExit(f'G07_STATISTICS_PERFORMANCE_FAIL size={size} rss_mib={rss:.2f} budget={RSS_MAX_MIB:.2f}')
        print(f'G07_STATS size={size} median_ms={med:.3f} p90_ms={p90:.3f} max_rss_mib={rss:.2f}')
    print('G07_STATISTICS_PERFORMANCE=PASS')
    print('FINAL_PHASE=G07_STATISTICS_PERFORMANCE_PASS')


if __name__=='__main__':
    if len(sys.argv)==3 and sys.argv[1]=='--worker': worker(int(sys.argv[2]))
    elif '--bootstrap-only' in sys.argv:
        if not _g07_or_later(): raise SystemExit(f'G07_STATISTICS_BOOTSTRAP=FAIL work_item={WORK_ITEM}')
        print(f'G07_STATISTICS_BOOTSTRAP=PASS root={ROOT}')
    else: main()
