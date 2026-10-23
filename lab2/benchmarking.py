"""Correctness-first microbenchmarking and CSV result output."""
import csv
import json
import statistics
import time
import tracemalloc
from collections import Counter
from pathlib import Path

from .algorithms import ALGORITHMS, SortStats
from .datasets import generate_dataset

FIELDS = ["dataset", "algorithm", "input_size", "seed", "trials", "time_unit",
          "median_seconds", "peak_python_bytes", "comparisons", "partitions",
          "max_partition_depth", "fallbacks", "status", "message"]


def _record_fingerprint(record):
    """Canonical representation for preserving supported int/dict records."""
    return json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _is_correctly_sorted_and_preserved(actual, original, key):
    """Check order by key and preserve the full multiset, independent of ties."""
    if len(actual) != len(original):
        return False
    actual_keys = [key(record) for record in actual] if key else actual
    if any(actual_keys[i] > actual_keys[i + 1] for i in range(len(actual_keys) - 1)):
        return False
    return Counter(map(_record_fingerprint, actual)) == Counter(map(_record_fingerprint, original))


def benchmark_suite(*, sizes=(1000,), seed=2026, trials=3, output_dir="results",
                    include_records=False):
    """Benchmark five distributions; invalid outputs never receive timings.

    Peak memory is tracemalloc's Python allocation peak, measured separately
    from timing to avoid tracing overhead in runtime samples. It excludes many
    native allocations and is not a process RSS or OS memory limit.
    """
    if trials < 1: raise ValueError("trials must be positive")
    distributions = ("random", "sorted", "reverse", "nearly_sorted", "adversarial")
    records = []
    for size in sizes:
        for dataset in distributions:
            data = generate_dataset(size, dataset, seed=seed, records=include_records)
            key = (lambda row: (row["timestamp"], row["amount"], row["merchant"])) if include_records else None
            expected = sorted(data, key=key)
            for name, algorithm in ALGORITHMS.items():
                stats = SortStats()
                try:
                    timings = []
                    last_trial_stats = SortStats()
                    for _ in range(trials):
                        trial_stats = SortStats()
                        sample = data.copy()
                        start = time.perf_counter()
                        actual = algorithm(sample, key=key, stats=trial_stats)
                        timings.append(time.perf_counter() - start)
                        last_trial_stats = trial_stats
                        if not _is_correctly_sorted_and_preserved(actual, data, key):
                            raise ValueError("output keys are not sorted or input records were not preserved")
                    memory_sample = data.copy()
                    tracemalloc.start()
                    algorithm(memory_sample, key=key)
                    _, peak = tracemalloc.get_traced_memory()
                    tracemalloc.stop()
                    counters_available = name != "timsort_baseline"
                    records.append({"dataset": dataset, "algorithm": name, "input_size": size,
                        "seed": seed, "trials": trials, "time_unit": "seconds",
                        "median_seconds": f"{statistics.median(timings):.9f}",
                        # Counters describe one timed run, not their sum across trials.
                        # CPython does not expose comparison counts for built-in Timsort.
                        "peak_python_bytes": peak,
                        "comparisons": last_trial_stats.comparisons if counters_available else "",
                        "partitions": last_trial_stats.partitions if counters_available else "",
                        "max_partition_depth": last_trial_stats.max_partition_depth if counters_available else "",
                        "fallbacks": last_trial_stats.fallbacks if counters_available else "",
                        "status": "ok", "message": ""})
                except Exception as exc:
                    if tracemalloc.is_tracing(): tracemalloc.stop()
                    records.append({"dataset": dataset, "algorithm": name, "input_size": size,
                        "seed": seed, "trials": trials, "time_unit": "seconds",
                        "median_seconds": "", "peak_python_bytes": "",
                        "comparisons": stats.comparisons, "partitions": stats.partitions,
                        "max_partition_depth": stats.max_partition_depth,
                        "fallbacks": stats.fallbacks, "status": "failed", "message": repr(exc)})
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    record_tag = "_records" if include_records else ""
    path = directory / f"benchmark_{'-'.join(map(str, sizes))}{record_tag}_seed{seed}_trials{trials}.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader(); writer.writerows(records)
    return path, records
