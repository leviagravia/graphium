from __future__ import annotations
import statistics,time
def median_ms(samples): return statistics.median(samples)
def timed_ms(fn):
    t=time.perf_counter(); value=fn(); return (time.perf_counter()-t)*1000.0,value
